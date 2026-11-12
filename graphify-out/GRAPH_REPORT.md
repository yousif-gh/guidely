# Graph Report - guidely  (2026-11-11)

## Corpus Check
- Corpus is ~13,332 words - fits in a single context window. You may not need a graph.

## Summary
- 210 nodes · 358 edges · 15 communities (11 shown, 4 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 1% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.89)
- Token cost: 249,161 input · 0 output

## Community Hubs (Navigation)
- Search and Answer API
- Frontend Dependencies
- Embedding and Indexing
- React Pages
- Metrics and Evaluation
- Document Management API
- Project Plan and Records
- Sample Docs and Tests
- Unused Icon Sprite
- Audit Risks and Limits
- Lint Config
- Backend Layout
- Frontend Entry
- Favicon

## God Nodes (most connected - your core abstractions)
1. `embed_texts()` - 15 edges
2. `build_index()` - 15 edges
3. `search()` - 11 edges
4. `Guidely project spec` - 11 edges
5. `ask()` - 10 edges
6. `answer_question()` - 9 edges
7. `read_text()` - 9 edges
8. `chunk_text()` - 8 edges
9. `AdminPage()` - 8 edges
10. `icons.svg SVG Symbol Sprite` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Full-width citation bug (【1】)` --references--> `answer_question()`  [INFERRED]
  .growth/progress.md → backend/services/llm.py
- `AD-4: FAISS with local files` --rationale_for--> `build_index()`  [INFERRED]
  .growth/architecture-decisions.md → backend/services/vector_store.py
- `MIN_SCORE similarity threshold 0.52` --references--> `ask()`  [INFERRED]
  .growth/progress.md → backend/routes/search.py
- `Guidely API endpoints table` --references--> `ask()`  [INFERRED]
  README.md → backend/routes/search.py
- `AD-6: Groq for answers, local fastembed for embeddings` --rationale_for--> `embed_texts()`  [INFERRED]
  .growth/architecture-decisions.md → backend/services/embeddings.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **RAG /ask answer flow** — readme_answering_pipeline, backend_services_embeddings_embed_texts, backend_services_vector_store_search, backend_services_llm_answer_question, backend_routes_search_ask [INFERRED 0.95]
- **Document indexing flow** — readme_indexing_pipeline, backend_services_parsing_chunk_text, backend_services_embeddings_embed_texts, backend_services_vector_store_build_index [INFERRED 0.95]
- **Spec validation metrics** — spec_retrieval_at_k, spec_answer_reference_coverage, spec_latency_target, spec_embedding_cache_effectiveness, spec_failure_handling, spec_source_precision [EXTRACTED 1.00]

## Communities (15 total, 4 thin omitted)

### Community 0 - "Search and Answer API"
Cohesion: 0.10
Nodes (14): MIN_SCORE similarity threshold 0.52, SearchRequest, reindex(), ask(), retrieve(), search_documents(), answer_question(), generate() (+6 more)

### Community 1 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (24): dependencies, react@^19.3.1, react-dom@^19.3.1, devDependencies, oxlint@^1.90.0, @types/react@^19.3.0, @types/react-dom@^19.3.0, vite@^8.3.6 (+16 more)

### Community 2 - "Embedding and Indexing"
Cohesion: 0.16
Nodes (11): Finding 4: question cache grows forever, cache_key(), embed_texts(), get_model(), record_cache(), chunk_text(), build_index(), search() (+3 more)

### Community 3 - "React Pages"
Cohesion: 0.16
Nodes (15): App(), SourceList(), AdminPage(), handleSave(), handleUpload(), send(), describeIndex(), ERROR_MESSAGES (+7 more)

### Community 4 - "Metrics and Evaluation"
Cohesion: 0.15
Nodes (6): health(), metrics(), track_requests(), record_request(), snapshot(), cache_counts()

### Community 5 - "Document Management API"
Cohesion: 0.19
Nodes (9): DocumentText, edit_document(), find_document(), list_documents(), read_document(), save_document(), upload_document(), decode_text() (+1 more)

### Community 6 - "Project Plan and Records"
Cohesion: 0.14
Nodes (16): Evidence labels (Independent / AI-assisted / AI-generated), Guidely progress log, Non-functional spec targets table, Guidely project brief, Guidely mentor audit 2026-11-11, Milestone roadmap 0-10, check_embeddings test cases, evaluate.py end-to-end evaluation (+8 more)

### Community 7 - "Sample Docs and Tests"
Cohesion: 0.16
Nodes (16): Full-width citation bug (【1】), Finding 9: tests assert exactly 5 documents, Larkfield Employee FAQ, Larkfield Warehouse Order Guide, Larkfield IT Security Rules, Larkfield New Hire Onboarding, Larkfield Returns, Refunds and Shipping Policy, Vacation and Leave Policy (+8 more)

### Community 8 - "Unused Icon Sprite"
Cohesion: 0.25
Nodes (8): bluesky-icon symbol, discord-icon symbol, documentation-icon symbol, github-icon symbol, social-icon symbol, icons.svg SVG Symbol Sprite, Default Vite React template asset (likely unused), x-icon symbol

### Community 9 - "Audit Risks and Limits"
Cohesion: 0.29
Nodes (6): In-browser document edit (GET/PUT /documents/{name}), Finding 1: no authentication on document routes, Finding 2: non-atomic embedding cache write, Finding 3: p95 latency 8.74 s misses target, Developer learning plan (delete doc, p95, prompt injection, explain-back, safe cache), Guidely limitations (no login, .txt only, in-memory metrics)

### Community 10 - "Lint Config"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

## Ambiguous Edges - Review These
- `Larkfield Supplies sample dataset` → `Logistics course video script (unrelated to Guidely)`  [AMBIGUOUS]
  backend/data/sample-docs/VIDEO_SCRIPT_Yousif.txt · relation: conceptually_related_to
- `icons.svg SVG Symbol Sprite` → `Default Vite React template asset (likely unused)`  [AMBIGUOUS]
  frontend/public/icons.svg · relation: rationale_for

## Knowledge Gaps
- **20 isolated node(s):** `Evidence labels (Independent / AI-assisted / AI-generated)`, `In-browser document edit (GET/PUT /documents/{name})`, `Finding 4: question cache grows forever`, `Planned file layout`, `Source precision metric (>=80%)` (+15 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 67 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_index()` connect `Embedding and Indexing` to `Search and Answer API`, `Document Management API`, `Project Plan and Records`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `embed_texts()` (e.g. with `AD-6: Groq for answers, local fastembed for embeddings` and `Finding 2: non-atomic embedding cache write`) actually correct?**
  _`embed_texts()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Evidence labels (Independent / AI-assisted / AI-generated)`, `In-browser document edit (GET/PUT /documents/{name})`, `Finding 4: question cache grows forever` to the rest of the system?**
  _20 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Search and Answer API` be split into smaller, more focused modules?**
  _Cohesion score 0.09848484848484848 - nodes in this community are weakly interconnected._
- **Why does `embed_texts()` connect `Embedding and Indexing` to `Audit Risks and Limits`, `Document Management API`, `Project Plan and Records`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Larkfield Supplies sample dataset` and `Logistics course video script (unrelated to Guidely)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `icons.svg SVG Symbol Sprite` and `Default Vite React template asset (likely unused)`?**
  _Edge tagged AMBIGUOUS (relation: rationale_for) - confidence is low._