"""Answer generation.

Providers (set LLM_PROVIDER in .env):
  - "openai":     OpenAI chat completions (needs OPENAI_API_KEY)
  - "groq":       Groq's OpenAI-compatible chat completions (needs GROQ_API_KEY).
                  Groq only serves chat models, not embeddings — pair this with
                  EMBEDDINGS_PROVIDER=local or =openai.
  - "ollama":     local Ollama server (OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL)
  - "extractive": no-LLM fallback that stitches the top sentences from the
                  retrieved chunks. Keeps the pipeline testable without keys.

The prompt instructs the model to answer ONLY from the provided context and
cite sources as [1], [2] matching the returned source list.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional

import httpx

SYSTEM_PROMPT = (
    "You are Guidely, an internal knowledge assistant. Answer the question "
    "using ONLY the provided context chunks. Be concise (2-5 sentences). "
    "Cite sources inline as [1], [2] etc., matching the numbered context. "
    "If the context does not contain the answer, say you could not find it "
    "in the indexed documents. Always answer in the same language the "
    "question was asked in (e.g. reply in Arabic to a question written in "
    "Arabic)."
)


ARABIC_RE = re.compile(r"[؀-ۿ]")


def needs_translation(text: str) -> bool:
    """True if the question is written in a script the (English-only) doc
    index can't lexically/semantically match against directly."""
    return bool(ARABIC_RE.search(text))


class MissingAPIKeyError(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


def provider_info() -> tuple[str, str]:
    provider = os.getenv("LLM_PROVIDER", "extractive").lower()
    default_models = {
        "openai": "gpt-oss-20b",
        "groq": "openai/gpt-oss-20b",
        "ollama": "qwen2.5:3b",
        "extractive": "extractive-v1",
    }
    model = os.getenv("LLM_MODEL", default_models.get(provider, "unknown"))
    return provider, model


def _build_user_prompt(question: str, contexts: List[dict], history: Optional[List[dict]]) -> str:
    ctx_lines = []
    for i, c in enumerate(contexts, start=1):
        ctx_lines.append(f"[{i}] (file: {c['file']})\n{c['text']}")
    history_block = ""
    if history:
        turns = "\n".join(f"{t.get('role', 'user')}: {t.get('content', '')}" for t in history[-6:])
        history_block = f"Conversation so far:\n{turns}\n\n"
    return (
        f"{history_block}Context:\n" + "\n\n".join(ctx_lines) + f"\n\nQuestion: {question}\nAnswer:"
    )


def _answer_openai_compatible(
    question, contexts, history, model, *, base_url, api_key, key_env_name, provider_label
) -> str:
    if not api_key:
        raise MissingAPIKeyError(
            f"{key_env_name} is not set. Add it to your .env or switch LLM_PROVIDER=extractive."
        )
    try:
        resp = httpx.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(question, contexts, history)},
                ],
                "temperature": 0.2,
                "max_tokens": 400,
            },
            timeout=45,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMProviderError("The language model timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise LLMProviderError(f"{provider_label} chat request failed: {exc}") from exc
    return resp.json()["choices"][0]["message"]["content"].strip()


def _chat_openai_compatible(
    messages, model, *, base_url, api_key, key_env_name, provider_label,
    temperature=0, max_tokens=200,
) -> str:
    if not api_key:
        raise MissingAPIKeyError(
            f"{key_env_name} is not set. Add it to your .env or switch LLM_PROVIDER=extractive."
        )
    try:
        resp = httpx.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMProviderError("The language model timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise LLMProviderError(f"{provider_label} chat request failed: {exc}") from exc
    return resp.json()["choices"][0]["message"]["content"].strip()


TRANSLATE_PROMPT = (
    "Translate the user's text to English. Output ONLY the translation, "
    "with no extra commentary or quotes."
)


def translate_to_english(text: str) -> str:
    """Best-effort translation used only to steer retrieval against an
    English-only document index. Falls back to the original text (and thus
    to whatever partial/no matches lexical search finds) if translation
    isn't available for the configured provider or the call fails."""
    provider, model = provider_info()
    messages = [
        {"role": "system", "content": TRANSLATE_PROMPT},
        {"role": "user", "content": text},
    ]
    try:
        if provider == "openai":
            return _chat_openai_compatible(
                messages, model,
                base_url="https://api.openai.com/v1/chat/completions",
                api_key=os.getenv("OPENAI_API_KEY"),
                key_env_name="OPENAI_API_KEY",
                provider_label="OpenAI",
            )
        if provider == "groq":
            return _chat_openai_compatible(
                messages, model,
                base_url="https://api.groq.com/openai/v1/chat/completions",
                api_key=os.getenv("GROQ_API_KEY"),
                key_env_name="GROQ_API_KEY",
                provider_label="Groq",
            )
        if provider == "ollama":
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            resp = httpx.post(
                f"{base}/api/chat",
                json={"model": model, "stream": False, "messages": messages},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
    except (MissingAPIKeyError, LLMProviderError, httpx.HTTPError):
        return text
    return text


def translate_text(text: str, target_lang: str) -> str:
    """On-demand translation (e.g. a source snippet) to an arbitrary target
    language. Raises LLMProviderError/MissingAPIKeyError on failure — unlike
    translate_to_english this is user-triggered, so callers should surface
    the error rather than silently falling back."""
    provider, model = provider_info()
    if provider == "extractive":
        raise LLMProviderError(
            "Translation needs an LLM provider. Set LLM_PROVIDER=openai/groq/ollama in .env."
        )
    messages = [
        {"role": "system", "content": f"Translate the user's text to {target_lang}. Output ONLY the translation, with no extra commentary or quotes."},
        {"role": "user", "content": text},
    ]
    if provider == "openai":
        return _chat_openai_compatible(
            messages, model,
            base_url="https://api.openai.com/v1/chat/completions",
            api_key=os.getenv("OPENAI_API_KEY"),
            key_env_name="OPENAI_API_KEY",
            provider_label="OpenAI",
            max_tokens=600,
        )
    if provider == "groq":
        return _chat_openai_compatible(
            messages, model,
            base_url="https://api.groq.com/openai/v1/chat/completions",
            api_key=os.getenv("GROQ_API_KEY"),
            key_env_name="GROQ_API_KEY",
            provider_label="Groq",
            max_tokens=600,
        )
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        resp = httpx.post(
            f"{base}/api/chat",
            json={"model": model, "stream": False, "messages": messages},
            timeout=60,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMProviderError("The language model timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise LLMProviderError(f"Ollama chat request failed: {exc}") from exc
    return resp.json()["message"]["content"].strip()


def _answer_openai(question, contexts, history, model) -> str:
    return _answer_openai_compatible(
        question, contexts, history, model,
        base_url="https://api.openai.com/v1/chat/completions",
        api_key=os.getenv("OPENAI_API_KEY"),
        key_env_name="OPENAI_API_KEY",
        provider_label="OpenAI",
    )


def _answer_groq(question, contexts, history, model) -> str:
    return _answer_openai_compatible(
        question, contexts, history, model,
        base_url="https://api.groq.com/openai/v1/chat/completions",
        api_key=os.getenv("GROQ_API_KEY"),
        key_env_name="GROQ_API_KEY",
        provider_label="Groq",
    )


def _answer_ollama(question, contexts, history, model) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        resp = httpx.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(question, contexts, history)},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMProviderError("The language model timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise LLMProviderError(f"Ollama chat request failed: {exc}") from exc
    return resp.json()["message"]["content"].strip()


def _answer_extractive(question: str, contexts: List[dict]) -> str:
    """Pick the sentences most lexically similar to the question from top chunks."""
    q_tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
    scored = []
    for i, ctx in enumerate(contexts, start=1):
        sentences = re.split(r"(?<=[.!?])\s+", ctx["text"].replace("\n", " "))
        for j, sent in enumerate(sentences):
            s_tokens = set(re.findall(r"[a-z0-9]+", sent.lower()))
            if not s_tokens:
                continue
            overlap = len(q_tokens & s_tokens) / (len(q_tokens) or 1)
            is_question = sent.rstrip().endswith("?") or sent.lstrip().startswith("Q:")
            if is_question:
                # A matching FAQ question means the *next* sentence is the answer.
                if j + 1 < len(sentences):
                    scored.append((overlap, sentences[j + 1].strip(), i))
                continue
            scored.append((overlap, sent.strip(), i))
    scored.sort(key=lambda t: t[0], reverse=True)
    best = scored[0][0] if scored else 0.0
    floor = max(best * 0.4, 0.08)
    top, seen = [], set()
    for overlap, sent, ref in scored:
        clean = re.sub(r"^A:\s*", "", sent).strip()
        if overlap < floor or not clean or clean in seen:
            continue
        seen.add(clean)
        top.append((clean, ref))
        if len(top) == 3:
            break
    if not top:
        return "I could not find an answer to that in the indexed documents."
    return " ".join(f"{sent} [{ref}]" for sent, ref in top)


def generate_answer(
    question: str, contexts: List[dict], history: Optional[List[dict]] = None
) -> str:
    provider, model = provider_info()
    if provider == "openai":
        return _answer_openai(question, contexts, history, model)
    if provider == "groq":
        return _answer_groq(question, contexts, history, model)
    if provider == "ollama":
        return _answer_ollama(question, contexts, history, model)
    return _answer_extractive(question, contexts)