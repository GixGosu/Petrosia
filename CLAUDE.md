# Petrosia

Knowledge base with a REST API. Search or ask questions. Your AI tools consume answers, not raw documents.

## Running the Project

```bash
docker-compose up --build
```

First startup pulls the Ollama model (~2GB), seeds sample articles, and prints a bootstrap admin API key to the logs. To nuke and restart fresh:

```bash
docker-compose down -v && docker-compose up --build
```

## Architecture

- **Backend:** FastAPI (Python 3.11), async SQLAlchemy, pgvector
- **Database:** PostgreSQL 16 + pgvector for semantic search
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, always local, no API cost)
- **LLM:** Multi-provider per-request — Ollama (default/local), Claude, OpenAI, Gemini, Mistral
- **Frontend:** Vanilla JS admin UI + embeddable chat widget (no build step)
- **Auth:** API key with permissions (read/write/admin) + namespace scoping

## Key Files

```
backend/
  main.py        — FastAPI app, 21 endpoints, rate limiting, startup seed
  config.py      — Pydantic settings (env vars)
  models.py      — SQLAlchemy models + Pydantic schemas
  auth.py        — API key auth (prefix: ptr_)
  seed_data.py   — Sample articles seeded on first run
  services/
    chat.py      — RAG pipeline: context retrieval + LLM answer generation
    search.py    — Semantic + hybrid search with pgvector
    articles.py  — Article CRUD + bulk operations + embedding generation
  llm/
    factory.py   — Provider factory (ollama, claude, openai, gemini, mistral)
    base.py      — Abstract LLM provider interface
docker-compose.yml — Postgres + Ollama + Backend
init.sql           — Schema DDL with migrations
```

## Common Tasks

### Add articles to the knowledge base

```bash
# Single article
curl -X POST http://localhost:8000/api/articles \
  -H "Content-Type: application/json" \
  -d '{"slug": "my-article", "content": {"en": {"title": "My Article", "body": "Full article content..."}}}'

# Bulk import
curl -X POST http://localhost:8000/api/articles/bulk \
  -H "Content-Type: application/json" \
  -d '{"articles": [...]}'

# From markdown files
curl -X POST http://localhost:8000/api/ingest/markdown -F "files=@docs/article.md"

# From CSV
curl -X POST http://localhost:8000/api/ingest/csv -F "file=@data.csv"
```

### Ask a question

```bash
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I reset my password?"}' | python3 -m json.tool
```

### Use a specific LLM provider

```bash
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "provider": "claude", "model": "claude-sonnet-4-20250514"}'
```

Cloud providers need API keys in `.env` — see `.env.example`.

### Manage API keys

Auth is off by default. A bootstrap admin key is printed to logs on first startup. Enable auth with `REQUIRE_API_KEY=true` in `.env`.

```bash
# Create a key
curl -X POST http://localhost:8000/api/admin/keys \
  -H "X-API-Key: ptr_your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "permissions": ["read"], "namespace": "default"}'
```

## Testing

```bash
# Health check
curl http://localhost:8000/api/health

# LLM status
curl http://localhost:8000/api/health/llm

# Search
curl "http://localhost:8000/api/search?q=password+reset"

# Interactive API docs
open http://localhost:8000/docs
```

## Important Notes

- Embeddings are always generated locally — no API cost for search or ingestion
- LLM provider is chosen per-request via `provider` and `model` fields
- The `/api/ask` endpoint is the primary product endpoint (JSON response with sources)
- The `/api/chat` endpoint is SSE streaming for the chat widget
- Namespace scoping enables multi-tenant knowledge bases on a single deployment
- Article slugs are unique per namespace, not globally
