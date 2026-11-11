# Backend tests

Each script is a plain Python check. It uses `assert` and fails with a traceback when something breaks. No test framework is needed.

## How to run

Activate the virtual environment, then run from `backend/`:

```bash
cd backend
python -m tests.check_parsing
python -m tests.check_embeddings
python -m tests.check_search
python -m tests.check_answers
python -m tests.check_metrics
```

These five need no running server and no Groq key. `check_answers` and `check_metrics` replace Groq with a fake client, so they cost nothing.

`evaluate.py` is different: it needs the backend running on port 8000 and a real `GROQ_API_KEY`. It makes about 17 real model calls.

```bash
python -m tests.evaluate
```

`check_search`, `check_answers` and `check_metrics` rebuild the real index in `data/index/`. That folder is generated and ignored by git.

## Test cases

### `check_parsing.py`: reading and chunking

| Case | Input | Expected |
|---|---|---|
| Chunks overlap | Words `0` to `9`, chunk size 4, overlap 1 | `0 1 2 3`, `3 4 5 6`, `6 7 8 9` |
| Corrupted file rejected | File with invalid UTF-8 bytes | `ValueError`, printed as `rejected: ...` |
| Sample docs present | `data/sample-docs/*.txt` | Exactly 5 files |
| Sample docs chunk | Each sample doc | `policy.txt` gives 2 chunks, the others 1 |

### `check_embeddings.py`: embedding cache

| Case | Input | Expected |
|---|---|---|
| First run embeds everything | 6 sample chunks, empty temporary cache | 0 cache hits |
| Second run uses the cache | Same 6 chunks again | 6 cache hits |
| Cache returns same vectors | Both runs | Identical vectors |
| Changed text is re-embedded | First chunk plus " changed" | 0 cache hits |
| Vector size | Any chunk | 384 numbers |

### `check_search.py`: vector search

| Case | Question | Expected top file |
|---|---|---|
| Refund rule | How long does a refund take for a damaged item? | `policy.txt` |
| Vacation | How many vacation days do I get? | `faq.txt` |
| Password | What is the minimum password length? | `it-security.txt` |
| Box weight | How heavy can a box be? | `guide.txt` |
| First day | What time should I arrive on my first day? | `onboarding.txt` |
| Overlap keeps the rule whole | Refund question | Top chunk contains `3 business days` |

### `check_answers.py`: `POST /ask`

| Case | Setup | Expected status |
|---|---|---|
| Cited answer | Fake model answers with `[1]` | 200, sources are only `policy.txt` |
| Full-width citation | Fake model answers with `【1†L2-L4】` | 200, answer converted to `[1]`, sources are only `policy.txt` |
| Model finds no answer | Fake model replies `NOT_FOUND` | 404 |
| Off-topic question | What is the capital of France? | 404, rejected by score before the model |
| Empty question | Spaces only | 422 |
| Model timeout | Fake model raises a timeout | 504 |
| Missing key | `GROQ_API_KEY` removed | 503, `GROQ_API_KEY is not set` |

### `check_metrics.py`: `GET /metrics`

Runs `check_answers.py` first, then asks the refund question 5 more times.

| Case | Expected |
|---|---|
| Document count | 5 |
| Chunk count | 6 |
| Queries served | Increases by 5 |
| Repeated questions use the cache | Hits increase by 5, misses unchanged |
| Latency recorded | p95 is at least the median, median above 0 |
| Failures counted by status | `404` twice, `422`, `503` and `504` once each |

### `evaluate.py`: end-to-end evaluation

Uses 15 questions whose answers are in the sample docs, against the running server and real model.

| Case | Target |
|---|---|
| Retrieval@3: correct passage in top 3 chunks | At least 80% |
| Answer reference coverage: answer cites the correct file | At least 90% |
| Latency median | Under 3,000 ms |
| Latency p95 | Under 5,000 ms |
| Embedding cache on repeated questions | 0 misses |
| Empty question | 422 |
| Off-topic question | 404 |
| Company question not in the docs, "What is the wifi password?" | 404 |

The latest results are in the main `README.md`.

## Manual checks with `curl`

Upload errors have no script yet. The test files are not in the repository, so create them first in `/tmp`:

```bash
echo "The office parking garage closes at 9 pm every weekday." > /tmp/parking.txt
printf '\xff\xfe broken' > /tmp/bad.txt
: > /tmp/empty.txt
echo "hello" > /tmp/note.md
head -c 1500000 /dev/zero | tr '\0' 'a' > /tmp/big.txt
```

Then, with the server running, send each one. `-w` prints the status code:

```bash
curl -F "file=@/tmp/parking.txt" -w ' [%{http_code}]\n' localhost:8000/documents
curl -F "file=@/tmp/bad.txt" -w ' [%{http_code}]\n' localhost:8000/documents
curl -F "file=@/tmp/empty.txt" -w ' [%{http_code}]\n' localhost:8000/documents
curl -F "file=@/tmp/note.md" -w ' [%{http_code}]\n' localhost:8000/documents
curl -F "file=@/tmp/big.txt" -w ' [%{http_code}]\n' localhost:8000/documents
curl -X POST -w ' [%{http_code}]\n' localhost:8000/documents
curl -F "file=@/tmp/parking.txt;filename=../../evil.txt" -w ' [%{http_code}]\n' localhost:8000/documents
```

| Case | File | Expected |
|---|---|---|
| Valid upload | `parking.txt` | 201, document added and indexed |
| Corrupted upload | `bad.txt`, invalid UTF-8 | 400 |
| Empty upload | `empty.txt` | 400 |
| Wrong type | `note.md` | 415 |
| Too large | `big.txt`, 1.5 MB | 413 |
| No file | none | 422 |
| Path in file name | `parking.txt` sent as `../../evil.txt` | 201, saved as `evil.txt` inside `data/sample-docs/` |
| Search before indexing | `POST /search` with no `data/index/` folder | 409 |

Only the two 201 cases save a file. Remove them before committing, then reindex:

```bash
rm data/sample-docs/parking.txt data/sample-docs/evil.txt
curl -X POST localhost:8000/documents/reindex
```
