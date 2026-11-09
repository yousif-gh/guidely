# Guidely

## Overview

Build an internal knowledge assistant that answers questions in plain language and cites where the answer came from. You'll use a React/Vite frontend and a FastAPI backend. The backend ingests company docs (policies, guides, FAQs), turns them into vector embeddings, searches the most relevant chunks, and asks an LLM to draft a concise answer with references.

The result is a simple workflow: upload docs → index → ask a question → get a clear answer with sources.

## Role Play

You're on a support engineering team. Your job is to ship a tool that helps teammates and customers find accurate information without digging through pages. The system should combine semantic search with natural-language answers, and always show which documents were used.

## Learning Objectives

- Build a Q&A dashboard with React (or another modern frontend).
- Index and retrieve documents using vector embeddings.
- Use an LLM to turn retrieved snippets into short, readable answers.
- Show ranked results and the sources behind each answer.
- Support adding, editing, and re-indexing content.

## Instructions

### AI & Processing

- Convert supported documents (guides, FAQs, manuals) to raw text.
- Split long files into small chunks (e.g., ~500–1,000 tokens).
- Create embeddings using OpenAI (or equivalent) and store them in a vector DB (FAISS, Pinecone, Weaviate, etc.).
- For each user query:
  - Embed the question.
  - Retrieve top-k chunks via vector similarity.
  - Provide those chunks + the question to the LLM.
  - Return the generated answer and the referenced sources (file names + optional snippet).

### Frontend (React/Vite)

- Build a search page that lets users:
  - Enter a question.
  - View the generated answer.
  - See the source snippets/files used.
- Build an admin page to:
  - Upload or edit documents.
  - Trigger re-indexing.

### Backend (FastAPI)

- Endpoint to upload documents and create embeddings.
- Endpoint to persist generated embeddings to the vector database.
- Endpoint to retrieve stored embeddings for similarity search operations.
- Endpoint to process a question, run vector search, and return an answer with references.
- Return clean JSON, handle errors (empty query, missing docs, model timeouts).

### Dataset

- Bring your own docs: internal policies, how-tos, FAQs.
- Include at least 5 sample files in `/data/sample-docs/` for testing.

### Code Quality

- Keep code modular and readable.
- Reuse functions (parsing, chunking, embedding, retrieval).
- If you add notebooks, document steps and results clearly.
- Secure sensitive data: Use `.env` files or system environment variables for API keys and credentials. Both approaches are acceptable.
- The `README.md` should explain purpose, dataset, setup, and how the pipeline works, and include your Testing & Metrics table.

## Testing & Metrics

Use these checks to validate your build. Record results in a short table in the README.

**Implementation Note:**

- **Auto-logged metrics** (must be logged by your backend): Latency, Embedding cache effectiveness, Failure handling
- **Manual validation metrics** (require human review): Retrieval@k accuracy, Answer reference coverage, Source precision

### Retrieval@k (accuracy of search) [Manual validation]

- Prepare 10–20 queries whose answers exist in your sample docs.
- Count how often the correct passage appears in the top-3 retrieved chunks.
- **Target:** ≥ 80% Retrieval@3.

### Answer reference coverage [Manual validation]

- Every answer must list at least one valid source (file + section/snippet).
- **Target:** ≥ 90% answers include at least one correct reference.

### Latency (local dev, warm cache) [Auto-logged]

- Measure time from question → final JSON response.
- **Target:** median < 3s with cached embeddings; p95 (95th percentile) < 5s.
- **Implementation:** Log response times in your backend; calculate median and 95th percentile statistics.

### Embedding cache effectiveness [Auto-logged]

- Re-ask 5+ queries after initial indexing; ensure no re-embedding occurs.
- **Target:** 100% cache hits for unchanged docs.
- **Validation:** Log cache hits vs. new embeddings generated; demonstrate 100% cache hit rate on repeated queries.

### Failure handling [Auto-logged]

- Test these specific cases: empty query, missing model key, corrupted file, no results found.
- **Pass if:** API returns HTTP 4xx/5xx with clear error message; UI shows friendly error state.
- **Implementation:** Log error types and counts; show proper error responses for each case.

### Source precision (highlight quality) [Manual validation]

- If you highlight snippets, spot-check 10 results to ensure the shown text actually supports the answer.
- **Target:** ≥ 80% correct snippet alignment.

### Indexing throughput [Auto-logged, optional]

- Log time to index 5 example files.
- **Target:** completes without errors; repeated runs skip unchanged files.

## Bonus

- Keep conversation history for follow-up questions.
- Add tags or categories for documents and filter in the UI.
- Add authentication/roles (reader vs. admin).
- Export query logs (CSV) with timestamp, latency, retrieved sources.
- Implement a `/health` endpoint and `/metrics` JSON endpoint (counts: docs, chunks, queries served).

## Project Repository Structure

```text
guidely/
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── App.jsx
│
├── backend/
│   ├── main.py
│   ├── routes/
│   │   ├── documents.py
│   │   └── search.py
│   ├── models/
│   │   └── record.py
│   └── data/
│       └── sample-docs/
│           ├── policy.txt
│           ├── faq.txt
│           └── guide.txt
│
├── requirements.txt
├── README.md
└── .env
```

## Tips for Success

- Test embedding + retrieval separately before wiring up the UI.
- Keep chunks short (a few paragraphs) for better relevance.
- Cache embeddings; only re-embed changed files.
- Always display which sources were used for the answer.
- Log queries to make debugging easier (latency, retrieved doc IDs).

## Resources

- OpenAI API
- FAISS
- Pinecone
- React / Vite
- FastAPI
