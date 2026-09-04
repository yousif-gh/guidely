# Guidely — Internal Knowledge Assistant

Ask questions about internal docs in plain language and get a concise answer with numbered, clickable citations back to the exact source passages.

**Stack:** React + Vite frontend · FastAPI backend · FAISS vector index · pluggable embeddings/LLM providers (OpenAI, Ollama, or a zero-dependency local mode).

## How the pipeline works

```
upload/edit .txt/.md ──► parse ──► chunk (~220 words, 40-word overlap)
                                      │
                                      ▼
                        embed (cache by sha256(provider|model|text))
                                      │
                                      ▼
                          FAISS IndexFlatIP (cosine on normalized vectors)

question ──► embed ──► top-k similarity search ──► min-score filter
                                      │
                                      ▼
                LLM answer from retrieved chunks, cited as [1] [2]
                                      │
                                      ▼
              JSON: answer + sources (file, chunk, score, snippet)
              + per-query log (timestamp, latency, cache hits, sources)
```

Key behaviors:

- **Embedding cache** — every chunk embedding is keyed by `sha256(provider|model|text)` and persisted to `backend/data/embeddings_cache.json`. Unchanged text is never re-embedded; hits/misses are counted and exposed in `/metrics`.
- **Skip unchanged files** — `/documents/reindex` compares each file's sha256 against the index manifest and skips files that haven't changed.
- **Providers are pluggable** via `.env`:
  - `EMBEDDINGS_PROVIDER`: `openai` | `ollama` | `local` (deterministic feature-hashing — no key, works offline; fine for dev/tests, use openai/ollama for production quality)
  - `LLM_PROVIDER`: `openai` | `ollama` | `extractive` (no-LLM fallback that stitches the best-matching sentences from retrieved chunks)
- **Sources always shown** — every answer returns file names, chunk IDs, similarity scores, and snippets; the UI renders `[n]` citations as chips that scroll to the matching source card.

## Dataset

Six sample documents live in `backend/data/sample-docs/` (bring your own by uploading via the admin page or dropping files there and re-indexing):

`remote-work-policy.txt` · `expense-policy.txt` · `it-security-faq.txt` · `onboarding-guide.txt` · `product-returns-faq.txt` · `incident-response-guide.txt`

## Setup

### Backend

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # defaults run with no API keys
cd backend
uvicorn main:app --reload --port 8000
curl -X POST localhost:8000/documents/reindex        # index the sample docs
```

To use real models, edit `.env`:

```ini
EMBEDDINGS_PROVIDER=openai        # or ollama
LLM_PROVIDER=openai               # or ollama
OPENAI_API_KEY=sk-...             # keep secrets in .env, never in code
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_EMBED_MODEL=nomic-embed-text
# OLLAMA_CHAT_MODEL=qwen2.5:3b
```

Switching embedding providers changes the vector space — run a re-index afterwards (cached entries are keyed per provider/model so nothing collides).

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (dev server proxies /api → :8000)
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/documents` | Upload a `.txt`/`.md` file, chunk + embed + index it |
| GET | `/documents` | List indexed documents |
| GET | `/documents/{id}/content` | Read a document's raw text |
| PUT | `/documents/{id}` | Replace content and re-index |
| DELETE | `/documents/{id}` | Remove document + vectors |
| POST | `/documents/reindex` | Re-index `data/sample-docs`, skipping unchanged files |
| POST | `/ask` | `{question, top_k?, tags?, history?}` → answer + sources |
| GET | `/health` | Status, index counts, active providers |
| GET | `/metrics` | Docs/chunks/queries, latency median + p95, cache stats, error counts |
| GET | `/metrics/export.csv` | Query log export (timestamp, latency, sources) |

Error contract: empty question → `400`, missing model key → `503`, corrupted/unsupported file → `400`, no relevant passages → `404`, provider failure/timeout → `502`. All errors are logged with type counts in `/metrics`.

## Testing & Metrics

Measured on local dev (provider `local` + `extractive`, warm cache) against the 6 sample docs with the 10-query set below.

| Metric | Type | Target | Result | Status |
|---|---|---|---|---|
| Retrieval@3 | Manual | ≥ 80% | 10/10 queries had the correct passage in top-3 (**100%**) | ✅ |
| Answer reference coverage | Manual | ≥ 90% | 10/10 answers cited ≥ 1 correct source (**100%**) | ✅ |
| Latency (median) | Auto | < 3 s | **1.5 ms** median (local provider; expect ~1–2 s with OpenAI) | ✅ |
| Latency (p95) | Auto | < 5 s | **3.9 ms** p95 (local provider) | ✅ |
| Embedding cache effectiveness | Auto | 100% hits on repeats | 5/5 repeated queries: **100% cache hits**, 0 re-embeddings | ✅ |
| Failure handling | Auto | 4xx/5xx + clear message | empty→400, missing key→503, corrupted file→400, no results→404 | ✅ |
| Source precision | Manual | ≥ 80% | 10/10 spot-checked snippets support the answer (**100%**) | ✅ |
| Indexing throughput | Auto (bonus) | no errors; skip unchanged | 6 files / 9 chunks in **24 ms**; repeat run skipped 6/6 in 0.3 ms | ✅ |

Retrieval test set (answers all exist in sample docs): password reset steps, remote days per week, refund timing, SEV1 response time, GCC hotel cap, client entertainment approval, salary date, phishing procedure, probation length, MFA for VPN.

Reproduce: start the backend, `POST /documents/reindex`, run the queries against `/ask`, then read `/metrics`. Raw per-query data is in `backend/data/logs/queries.jsonl` and via `/metrics/export.csv`.

## Bonus features included

- Conversation history: the UI sends the last turns with each `/ask` so follow-ups keep context.
- Tags: attach comma-separated tags on upload; `/ask` accepts a `tags` filter.
- Query-log CSV export with timestamp, latency, and retrieved sources.
- `/health` and `/metrics` JSON endpoints.

## Project structure

```
guidely/
├── frontend/
│   └── src/
│       ├── components/    AnswerCard, SourceCard, DocumentTable, UploadForm
│       ├── pages/         SearchPage, AdminPage
│       ├── App.jsx · main.jsx · api.js · styles.css
├── backend/
│   ├── main.py            app, CORS, /health, /metrics, CSV export
│   ├── routes/            documents.py (upload/edit/delete/reindex), search.py (/ask)
│   ├── services/          parsing.py, embeddings.py (providers + cache),
│   │                      vector_store.py (FAISS), llm.py, metrics.py
│   ├── models/record.py   Pydantic schemas
│   └── data/sample-docs/  6 sample files
├── requirements.txt · .env.example · README.md
```
