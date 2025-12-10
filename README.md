# WorkStream Compass AI (LangChain + OpenAI + Qdrant + Redis) — Monorepo Plan

RAG application designed for **scaling without runaway token costs**.  
Uses **LangChain** for orchestration, **OpenAI API** for embeddings + chat, **Qdrant** for vector search, and **Redis** for shared caching (rewrites, retrieval sets, compressed context, semantic answer cache, rate limits).

> Security note: This blueprint assumes **internal / trusted network** deployment. Do not expose ingest or answer endpoints publicly until auth + authorization are implemented.

---

## At a Glance

| Subsystem | Responsibility | Stack |
|---|---|---|
| `backend/` | API, ingestion, retrieval, caching, streaming | Python (FastAPI) + LangChain |
| `frontend/web/` | Operator UI | Vite + React + Tailwind |
| `frontend/bff/` (optional) | Proxy + sessions + streaming downloads | Node + Express |
| `infra/` | Local dev infra | Docker Compose (Qdrant + Redis) |
| `scripts/` | Dev automation | PowerShell + Python |

---

## Goals

- Fast, accurate internal helpdesk answers with traceable sources
- Hybrid-ish behavior without Postgres FTS: Qdrant semantic retrieval + **document/filename heuristics**
- **Token cost control**: clarify/expand locally, compress context, and cache aggressively
- Operator-friendly UX: onboarding, file hints, source downloads, verbatim snippets

## Non-goals (initially)

- Public multi-tenant SaaS
- Fine-tuning models
- Complex role-based access control (RBAC) (Phase 2)

---

## Architecture

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
