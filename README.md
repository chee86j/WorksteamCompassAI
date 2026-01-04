# WorkStream Compass AI

LangChain + OpenAI + Qdrant + Redis blueprint for departmental or personal work assistants that scale **without runaway token costs**. The goal is a pragmatic monorepo pattern you can clone, trim, or extend for your own team knowledge assistant or SOP companion—whether you deploy it internally or call hosted OpenAI models directly.

> Security note: even if you expose this beyond an internal, trusted network, make sure ingest/answer endpoints are locked down before inviting multi-tenant users.

---

## Highlights

- Fast answers with auditable sources and verbatim snippets when policy demands exact wording.
- Hybrid retrieval feel (semantic + filename/metadata heuristics) without Postgres FTS.
- Aggressive cost controls: local rewrites, context compression, and Redis-backed caching.
- Operator-focused UX: onboarding hints, file discovery, traceable downloads.

## RAG Learning Path

If you want to use this app as a hands-on RAG course (chunking, retrieval, reranking, eval loops),
start with the guided labs in `docs/rag-learning-path.md`.

### Stack at a Glance

| Subsystem                  | Responsibility                                | Stack                        |
| -------------------------- | --------------------------------------------- | ---------------------------- |
| `backend/`                 | API, ingestion, retrieval, caching, streaming | Python (FastAPI) + LangChain |
| `frontend/web/`            | Operator UI                                   | Vite + React + Tailwind      |
| `frontend/bff/` (optional) | Proxy, sessions, streaming downloads          | Node + Express               |
| `infra/`                   | Local Qdrant + Redis                          | Docker Compose               |
| `scripts/`                 | Dev automation                                | PowerShell + Python          |

---

## Goals & Non-goals

**Goals**

- High-quality departmental/personal assistant answers with citations.
- Operate efficiently: local query rewrites, compressed context packs, reuse via caching.
- Smooth operator tooling: file hints, downloads, onboarding flows.
- Production-grade RAG pipeline: vector DB with rich metadata, ingestion/resync parity, and auditable lineage.
- Keep the architecture clean so Slack/Teams/CRM/ticketing hooks can drop in without major refactors.

**Non-goals (initially)**

- Public multi-tenant SaaS footprint.
- Fine-tuning foundation models.
- Full RBAC matrix (pushed to Phase 2).

---

## System Overview

```txt
React UI (frontend/web)  ->  /api/*  ->  (optional) Express BFF  ---------+
                                                                         |
                                                                  FastAPI backend
                                                           (/ask, /ask_stream, /upload,
                                                            /files, /source, /refresh)
                                                                         |
                                     NOTES_DIR -> loaders -> chunker -> embeddings (OpenAI)
                                                                         |
                                                           +-------------+-------------+
                                                           |                           |
                                                      Qdrant Vector DB             Redis Cache
                                                   (chunks + metadata)     (rewrites/retrieval/answers,
                                                                             rate limits, sessions)
```

### Storage Strategy

- **Qdrant**: vectorized chunks + metadata (doc id, filename, page, offsets, hash).
- **Local disk (`NOTES_DIR`)**: original files + extracted text artifacts.
- **Redis**: coordination + shared cache for rewrites, retrieval, compression, answers, and rate limits.

### Core Flow

**Ingestion**

1. File arrives via drop into `NOTES_DIR` + `POST /refresh`, or via `POST /upload`.
2. Loader extracts text (PDF/DOCX/XLSX/CSV/MD/TXT/LOG, OCR optional).
3. Text normalizes and chunks (size/overlap configurable).
4. OpenAI embeddings are generated.
5. Chunks upsert into Qdrant with metadata linking back to the file.
6. Redis invalidates file lists, retrieval sets, and cached answers.

**Ask**

1. Normalize the query (case, tokens, heuristics).
2. Clarify/expand locally (rules, classifier, or a short LLM rewrite chain) to normalize abbreviations, tag entities, and detect intent.
3. Retrieve top-K chunks from Qdrant with metadata filters (department/system/tag) when available.
4. Compress context into “facts / steps / constraints” while keeping citations and chunk IDs.
5. Generate the answer via OpenAI chat, honoring `mode=answer` vs `mode=verbatim`.
6. Return answer + citations + quoted snippets plus latency/token metadata.
7. Cache rewrite/retrieval/context/answer artifacts in Redis (subject to TTL + invalidation rules).

Example response:

```json
{
  "answer": "...",
  "mode": "answer",
  "sources": ["telecom-voicemail-policy.pdf#p12_c4"],
  "quotes": ["\"Dial *86 ...\""],
  "metadata": {
    "model": "gpt-4.1-mini",
    "latency_ms": 1200,
    "tokens_input": 1800,
    "tokens_output": 400
  }
}
```

---

## Redis Responsibilities

| Bucket              | Purpose                                               | Suggested TTL |
| ------------------- | ----------------------------------------------------- | ------------- |
| Rewrite cache       | Normalized query → clarified intent + rewritten query | 1–7 days      |
| Retrieval cache     | Rewritten query → chunk IDs + scores                  | 1–24 hours    |
| Compression cache   | Query + chunk IDs → compressed context pack           | 15 min–6 hrs  |
| Semantic answer     | Query embedding hash → answer + citations             | 5 min–24 hrs  |
| File list cache     | Cached file metadata listings                         | 30–120 sec    |
| Rate/in-flight data | Token budgets, dedupe locks, session metadata         | Policy based  |

Key patterns (illustrative): `rewrite:{hash(query_norm)}`, `retrieve:{hash(rewritten_query)}:{k}`, `compress:{hash(rewritten_query)}:{hash(chunk_ids)}`, and `answer:{hash(rewritten_query)}:{model}:{mode}`. Locks such as `inflight:{hash(rewritten_query)}` keep 20 identical questions from triggering 20 OpenAI calls while caches expire based on document churn.

---

## API Surface (planned)

| Route           | Method | Purpose                                              | Notes                     |
| --------------- | ------ | ---------------------------------------------------- | ------------------------- |
| `/health`       | GET    | Basic health plus Qdrant/Redis status                |                           |
| `/files`        | GET    | List known docs from local index + Qdrant metadata   |                           |
| `/files/search` | GET    | Fuzzy filename search for UI hints                   |                           |
| `/source`       | GET    | Stream original file bytes from `NOTES_DIR`          | Auth recommended          |
| `/source_text`  | GET    | Return normalized extracted text                     |                           |
| `/refresh`      | POST   | Rescan `NOTES_DIR` and upsert into Qdrant            | Webhook or manual trigger |
| `/upload`       | POST   | Upload + ingest file(s)                              | Multipart                 |
| `/ask`          | POST   | Main RAG endpoint (`mode=answer` or `mode=verbatim`) | JSON body                 |
| `/ask_stream`   | POST   | NDJSON/SSE stream of the answer                      | UI typing indicators      |

Optional BFF proxies these as `/api/*` and handles download streaming/session auth.

---

## Repo Structure (suggested)

```
workspace-assistant/
  backend/
    app/
      main.py
      api/
        routes_ask.py
        routes_files.py
        routes_ingest.py
        routes_health.py
        routes_source.py
        routes_source_text.py
      rag/
        pipeline.py            # LangChain runnable graph
        retriever.py           # Qdrant + metadata filters
        compressor.py          # Context compression logic
        prompts.py             # Prompt templates
        cache.py               # Redis helpers (keys/TTLs/locks)
      ingest/
        loaders.py             # PDF/DOCX/XLSX/etc
        chunking.py
        ocr.py                 # Optional
        indexing.py            # File index + metadata
      utils/
        hashing.py
        normalize.py
        logging.py
    requirements.txt
    .env.example
  frontend/
    web/
      src/
      .env.example
      package.json
    bff/ (optional)
      src/server.js
      .env.example
      package.json
  infra/
    docker-compose.yml         # Qdrant + Redis
  docs/                        # RAG learning path + eval sets
  scripts/
    dev.ps1
    stop.ps1
    ingest.ps1
  notes/                       # Default NOTES_DIR (gitignored)
  README.md
```

---

## Environment Variables

```
Backend (backend/.env)

[OpenAI]
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBED_MODEL=text-embedding-3-large
OPENAI_TIMEOUT_SEC=60

[Qdrant]
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=workspace_chunks

[Redis]
REDIS_URL=redis://localhost:6379/0
CACHE_REWRITE_TTL_SEC=86400
CACHE_RETRIEVAL_TTL_SEC=3600
CACHE_COMPRESS_TTL_SEC=1800
CACHE_ANSWER_TTL_SEC=900

[Docs]
NOTES_DIR=../notes
ALLOWED_EXTS=.pdf,.docx,.xlsx,.csv,.md,.txt,.log

[Chunking]
CHUNK_SIZE=700
CHUNK_OVERLAP=80
CHUNK_STRATEGY=recursive   # recursive | markdown | auto

[RAG Controls]
TOP_K=10
MAX_CONTEXT_TOKENS=2500
VERBATIM_DEFAULT=0

[OCR]
OCR_ENABLED=1
TESSERACT_CMD=/usr/bin/tesseract        # Linux
# or C:\Program Files\Tesseract-OCR\tesseract.exe on Windows

Frontend (frontend/web/.env)
VITE_API_BASE=/api          # or http://localhost:8000 when hitting backend directly
VITE_LOGO_URL=/your-logo.svg

BFF (frontend/bff/.env)
PORT=3001
BACKEND_URL=http://localhost:8000
CORS_ORIGIN=http://localhost:5173
SESSION_SECRET=change-me
```

---

## Local Infra Bootstrap (WS-102)

**Prerequisites**

- Docker Desktop (macOS/Windows) or Docker Engine plus the Compose plugin (Linux)
- `curl` for HTTP checks (preinstalled on macOS/Linux/Windows 10+)
- `redis-cli` (install via `brew install redis`, `apt install redis-tools`, `choco install redis-64`, or run `docker exec -it compass_redis redis-cli`)
- No hosted accounts are needed; Qdrant and Redis both run as local Docker containers.

Qdrant exposes REST on `http://localhost:6333` and gRPC on `6334`. Redis listens on `redis://localhost:6379`.

### Start, stop, and verify

```bash
./scripts/start-data-plane.sh        # or: pwsh scripts/start-data-plane.ps1
./scripts/check-data-plane.sh        # curl + redis-cli probes
./scripts/stop-data-plane.sh         # or: pwsh scripts/stop-data-plane.ps1
```

Raw Compose commands for reference:

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml down
```

Manual health checks (also run by `check-data-plane`):

```bash
curl http://localhost:6333/healthz
redis-cli -p 6379 ping
```

### Troubleshooting

- **Port already allocated (`6333` or `6379`)**: stop the conflicting process (`docker ps`, `lsof -i :6333`) or edit the host-side ports in `infra/docker-compose.yml`.
- **Stale/corrupt volumes**: remove them via `docker volume rm worksteamcompassai_qdrant_storage worksteamcompassai_redis_storage` (check actual names with `docker volume ls`) and rerun the start script.
- **Compose errors**: upgrade Docker Desktop/Engine so `docker compose` understands file format `3.8`.
- **Missing `redis-cli`**: install it locally or exec into the container with `docker exec -it compass_redis redis-cli ping`.

---

## Backend Skeleton (WS-103)

- FastAPI app lives under `backend/app/main.py` with routers split into `ask`, `files`, `health`, and `ingest`.
- Configuration uses `backend/app/core/settings.py` (`pydantic.BaseSettings`), so fill `backend/.env` or rely on defaults shown above.
- Logging is pre-wired; run the API locally via `uvicorn backend.app.main:app --reload --port 8000`.
- Available routes today (stub implementations): `GET /health`, `POST /ask`, `POST /ask_stream`, `GET /files`, `POST /refresh`, and `POST /upload`.
- Utility helpers (`backend/app/utils/normalize.py`, `backend/app/utils/hashing.py`) centralize query normalization and manifest hashing for upcoming ingestion work.

---

## Environment Setup (WS-104)

1. **Create backend/.env**

   The backend uses `pydantic.BaseSettings`, so add the required environment variables to `backend/.env`:

   ```bash
   cat > backend/.env <<'EOF'
   OPENAI_API_KEY=sk-your-key-here

   # Optional overrides (defaults shown)
   OPENAI_CHAT_MODEL=gpt-4.1-mini
   OPENAI_CHAT_TEMPERATURE=0.2
   OPENAI_CHAT_MAX_TOKENS=600
   OPENAI_TIMEOUT_SEC=60
   OPENAI_EMBED_MODEL=text-embedding-3-large
   OPENAI_EMBED_DIMENSION=3072

   QDRANT_URL=http://localhost:6333
   REDIS_URL=redis://localhost:6379/0

   NOTES_DIR=../notes
   ALLOWED_EXTS=.pdf,.docx,.xlsx,.csv,.md,.txt,.log
   EOF
   ```

   - `OPENAI_API_KEY` is mandatory for embeddings + chat generation.
   - `QDRANT_URL` / `REDIS_URL` default to the local Docker compose endpoints.
   - `NOTES_DIR` must exist (create `notes/` at the repo root) and holds uploaded files.

2. **Start the local data plane**

   ```bash
   ./scripts/start-data-plane.sh
   # or: pwsh scripts/start-data-plane.ps1
   ```

   This launches Qdrant + Redis and exposes health checks on `http://localhost:6333/healthz` and `redis://localhost:6379`.

3. **Install backend dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

4. **Run the FastAPI server**

   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

   On startup the app will connect to Redis/Qdrant, ensure the collection exists, and initialize the ingestion/RAG pipeline.

5. **Load documents**

   - Drop files into `notes/` and call `POST /refresh` to ingest everything in the directory, **or**
   - Call `POST /upload` with multipart files; they are saved into `NOTES_DIR` and ingested automatically.

6. **Ask questions**

   Use `POST /ask` or `POST /ask_stream` after ingestion completes:

   ```bash
   curl -X POST http://localhost:8000/ask \
     -H 'Content-Type: application/json' \
     -d '{"query":"Where is the PTO policy?","mode":"answer"}'
   ```

## Local Development

1. **Start infra** (Qdrant + Redis) – see Environment Setup step 2.
2. **Backend**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   uvicorn backend.app.main:app --reload --port 8000
   ```
3. **Frontend (React)**
   ```bash
   cd frontend/web
   npm install
   npm run dev
   ```
4. **Optional BFF**
   ```bash
   cd frontend/bff
   npm install
   npm run dev
   ```
5. **Smoke test**
   - `GET http://localhost:8000/health`
   - Upload: `POST /upload`
   - Refresh: `POST /refresh`
   - Ask: `POST /ask {"query": "How do I reset voicemail?", "mode": "answer"}`

---

## LangChain Implementation Notes

- Use file-type aware loaders; ensure parity between ingestion + refresh.
- Normalize extracted text (line endings/whitespace) before chunking so hashes stay stable.
- Prefer token-aware splitter so chunk size stays stable across formats.
- Embeddings: OpenAI embeddings; swap for Azure/Open-source if policy requires.
- Retrieval: QdrantVectorStore with optional metadata filters (department/system/file tags).
- Compression: convert retrieved chunks into bullet facts + step blocks + constraints; retain citations `{doc_id, filename, chunk_id, offsets/page}`.
- Generation: enforce “If the info is not present in sources, say so.”; return `{answer, sources[], quotes[]}` payload.

---

## Cost & Token Controls

- Minimize input tokens via local rewrite + compression before hitting GPT.
- Cache rewrite, retrieval, compression, and semantic answers (Redis) to prevent duplicate spend.
- Use in-flight dedupe locks so burst traffic does not trigger repeated OpenAI calls.
- Enforce rate limits per user/department, plus max context/output tokens.
- Provide verbatim snippets fallback for SOP-style questions to keep responses short.

---

## Security Posture

- Phase 1: private network only, VPN/firewall required.
- Before Phase 2: add auth (SSO/OIDC), per-department access controls, audit logging, and PHI/PII policy.
- Confirm org policy for OpenAI usage; insert redaction layer if files may contain PHI/PII.

---

## Testing & Validation

- **Unit tests**: chunking determinism, cache key + TTL correctness, loader extraction quality.
- **Integration tests**: Qdrant upsert/retrieval, Redis cache hit/miss, `/upload → /ask → /source` happy path.
- **Golden set**: canonical queries must surface known sources; verbatim requests must return exact steps.
- **Eval harness**: run `python scripts/eval_rag.py --data docs/rag-eval-golden-set.sample.json` to track Recall@k and MRR.

  ```json
  [
    {
      "query": "How do I reset my voicemail PIN?",
      "expected_sources": ["telecom-voicemail-policy.pdf"],
      "mode": "answer",
      "must_have_verbatim": true
    }
  ]
  ```

Use the golden set to compare prompt/routing adjustments, validate new versions before deploy, and flag regressions in latency or accuracy.

---

## Roadmap

**Phase 1 (MVP)**

- Qdrant-based RAG pipeline.
- LangChain chains for ingestion, retrieval, compression, and generation.
- Redis caching (rewrite, retrieval, answer).
- React operator UI with:
  - onboarding,
  - suggestion buttons,
  - file hints and downloads,
  - answer + citations.

**Phase 2 (Advanced Features)**

- Agent tools (ticket creation, notifications, internal APIs).
- Slack/Teams integration.
- Simple analytics dashboard (usage, latency, “no answer” rate).
- A/B tests for prompts and model settings.
- Optional fine-tuning or specialized small models for classification/routing.

**Phase 3 (Enterprise Hardening)**

- SSO/OIDC integration
- Per-department collections and policies
- Full observability (metrics, tracing, alerting).
- Governance documentation and risk assessments.
