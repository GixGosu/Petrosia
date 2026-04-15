<p align="center">
  <img src="docs/petrosia-sponge.jpg" alt="Petrosia" width="200">
</p>

# Petrosia

Knowledge base with a REST API. Search or ask questions. Your AI tools consume answers, not raw documents.

<p align="center">
  <img src="docs/petrosia-example.png" alt="Petrosia Demo" width="700">
</p>

## Quick Start

```bash
git clone <repo-url> && cd petrosia
```

### With an AI Coding Assistant (recommended)

The fastest path. Clone the repo, open your AI coding CLI, and talk to it:

```bash
# Claude Code
claude

# Codex
codex

# Any CLI that reads project files works — the CLAUDE.md and README
# give the assistant everything it needs to understand the project.
```

Then just ask it things in natural language:

- **"Spin up the project and explain how it works"** — it will run `docker-compose up --build`, read the architecture, and walk you through it
- **"Add our company's FAQ to the knowledge base"** — it will use the bulk import or markdown ingestion endpoints to load your content
- **"Ask Petrosia how to reset a password"** — it will curl `/api/ask` and show you the grounded answer
- **"Set up Claude as the LLM provider"** — it will configure `.env` with your API key and show you how to specify `"provider": "claude"` per request
- **"Create a read-only API key for our frontend app"** — it will hit the admin endpoint and hand you the key

The API is designed so that AI assistants can discover and use every endpoint from the OpenAPI spec at `/docs`.

### Manual Setup

```bash
docker-compose up --build
```

Open [http://localhost:8000/admin](http://localhost:8000/admin) to manage articles, or [http://localhost:8000/widget-demo](http://localhost:8000/widget-demo) to try the chat widget.

First startup pulls the Ollama model (~2GB), seeds sample articles, and prints a bootstrap admin API key to the logs. No external API keys required.

## Ask a Question

The `/api/ask` endpoint is the core product. Send a question, get a grounded answer with sources:

```bash
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I reset my password?"}' | python3 -m json.tool
```

```json
{
  "answer": "To reset your password, go to the login page and click 'Forgot Password'...",
  "sources": [{"slug": "password-reset", "title": "How to Reset Your Password", "score": 0.82}],
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "grounded": true,
  "confidence": 0.82
}
```

- `grounded: true` means the answer is based on your knowledge base, not hallucinated
- `confidence` is the average similarity score of matched articles
- `sources` tells you exactly which articles were used

## Choose Your LLM

Every request can specify a provider and model. Use local models for free, or cloud APIs for quality:

```bash
# Local (default, no API key needed)
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "provider": "ollama", "model": "qwen2.5:3b"}'

# Claude
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "provider": "claude", "model": "claude-sonnet-4-20250514"}'

# OpenAI
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "provider": "openai", "model": "gpt-4o-mini"}'
```

To enable cloud providers, add API keys to `.env`:

```bash
cp .env.example .env
# Add your keys:
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Supported providers: **Ollama** (default/local), **Claude**, **OpenAI**, **Gemini**, **Mistral**.

See available models: `GET /api/models`

## Load Your Knowledge Base

### Single Article

```bash
curl -X POST http://localhost:8000/api/articles \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "returns-policy",
    "content": {
      "en": {"title": "Returns Policy", "body": "You can return items within 30 days..."}
    }
  }'
```

### Bulk Import (JSON)

```bash
curl -X POST http://localhost:8000/api/articles/bulk \
  -H "Content-Type: application/json" \
  -d '{"articles": [
    {"slug": "article-1", "content": {"en": {"title": "...", "body": "..."}}},
    {"slug": "article-2", "content": {"en": {"title": "...", "body": "..."}}}
  ]}'
```

### Import from Markdown Files

```bash
curl -X POST http://localhost:8000/api/ingest/markdown \
  -F "files=@docs/getting-started.md" \
  -F "files=@docs/faq.md"
```

Markdown files use YAML frontmatter for metadata:

```markdown
---
slug: getting-started
title: Getting Started Guide
language: en
---
Your article content here...
```

### Import from CSV

```bash
curl -X POST http://localhost:8000/api/ingest/csv \
  -F "file=@knowledge-base.csv"
```

CSV columns: `slug`, `language`, `title`, `body`

## API Authentication

Auth is **off by default** for local development. Enable it for production:

```bash
# In .env
REQUIRE_API_KEY=true
```

On first startup, a bootstrap admin key is printed to the container logs. Use it to create additional keys:

```bash
curl -X POST http://localhost:8000/api/admin/keys \
  -H "X-API-Key: ptr_your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "permissions": ["read"], "namespace": "default"}'
```

Then use it:

```bash
curl -s http://localhost:8000/api/ask \
  -H "X-API-Key: ptr_your-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I reset my password?"}'
```

Permissions: `read` (search/ask/chat), `write` (create/update/delete articles), `admin` (manage API keys).

## Namespaces

API keys are scoped to a namespace, enabling multi-tenant knowledge bases on a single deployment. Each namespace has its own isolated set of articles. Default namespace is `"default"`.

## All Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/ask` | read | **Ask a question (JSON response)** |
| POST | `/api/chat` | read | Chat (SSE streaming for widgets) |
| GET | `/api/search?q=...` | read | Search articles |
| POST | `/api/search/semantic` | read | Semantic search |
| GET | `/api/articles` | read | List articles |
| POST | `/api/articles` | write | Create article |
| GET | `/api/articles/{slug}` | read | Get article |
| PUT | `/api/articles/{slug}/{lang}` | write | Update article |
| DELETE | `/api/articles/{slug}` | write | Delete article |
| POST | `/api/articles/bulk` | write | Bulk create articles |
| POST | `/api/ingest/markdown` | write | Import markdown files |
| POST | `/api/ingest/csv` | write | Import CSV file |
| GET | `/api/models` | read | List available models |
| GET | `/api/providers` | read | List LLM providers |
| GET | `/api/chat/history` | read | Recent questions |
| POST | `/api/admin/keys` | admin | Create API key |
| GET | `/api/admin/keys` | admin | List API keys |
| DELETE | `/api/admin/keys/{id}` | admin | Revoke API key |
| GET | `/api/health` | none | Health check |
| GET | `/api/health/llm` | none | LLM status |
| GET | `/docs` | none | Interactive API docs |

## Chat Widget

Embed the chat widget on any page:

```html
<script src="http://localhost:8000/static/widget/widget.js" 
        data-api-url="http://localhost:8000"
        data-position="bottom-right"
        data-color="#0066FF">
</script>
```

## Integrations

### Claude Code

Add this to your project's `CLAUDE.md` to give Claude Code access to your knowledge base:

```markdown
## Knowledge Base

When you need domain-specific knowledge, query the Petrosia knowledge base:

\```bash
# Ask a question (returns grounded answer with sources)
curl -s http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "your question here"}' | python3 -m json.tool

# Search for articles
curl -s "http://localhost:8000/api/search?q=your+search+terms"
\```

Check `grounded: true` in the response to verify the answer is based on actual knowledge base content.
```

### ChatGPT Custom GPTs / Actions

Petrosia exposes an OpenAPI spec that ChatGPT Actions can consume directly:

1. Open [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
2. In ChatGPT, create a Custom GPT and add an Action
3. Import the OpenAPI schema from your Petrosia URL
4. The GPT can now search and ask questions against your knowledge base

For production, expose Petrosia behind HTTPS and set `REQUIRE_API_KEY=true`.

### OpenAI Codex / Any AI Agent

Any agent that can make HTTP calls can use Petrosia. The `/api/ask` endpoint is the universal interface:

```python
import requests

response = requests.post("http://localhost:8000/api/ask", json={
    "query": "How do I reset my password?",
    "provider": "openai",
    "model": "gpt-4o-mini",
})
data = response.json()

if data["grounded"]:
    print(f"Answer: {data['answer']}")
    print(f"Sources: {[s['title'] for s in data['sources']]}")
else:
    print("No relevant knowledge base articles found.")
```

### OpenAPI Spec

Full interactive API docs are available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Raw spec:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Architecture

```
┌─────────────────┐
│  Chat Widget    │  Embeddable vanilla JS
│  (widget.js)    │
└────────┬────────┘
         │ SSE
         ↓
┌─────────────────┐      ┌──────────────────┐
│  FastAPI        │◄─────┤  Admin UI        │
│  Backend        │      │  (HTML/JS/CSS)   │
└───┬────┬────┬───┘      └──────────────────┘
    │    │    │
    ↓    ↓    ↓
┌──────┐ ┌──────────┐ ┌──────────────┐
│Postgres│ │Embeddings│ │ LLM Provider │
│pgvector│ │MiniLM-L6 │ │Ollama/Claude/│
│        │ │(local)   │ │OpenAI/Gemini │
└──────┘ └──────────┘ └──────────────┘
```

- **Embeddings** are always local (sentence-transformers, 384-dim) — no API cost for search
- **LLM** is swappable per-request between local and cloud providers
- **pgvector** handles semantic similarity search

## Development

```bash
# Start PostgreSQL with pgvector
docker run -d -e POSTGRES_USER=petrosia -e POSTGRES_PASSWORD=petrosia123 \
  -e POSTGRES_DB=petrosia -p 5432:5432 pgvector/pgvector:pg16

# Install dependencies
cd backend && pip install -r requirements.txt

# Run
DATABASE_URL=postgresql+asyncpg://petrosia:petrosia123@localhost:5432/petrosia \
  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## License

MIT
