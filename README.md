# Guidely

Guidely is an internal knowledge assistant. Ask a question in plain language and it answers from your company documents, and shows which document the answer came from.

It runs a React frontend and a FastAPI backend on your own machine.

## How it works

**Indexing**

1. Read each `.txt` file in `backend/data/sample-docs/`.
2. Split it into chunks of 400 words, with 50 words of overlap.
3. Turn each chunk into a 384-number embedding with `fastembed` (`BAAI/bge-small-en-v1.5`), running locally.
4. Cache embeddings by a hash of model and text, so unchanged text is never embedded twice.
5. Store the vectors in a FAISS index, using cosine similarity.

**Answering**

1. Embed the question and find the top 3 chunks.
2. Reject the question if no chunk scores at least 0.52.
3. Send the chunks to `openai/gpt-oss-120b` on Groq, with instructions to use only those sources and cite them.
4. Return the answer and the chunks it cited. If the sources don't hold the answer, return 404.

## Dataset

Five fictional documents for a made-up company, Larkfield Supplies, in `backend/data/sample-docs/`:

| File | Content |
|---|---|
| `policy.txt` | Returns, refunds and shipping |
| `faq.txt` | Employee questions |
| `guide.txt` | Warehouse order handling |
| `it-security.txt` | Security rules |
| `onboarding.txt` | New hire process |

## Setup

Requires Python and Node. Tested on Python 3.14 and Node 24. You also need a [Groq API key](https://console.groq.com/keys).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your key to `.env`. The file is ignored by git.

Start the backend:

```bash
cd backend
uvicorn main:app --reload
```

The first run downloads the embedding model, about 67 MB. Build the index once, from another terminal:

```bash
curl -X POST localhost:8000/documents/reindex
```

Start the frontend, from another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173/>. API docs are at <http://localhost:8000/docs>.

To change the answer model, edit `MODEL` in `backend/services/llm.py`. Each Groq account can use a different list of models.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Server status |
| `GET` | `/metrics` | Counts, latency, cache and failures |
| `GET` | `/documents` | List documents |
| `POST` | `/documents` | Upload a `.txt` file and reindex |
| `POST` | `/documents/reindex` | Rebuild and save the index |
| `POST` | `/search` | Return the most similar chunks |
| `POST` | `/ask` | Return an answer with sources |

## Testing & Metrics

Measured on 2026-11-10 on a local machine, with 15 questions whose answers are in the sample docs. To reproduce, start the backend and run `python -m tests.evaluate` from `backend/`.

| Metric | Target | Result | Status |
|---|---|---|---|
| Retrieval@3 | at least 80% | 15/15, 100% | Pass |
| Answer reference coverage | at least 90% | 15/15, 100% | Pass |
| Latency, median | under 3 s | 1.78 s | Pass |
| Latency, p95 | under 5 s | 8.74 s | **Miss** |
| Embedding cache on repeated questions | 100% hits | 30 hits, 0 misses | Pass |
| Empty query | 4xx with clear error | 422 | Pass |
| Missing model key | 4xx/5xx with clear error | 503 | Pass |
| Corrupted file | 4xx/5xx with clear error | 400 | Pass |
| No results found | 4xx/5xx with clear error | 404 | Pass |

Notes on these results:

- **Retrieval@3 is an easy test here.** The sample set has only 6 chunks, so the top 3 is half of everything indexed. Expect a lower score on a larger set.
- **The latency p95 comes from a small sample.** With 15 questions, one or two slow calls set the p95. The cause of the slow calls has not been investigated.
- **Reference coverage is checked by file**, not by exact passage.
- **Answer accuracy:** all 15 answers were compared by hand with the source documents, and all were correct.
- **Missing key** was tested with a fake model client, using `python -m tests.check_answers`.
- A question the documents don't cover but that scores high, "What is the wifi password?", also returned 404.

## Limitations

- There is no login. Anyone who can reach the API can upload documents, so keep it on localhost.
- Only UTF-8 `.txt` files up to 1 MB are supported.
- To edit a document, upload a new file with the same name.
- `/metrics` counters are held in memory and reset when the server restarts.
- The similarity threshold of 0.52 was tuned on 27 questions against this sample set. Re-check it for other documents.
