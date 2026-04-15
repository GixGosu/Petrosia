# Petrosia — Project Manifest

> Last updated: 2026-04-14
> Update this file when architecture, files, or known issues change.

## What This Is

Knowledge base with a REST API. Search or ask questions. AI tools consume answers, not raw documents. Supports local LLM (Ollama) and cloud providers (Claude, OpenAI, Gemini, Mistral) interchangeably per-request. Multi-tenant via namespace-scoped API keys.

## Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), pgvector
- **Database:** PostgreSQL 16 + pgvector extension
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, always local)
- **LLM:** Multi-provider — Claude, OpenAI, Gemini, Mistral, Ollama (selectable per-request)
- **Frontend:** Vanilla JavaScript (no build step, no frameworks)
- **Auth:** API key with permissions (read/write/admin) + namespace scoping
- **Rate Limiting:** slowapi (per-key or per-IP)
- **Infra:** Docker Compose (postgres + backend + ollama)

## File Map

```
backend/
  main.py              — FastAPI app. 21 endpoints. CORS, rate limiting (slowapi), startup seed. Ingestion endpoints (markdown, CSV, bulk).
  config.py            — Pydantic BaseSettings. DB URLs, LLM keys, embedding config, CORS, RAG thresholds, REQUIRE_API_KEY, rate limits.
  database.py          — Async SQLAlchemy engine (pool_size=10, max_overflow=20). init_db() creates tables + pgvector ext.
  models.py            — 5 SQLAlchemy models (Article, ArticleContent, ArticleVersion, ChatHistory, ApiKey) + 12 Pydantic schemas.
  auth.py              — API key auth. generate/hash keys, get_api_key dependency, require_read/write/admin. AnonymousKey fallback when auth disabled.
  seed_data.py         — 3 articles (password-reset, getting-started, billing-faq) x 3 languages (en/es/fr).
  requirements.txt     — 23 deps. Key: fastapi, sqlalchemy, pgvector, anthropic, openai, sentence-transformers, slowapi, pyyaml.
  Dockerfile           — Python 3.11-slim. Installs PyTorch CPU + sentence-transformers. ~2GB image.
  llm/
    base.py            — BaseLLMProvider ABC. Two methods: stream_chat(), generate_embedding().
    factory.py         — get_llm_provider(provider, model) factory. Cached by (provider, model) tuple. Uses settings for defaults.
    claude.py          — Anthropic SDK, async streaming.
    openai.py          — OpenAI SDK, async streaming.
    gemini.py          — Google genai SDK. Note: uses sync-in-async pattern.
    mistral.py         — Mistral SDK. Note: uses sync-in-async pattern.
    ollama.py          — httpx-based. Calls /api/chat and /api/embeddings.
    __init__.py        — Re-exports all providers.
  services/
    __init__.py        — get_embedding_model() singleton (SentenceTransformer). Re-exports services.
    articles.py        — ArticleService. CRUD, embedding generation, version history, bulk create, namespace filtering. Async executor for embeddings.
    search.py          — SearchService. pgvector cosine similarity search. Namespace-scoped. Default threshold 0.5, chat uses 0.3.
    chat.py            — ChatService. RAG pipeline: _prepare_rag_context() -> stream or collect. generate_answer() for /api/ask. Language auto-detection. Uses llm.factory (no duplicate).

widget/
  widget.js            — 479 lines. IIFE, self-contained. SSE streaming. Config via data attributes.
  demo.html            — Demo page that loads widget.js.

admin/
  index.html           — Admin SPA shell. Nav, views (articles, editor, search, analytics).
  app.js               — 412 lines. Article list, editor with language tabs, search test, analytics.
  styles.css           — Admin styling.

docker-compose.yml     — 4 services: db (pgvector/pgvector:pg16), backend (builds ./backend), ollama (ollama/ollama), ollama-pull (one-shot model pull).
init.sql               — DDL for 5 tables + indexes + migrations (namespace, model column, slug constraint swap). Safe for re-runs (IF NOT EXISTS/IF EXISTS guards).
.env.example           — Env template. DEFAULT_LLM_PROVIDER=ollama. Cloud keys commented out.
```

## Data Model

```
articles (1) ──→ (N) article_content (per language)
                       └──→ (N) article_versions (history snapshots)

api_keys (standalone, scoped by namespace + permissions)
chat_history (standalone, tracks queries + responses + sources + model used)
```

- Embeddings: 384-dim vectors (MiniLM-L6-v2) stored in article_content.embedding
- Namespace: articles.namespace scopes data per API key
- Unique constraint: (slug, namespace) — same slug allowed in different namespaces

## API Endpoints (21)

```
Ask:        POST /api/ask (JSON response with answer, sources, grounded, confidence)
Chat:       POST /api/chat (SSE streaming), GET /api/chat/history
Search:     GET /api/search?q=&lang=, POST /api/search/semantic
Articles:   POST/GET /api/articles, GET/PUT/DELETE /api/articles/{slug}[/{lang}]
Ingestion:  POST /api/articles/bulk, POST /api/ingest/markdown, POST /api/ingest/csv
Models:     GET /api/models, GET /api/providers
Admin:      POST/GET /api/admin/keys, DELETE /api/admin/keys/{id}
Utility:    GET /api/health, GET /api/health/llm
Static:     GET /widget-demo, GET /admin, GET /
```

## Key Patterns

- **LLM Provider Abstraction:** BaseLLMProvider → 5 implementations → cached factory. Switch provider+model per request.
- **Non-Streaming Answer:** POST /api/ask collects full LLM response, returns JSON with groundedness signal. THE primary integration endpoint.
- **Streaming RAG:** POST /api/chat streams via SSE for the widget. Same RAG pipeline, different delivery.
- **API Key Auth:** X-API-Key header, permissions (read/write/admin), namespace scoping. Off by default (REQUIRE_API_KEY=false).
- **Namespace Isolation:** API keys scoped to namespace. All queries filter by namespace. Multi-tenant on single deployment.
- **One-Call Updates:** PUT /api/articles/{slug}/{lang} updates content + regenerates embedding + saves version.
- **Bulk Ingestion:** JSON array, markdown files (YAML frontmatter), or CSV upload.
- **Rate Limiting:** slowapi, per-key or per-IP. Configurable via RATE_LIMIT_READS/WRITES.

## Known Issues / Tech Debt

- Gemini and Mistral providers use sync-in-async pattern (will block event loop under load)
- No tests
- Docker image is ~2GB due to PyTorch (could be reduced with ONNX runtime)
- hybrid_search() in search.py just delegates to semantic_search() — BM25 not implemented
- /api/models returns different structure than ProviderInfo schema (works but inconsistent)

## What's Been Done

- [x] Core platform (API, DB, embeddings, RAG)
- [x] Multi-provider LLM support (5 providers, selectable per-request)
- [x] Non-streaming /api/ask endpoint with groundedness + confidence
- [x] API key auth with permissions and namespace scoping
- [x] Bulk ingestion (JSON, markdown, CSV)
- [x] Rate limiting (slowapi)
- [x] Chat widget (embeddable, streaming)
- [x] Admin interface (articles, editor, search, analytics)
- [x] Docker deployment with Ollama bundled
- [x] Provider factory consolidated (no duplicate code)
- [x] Open-source cleanup + MIT license
- [x] Generic seed data (password-reset, getting-started, billing-faq)

## What's Next (Not Started)

- [ ] Integration guides (ChatGPT Actions, Claude Projects, Claude Code hooks)
- [ ] Tests (pytest, API integration tests)
- [ ] Docker image size reduction (ONNX runtime instead of PyTorch)
- [ ] BM25/full-text hybrid search
- [ ] CLI tool for querying from terminal
- [ ] Admin UI updates for auth management and namespace switching
