# RAG Learning Path for WorkStream Compass AI

Use this repo as a hands-on lab for RAG, chunking, and evaluation. Each lab ties back to the
actual files and settings in this app so you can learn by changing real code, not toy demos.

## How this repo maps to the RAG pipeline

- Ingest: `backend/app/ingest/loaders.py`, `backend/app/ingest/indexing.py`
- Chunking + metadata: `backend/app/ingest/chunking.py`
- Embedding + indexing: `backend/app/rag/pipeline.py` (`_upsert_chunks`)
- Retrieval: `backend/app/rag/pipeline.py` (`_retrieve_chunks`)
- Rerank: not implemented yet (add after `_retrieve_chunks`)
- Prompt assembly + generation: `backend/app/rag/pipeline.py` (`_answer_from_context`)
- Caching: `backend/app/rag/cache.py`
- Ask endpoint: `backend/app/routers/ask.py`

## Lab 1: Minimal RAG (ingest -> retrieve -> generate)

Goal: prove the end-to-end loop works and see citations.

1) Start Qdrant + Redis (see `README.md` Environment Setup).
2) Run the backend (`uvicorn backend.app.main:app --reload --port 8000`).
3) Drop a few docs into `notes/` and call `POST /refresh`.
4) Ask a question with `/ask` and inspect `sources` and `quotes`.

Learning log:
- What question did you ask?
- Which sources were cited?
- Was the answer grounded in the citations?

## Lab 2: Chunking strategy experiments

Goal: see how chunking quality changes retrieval results.

1) Set `CHUNK_STRATEGY=markdown` (or `auto`) in `backend/.env`.
2) Re-ingest your docs (`POST /refresh`).
3) Compare retrieval quality and the `section_title` metadata fields on chunks.

Tune these settings:
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `CHUNK_STRATEGY` (recursive vs markdown)

Where it happens:
- `backend/app/ingest/chunking.py` uses `MarkdownHeaderTextSplitter` for `.md`
- Metadata includes `section_title`, `h1`, `h2`, `h3`, `source_extension`

Learning log:
- What size/overlap worked best for your documents?
- Did section-aware chunking improve answers?

## Lab 3: Metadata filters (precision vs recall)

Goal: see how metadata changes retrieval precision.

You can now pass filters to `/ask` that match chunk metadata fields:

```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"reset voicemail","filters":{"source_extension":".pdf"}}'
```

Common filters you can try:
- `filename`
- `source_extension`
- `section_title`
- `h1`, `h2`, `h3`

Learning log:
- Which filters reduced noise?
- Did you lose recall when filters were too strict?

## Lab 4: Prompt grounding and refusal

Goal: enforce "answer only from context" behavior.

Edit `backend/app/rag/prompts.py`:
- tighten the grounding language
- add explicit refusal rules
- require citations in every answer

Learning log:
- Did hallucinations go down?
- Did the model refuse too often?

## Lab 5: Evaluation loop (Recall@k, MRR)

Goal: measure retrieval quality instead of guessing.

1) Create an eval set using `docs/rag-eval-golden-set.sample.json`.
2) Run the script:

```bash
python scripts/eval_rag.py --data docs/rag-eval-golden-set.sample.json
```

3) Track Recall@k and MRR over time as you tweak chunking and prompts.

Learning log:
- What was your baseline Recall@k and MRR?
- Which change improved them the most?

## Decision framework: RAG vs fine-tuning vs prompting

- Use RAG for knowledge (dynamic, auditable, source grounded).
- Use fine-tuning for behavior (format, tone, policies).
- Use prompting for fast iteration and early experiments.

Rule of thumb: knowledge changes -> RAG, behavior changes -> fine-tuning.

## Learning log template

```text
Experiment:
Hypothesis:
Change:
Docs / data used:
Metrics (Recall@k, MRR, faithfulness notes):
Result:
Next step:
```
