# WorkStream Compass AI

LangChain + OpenAI + Qdrant + Redis blueprint for internal RAG that scales **without runaway token costs**. The goal is a pragmatic monorepo pattern you can clone, trim, or extend for your own helpdesk or SOP assistant.

> Security note: assume an internal, trusted network. Lock down ingest/answer endpoints before moving outside the firewall or adding multi-tenant users.

---

## Highlights

- Fast answers with auditable sources and verbatim snippets when policy demands exact wording.
- Hybrid retrieval feel (semantic + filename/metadata heuristics) without Postgres FTS.
- Aggressive cost controls: local rewrites, context compression, and Redis-backed caching.
- Operator-focused UX: onboarding hints, file discovery, traceable downloads.

### Stack at a Glance

| Subsystem                  | Responsibility                                | Stack                           |
| -------------------------- | --------------------------------------------- | ------------------------------- |
| `backend/`                 | API, ingestion, retrieval, caching, streaming | Python (FastAPI) + LangChain    |
| `frontend/web/`            | Operator UI                                   | Vite + React + Tailwind         |
| `frontend/bff/` (optional) | Proxy, sessions, streaming downloads          | Node + Express                  |
| `infra/`                   | Local Qdrant + Redis                          | Docker Compose                  |
| `scripts/`                 | Dev automation                                | PowerShell + Python             |

---

## Goals & Non-goals

**Goals**
- High-quality internal helpdesk answers with citations.
- Operate efficiently: local query rewrites, compressed context packs, reuse via caching.
- Smooth operator tooling: file hints, downloads, onboarding flows.

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
2. Loader extracts text (PDF/DOCX/XLSX/CSV/MD/TXT, OCR optional).
3. Text normalizes and chunks (size/overlap configurable).
4. OpenAI embeddings are generated.
5. Chunks upsert into Qdrant with metadata linking back to the file.
6. Redis invalidates file lists, retrieval sets, and cached answers.

**Ask**
1. Normalize the query (case, tokens, heuristics).
2. Clarify/expand locally (rules, classifier, or short rewrite call).
3. Retrieve top-K chunks from Qdrant.
4. Compress context into “facts / steps / constraints” while keeping citations.
5. Generate the answer via OpenAI chat.
6. Return answer + citations + quoted snippets.
7. Cache retrieval + answer artifacts in Redis.

---

## Redis Responsibilities

| Bucket              | Purpose                                                   | Suggested TTL |
| ------------------- | --------------------------------------------------------- | ------------- |
| Rewrite cache       | Normalized query → clarified intent + rewritten query     | 1–7 days      |
| Retrieval cache     | Rewritten query → chunk IDs + scores                      | 1–24 hours    |
| Compression cache   | Query + chunk IDs → compressed context pack               | 15 min–6 hrs  |
| Semantic answer     | Query embedding hash → answer + citations                 | 5 min–24 hrs  |
| File list cache     | Cached file metadata listings                             | 30–120 sec    |
| Rate/in-flight data | Token budgets, dedupe locks, session metadata             | Policy based  |

---

## API Surface (planned)

| Route           | Method | Purpose                                                   | Notes                      |
| --------------- | ------ | --------------------------------------------------------- | -------------------------- |
| `/health`       | GET    | Basic health plus Qdrant/Redis status                     |                            |
| `/files`        | GET    | List known docs from local index + Qdrant metadata        |                            |
| `/files/search` | GET    | Fuzzy filename search for UI hints                        |                            |
| `/source`       | GET    | Stream original file bytes from `NOTES_DIR`               | Auth recommended           |
| `/source_text`  | GET    | Return normalized extracted text                          |                            |
| `/refresh`      | POST   | Rescan `NOTES_DIR` and upsert into Qdrant                 | Webhook or manual trigger  |
| `/upload`       | POST   | Upload + ingest file(s)                                   | Multipart                  |
| `/ask`          | POST   | Main RAG endpoint (`mode=answer` or `mode=verbatim`)      | JSON body                  |
| `/ask_stream`   | POST   | NDJSON/SSE stream of the answer                           | UI typing indicators       |

Optional BFF proxies these as `/api/*` and handles download streaming/session auth.

---

## Repo Structure (suggested)

```
helpdesk-rag/
  backend/
    app/
      main.py
      api/
        routes_ask.py
        routes_files.py
        routes_ingest.py
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
QDRANT_COLLECTION=helpdesk_chunks

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

[RAG Controls]
TOP_K=10
MAX_CONTEXT_TOKENS=2500
VERBATIM_DEFAULT=0

[OCR]
OCR_ENABLED=1
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

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

## Local Development

1. **Start infra** (Qdrant + Redis)  
   ```bash
   cd infra
   docker compose up -d
   ```
2. **Backend**
   ```bash
   python -m venv venv
   ./venv/Scripts/pip install -r backend/requirements.txt
   ./venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000
   ```
3. **Frontend (React)**
   ```bash
   cd frontend/web
   npm install
   npm run dev
   ```
4. **Smoke test**
   - `GET http://localhost:8000/health`
   - Upload: `POST /upload`
   - Ask: `POST /ask {"query": "How do I reset voicemail?", "mode": "answer"}`

---

## LangChain Implementation Notes

- Use file-type aware loaders; ensure parity between ingestion + refresh.  
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

---

## Roadmap

**Phase 1 (MVP)**  
- Ingest → Qdrant, ask → retrieve → compress → generate.  
- Redis caching (rewrite, retrieval, answers).  
- Basic UI with file hints and downloads.  

**Phase 2 (Production hardening)**  
- Auth + roles, per-department access.  
- Observability (metrics, tracing).  
- Strong PHI/PII handling + audit logging.  
- Multi-instance deployment across environments.  
