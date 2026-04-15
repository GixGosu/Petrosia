from fastapi import FastAPI, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
import hashlib
import csv
import io
import yaml
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("petrosia")

from config import settings
from database import get_db, init_db, AsyncSessionLocal
from models import (
    Article, ApiKey,
    ArticleCreate, ArticleUpdate, ArticleResponse,
    ChatRequest, ChatResponse, SearchRequest, SearchResult,
    ProviderInfo,
    AskRequest, AskResponse,
    ApiKeyCreate, ApiKeyResponse,
    BulkCreateRequest, BulkCreateResponse,
)
from services import ArticleService, SearchService, ChatService
from auth import (
    require_read, require_write, require_admin, get_api_key,
    generate_api_key, hash_api_key,
)

# Initialize FastAPI app
app = FastAPI(
    title="Petrosia",
    description=(
        "Knowledge base with a REST API. Search or ask questions. "
        "Your AI tools consume answers, not raw documents.\n\n"
        "## Key Endpoints\n"
        "- **POST /api/ask** — Ask a question, get a grounded JSON answer with sources\n"
        "- **POST /api/chat** — Streaming chat (SSE) for widgets\n"
        "- **GET /api/search** — Semantic search across articles\n"
        "- **GET /api/models** — List available LLM providers and models\n\n"
        "## Authentication\n"
        "Pass `X-API-Key` header. Auth is off by default (`REQUIRE_API_KEY=false`)."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting setup
def get_rate_limit_key(request: Request) -> str:
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        return hashlib.sha256(api_key_header.encode()).hexdigest()[:16]
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Max upload size for ingestion endpoints (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()

    # Auto-seed if database is empty
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func
        from models import Article
        result = await db.execute(select(func.count()).select_from(Article))
        count = result.scalar()
        if count == 0:
            logger.info("No articles found, seeding with sample data...")
            from seed_data import SEED_ARTICLES
            from services.articles import ArticleService
            service = ArticleService(db)
            for article_data in SEED_ARTICLES:
                try:
                    await service.create_article(
                        slug=article_data["slug"],
                        content=article_data["content"],
                        status="published",
                        created_by="seed_script"
                    )
                    logger.info(f"  Seeded: {article_data['content']['en']['title']}")
                except Exception as e:
                    logger.warning(f"  Failed to seed '{article_data['slug']}': {e}")
            logger.info("Database seeding complete.")
        else:
            logger.info(f"Database has {count} articles, skipping seed.")

        # Bootstrap admin API key if none exist
        key_count = (await db.execute(select(func.count()).select_from(ApiKey))).scalar()
        if key_count == 0:
            plain_key = generate_api_key()
            admin_key = ApiKey(
                key_hash=hash_api_key(plain_key),
                name="bootstrap-admin",
                permissions=["read", "write", "admin"],
                namespace="default",
                is_active=True,
            )
            db.add(admin_key)
            await db.commit()
            logger.info("=" * 60)
            logger.info("ADMIN API KEY (save this — it won't be shown again):")
            logger.info(f"  {plain_key}")
            logger.info("=" * 60)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "petrosia-mvp"}


@app.get("/api/health/llm")
async def llm_health_check(db: AsyncSession = Depends(get_db)):
    """Check LLM provider status"""
    chat_service = ChatService(db)
    providers = await chat_service.get_available_providers()
    return {"providers": providers}


# ── Articles ──────────────────────────────────────────────────────────────────

@app.post("/api/articles", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def create_article(
    request: Request,
    article: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_write),
):
    """Create a new article"""
    service = ArticleService(db)
    created = await service.create_article(
        slug=article.slug,
        content=article.content,
        status=article.status,
        created_by=article.created_by,
        namespace=api_key.namespace,
    )
    return service.article_to_dict(created)


@app.get("/api/articles", response_model=List[dict])
@limiter.limit(settings.RATE_LIMIT_READS)
async def list_articles(
    request: Request,
    status: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """List all articles"""
    service = ArticleService(db)
    articles = await service.list_articles(
        status=status, language=language, limit=limit, namespace=api_key.namespace
    )
    return [service.article_to_dict(a) for a in articles]


@app.get("/api/articles/{slug}", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_READS)
async def get_article(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """Get article by slug"""
    service = ArticleService(db)
    article = await service.get_article(slug, namespace=api_key.namespace)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return service.article_to_dict(article)


@app.get("/api/articles/{slug}/{language}", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_READS)
async def get_article_language(
    request: Request,
    slug: str,
    language: str,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """Get article content for specific language"""
    service = ArticleService(db)
    article = await service.get_article(slug, namespace=api_key.namespace)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article_dict = service.article_to_dict(article)
    if language not in article_dict["content"]:
        raise HTTPException(status_code=404, detail=f"Language {language} not found for this article")

    return {
        "slug": article_dict["slug"],
        "language": language,
        **article_dict["content"][language],
    }


@app.put("/api/articles/{slug}/{language}", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def update_article_content(
    request: Request,
    slug: str,
    language: str,
    update: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_write),
):
    """Update article content for specific language (ONE API CALL!)"""
    service = ArticleService(db)
    content = await service.update_article_content(
        slug=slug,
        language=language,
        title=update.title,
        body=update.body,
        updated_by=update.updated_by,
        namespace=api_key.namespace,
    )

    if not content:
        raise HTTPException(status_code=404, detail="Article not found")

    return {
        "id": str(content.id),
        "article_id": str(content.article_id),
        "language": content.language,
        "title": content.title,
        "body": content.body,
        "updated_at": content.updated_at.isoformat(),
    }


@app.delete("/api/articles/{slug}")
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def delete_article(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_write),
):
    """Delete an article"""
    service = ArticleService(db)
    success = await service.delete_article(slug, namespace=api_key.namespace)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "deleted"}


# ── Bulk ingestion ────────────────────────────────────────────────────────────

@app.post("/api/articles/bulk", response_model=BulkCreateResponse)
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def bulk_create_articles(
    request: Request,
    body: BulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_write),
):
    """Bulk-create articles from a JSON list"""
    service = ArticleService(db)
    result = await service.bulk_create_articles(
        [a.model_dump() for a in body.articles], namespace=api_key.namespace
    )
    return BulkCreateResponse(**result)


@app.post("/api/ingest/markdown", response_model=BulkCreateResponse)
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def ingest_markdown(
    request: Request,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_write),
):
    """Ingest one or more Markdown files with YAML frontmatter"""
    service = ArticleService(db)
    created = 0
    failed = 0
    errors: List[dict] = []

    for upload in files:
        raw = (await upload.read()).decode("utf-8", errors="replace")
        if len(raw.encode("utf-8")) > MAX_UPLOAD_BYTES:
            errors.append({"slug": upload.filename or "<unknown>", "error": f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)}MB limit"})
            failed += 1
            continue
        # Split on frontmatter delimiters
        parts = raw.split("---")
        if len(parts) < 3:
            # No frontmatter: treat whole file as body, use filename as slug
            slug = upload.filename.rsplit(".", 1)[0] if upload.filename else "unknown"
            body = raw
            title = slug
            language = "en"
        else:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                meta = {}
            slug = meta.get("slug") or (upload.filename.rsplit(".", 1)[0] if upload.filename else "unknown")
            title = meta.get("title") or slug
            language = meta.get("language", "en")
            body = "---".join(parts[2:]).strip()

        if not slug:
            errors.append({"slug": "<unknown>", "error": "Could not determine slug from frontmatter or filename"})
            failed += 1
            continue

        try:
            await service.create_article(
                slug=slug,
                content={language: {"title": title, "body": body}},
                status="published",
                created_by="ingest",
                namespace=api_key.namespace,
            )
            created += 1
        except Exception as e:
            errors.append({"slug": slug, "error": str(e)})
            failed += 1

    return BulkCreateResponse(created=created, failed=failed, errors=errors)


@app.post("/api/ingest/csv", response_model=BulkCreateResponse)
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def ingest_csv(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_write),
):
    """Ingest a CSV file. Required columns: slug, language, title, body"""
    service = ArticleService(db)
    created = 0
    failed = 0
    errors: List[dict] = []

    raw = (await file.read()).decode("utf-8", errors="replace")
    if len(raw.encode("utf-8")) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"CSV file exceeds {MAX_UPLOAD_BYTES // (1024*1024)}MB limit")
    reader = csv.DictReader(io.StringIO(raw))

    # Group rows by slug (cap at 10,000 rows to prevent abuse)
    MAX_CSV_ROWS = 10_000
    grouped: dict = {}
    row_count = 0
    for row in reader:
        row_count += 1
        if row_count > MAX_CSV_ROWS:
            raise HTTPException(status_code=413, detail=f"CSV exceeds {MAX_CSV_ROWS} row limit")
        slug = row.get("slug", "").strip()
        if not slug:
            continue
        language = row.get("language", "en").strip() or "en"
        title = row.get("title", "").strip()
        body = row.get("body", "").strip()
        if slug not in grouped:
            grouped[slug] = {}
        grouped[slug][language] = {"title": title, "body": body}

    for slug, content in grouped.items():
        try:
            await service.create_article(
                slug=slug,
                content=content,
                status="published",
                created_by="ingest",
                namespace=api_key.namespace,
            )
            created += 1
        except Exception as e:
            errors.append({"slug": slug, "error": str(e)})
            failed += 1

    return BulkCreateResponse(created=created, failed=failed, errors=errors)


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/api/search", response_model=List[SearchResult])
@limiter.limit(settings.RATE_LIMIT_READS)
async def search_articles(
    request: Request,
    q: str = Query(..., description="Search query"),
    language: str = Query("en", description="Language code"),
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """Hybrid search across articles"""
    service = SearchService(db)
    return await service.hybrid_search(q, language, limit, namespace=api_key.namespace)


@app.post("/api/search/semantic", response_model=List[SearchResult])
@limiter.limit(settings.RATE_LIMIT_READS)
async def semantic_search(
    request: Request,
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """Semantic search only"""
    service = SearchService(db)
    return await service.semantic_search(
        body.query, body.language, body.limit, namespace=api_key.namespace
    )


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
@limiter.limit(settings.RATE_LIMIT_READS)
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """RAG chatbot with streaming response"""
    chat_service = ChatService(db)

    async def generate():
        try:
            async for chunk in chat_service.stream_chat_response(
                query=body.query,
                language=body.language,
                provider_name=body.provider,
                model=body.model,
                session_id=body.session_id,
                namespace=api_key.namespace,
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/chat/history")
@limiter.limit(settings.RATE_LIMIT_READS)
async def get_chat_history(
    request: Request,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """Get recent chat questions for analytics"""
    chat_service = ChatService(db)
    return await chat_service.get_recent_questions(limit)


# ── Ask (non-streaming) ───────────────────────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
@limiter.limit(settings.RATE_LIMIT_READS)
async def ask(
    request: Request,
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """Non-streaming RAG answer. Returns JSON with answer, sources, and confidence."""
    chat_service = ChatService(db)
    return await chat_service.generate_answer(
        query=body.query,
        language=body.language,
        provider_name=body.provider,
        model=body.model,
        session_id=body.session_id,
        namespace=api_key.namespace,
    )


# ── Providers / Models ────────────────────────────────────────────────────────

@app.get("/api/providers", response_model=List[ProviderInfo])
@limiter.limit(settings.RATE_LIMIT_READS)
async def list_providers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_read),
):
    """List available LLM providers"""
    chat_service = ChatService(db)
    providers = await chat_service.get_available_providers()
    return providers


@app.get("/api/models")
@limiter.limit(settings.RATE_LIMIT_READS)
async def list_models(
    request: Request,
    api_key=Depends(require_read),
):
    """Return available models per provider"""
    providers = []

    # Cloud providers — check which keys are configured
    if settings.ANTHROPIC_API_KEY:
        providers.append({
            "name": "claude",
            "available": True,
            "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001", "claude-opus-4-5"],
        })
    else:
        providers.append({"name": "claude", "available": False, "models": []})

    if settings.OPENAI_API_KEY:
        providers.append({
            "name": "openai",
            "available": True,
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        })
    else:
        providers.append({"name": "openai", "available": False, "models": []})

    if settings.GOOGLE_API_KEY:
        providers.append({
            "name": "gemini",
            "available": True,
            "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
        })
    else:
        providers.append({"name": "gemini", "available": False, "models": []})

    if settings.MISTRAL_API_KEY:
        providers.append({
            "name": "mistral",
            "available": True,
            "models": ["mistral-small-latest", "mistral-medium-latest", "mistral-large-latest"],
        })
    else:
        providers.append({"name": "mistral", "available": False, "models": []})

    # Ollama — query dynamically
    ollama_models: List[str] = []
    ollama_available = False
    if settings.OLLAMA_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
                ollama_available = True
        except Exception:
            pass
    providers.append({
        "name": "ollama",
        "available": ollama_available,
        "models": ollama_models,
    })

    return {"providers": providers}


# ── Admin — API key management ────────────────────────────────────────────────

@app.post("/api/admin/keys", response_model=ApiKeyResponse)
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def create_api_key(
    request: Request,
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_admin),
):
    """Create a new API key (plain key returned once only)"""
    plain_key = generate_api_key()
    key_hash = hash_api_key(plain_key)

    new_key = ApiKey(
        key_hash=key_hash,
        name=body.name,
        permissions=body.permissions,
        namespace=body.namespace,
        is_active=True,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    return ApiKeyResponse(
        id=new_key.id,
        name=new_key.name,
        created_at=new_key.created_at,
        permissions=new_key.permissions,
        namespace=new_key.namespace,
        is_active=new_key.is_active,
        key=plain_key,
    )


@app.get("/api/admin/keys", response_model=List[ApiKeyResponse])
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def list_api_keys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_admin),
):
    """List all API keys (hash never returned)"""
    result = await db.execute(select(ApiKey))
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            created_at=k.created_at,
            permissions=k.permissions,
            namespace=k.namespace,
            is_active=k.is_active,
        )
        for k in keys
    ]


@app.delete("/api/admin/keys/{key_id}")
@limiter.limit(settings.RATE_LIMIT_WRITES)
async def revoke_api_key(
    request: Request,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_admin),
):
    """Revoke an API key (sets is_active=False)"""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Key not found")
    target.is_active = False
    await db.commit()
    return {"status": "revoked", "id": str(key_id)}


# ── Static pages ──────────────────────────────────────────────────────────────

# Serve widget demo page
@app.get("/widget-demo")
async def widget_demo():
    """Demo page with embedded widget"""
    return FileResponse("/app/static/widget/demo.html")


# Serve admin interface
@app.get("/admin")
async def admin_interface():
    """Admin interface"""
    return FileResponse("/app/static/admin/index.html")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Petrosia MVP",
        "version": "1.0.0",
        "endpoints": {
            "admin": "/admin",
            "widget_demo": "/widget-demo",
            "api_docs": "/docs",
            "health": "/api/health",
        },
    }


# Static file mounts (must come after all route definitions)
app.mount("/static/widget", StaticFiles(directory="/app/static/widget"), name="widget")
app.mount("/static/admin", StaticFiles(directory="/app/static/admin"), name="admin")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
