import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
import uuid
import logging
from models import Article, ArticleContent, ArticleVersion
from services import get_embedding_model

logger = logging.getLogger("petrosia.articles")


class ArticleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_model = get_embedding_model()

    async def create_article(self, slug: str, content: Dict[str, Dict[str, str]], status: str = "published", created_by: str = "system", namespace: str = "default") -> Article:
        """Create a new article with multi-language content"""
        # Create article
        article = Article(
            slug=slug,
            status=status,
            created_by=created_by,
            namespace=namespace
        )
        self.db.add(article)
        await self.db.flush()

        # Create content for each language
        for language, lang_content in content.items():
            # Generate embedding from title + body (run in executor to avoid blocking event loop)
            text_for_embedding = f"{lang_content['title']} {lang_content['body']}"
            embedding = await asyncio.to_thread(lambda t=text_for_embedding: self.embedding_model.encode(t).tolist())

            article_content = ArticleContent(
                article_id=article.id,
                language=language,
                title=lang_content['title'],
                body=lang_content['body'],
                embedding=embedding,
                updated_by=created_by
            )
            self.db.add(article_content)

        await self.db.commit()
        logger.info(f"Created article: {slug} ({len(content)} languages) in namespace={namespace}")
        await self.db.refresh(article)
        return article

    async def get_article(self, slug: str, namespace: str = "default") -> Optional[Article]:
        """Get article with all language content"""
        result = await self.db.execute(
            select(Article)
            .options(selectinload(Article.content_entries))
            .where(Article.slug == slug, Article.namespace == namespace)
        )
        return result.scalar_one_or_none()

    async def get_article_by_id(self, article_id: uuid.UUID) -> Optional[Article]:
        """Get article by ID with all language content"""
        result = await self.db.execute(
            select(Article)
            .options(selectinload(Article.content_entries))
            .where(Article.id == article_id)
        )
        return result.scalar_one_or_none()

    async def list_articles(self, status: Optional[str] = None, language: Optional[str] = None, limit: int = 100, namespace: str = "default") -> List[Article]:
        """List all articles"""
        query = select(Article).options(selectinload(Article.content_entries)).where(Article.namespace == namespace)

        if status:
            query = query.where(Article.status == status)

        query = query.limit(limit).order_by(Article.updated_at.desc())

        result = await self.db.execute(query)
        articles = result.scalars().all()

        # Filter by language if specified
        if language:
            filtered = []
            for article in articles:
                if any(c.language == language for c in article.content_entries):
                    filtered.append(article)
            return filtered

        return list(articles)

    async def update_article_content(self, slug: str, language: str, title: str, body: str, updated_by: str = "system", namespace: str = "default") -> Optional[ArticleContent]:
        """Update article content for a specific language (ONE API CALL!)"""
        # Get article
        article = await self.get_article(slug, namespace=namespace)
        if not article:
            return None

        # Find existing content for this language
        content = None
        for c in article.content_entries:
            if c.language == language:
                content = c
                break

        # Generate new embedding (run in executor to avoid blocking event loop)
        text_for_embedding = f"{title} {body}"
        embedding = await asyncio.to_thread(lambda: self.embedding_model.encode(text_for_embedding).tolist())

        if content:
            # Save version before updating
            version = ArticleVersion(
                article_content_id=content.id,
                title=content.title,
                body=content.body,
                created_by=content.updated_by
            )
            self.db.add(version)

            # Update existing content
            content.title = title
            content.body = body
            content.embedding = embedding
            content.updated_by = updated_by
        else:
            # Create new language content
            content = ArticleContent(
                article_id=article.id,
                language=language,
                title=title,
                body=body,
                embedding=embedding,
                updated_by=updated_by
            )
            self.db.add(content)

        # Update article timestamp
        article.updated_at = func.now()

        await self.db.commit()
        logger.info(f"Updated article: {slug}/{language}")
        await self.db.refresh(content)
        return content

    async def delete_article(self, slug: str, namespace: str = "default") -> bool:
        """Delete an article"""
        article = await self.get_article(slug, namespace=namespace)
        if not article:
            return False

        await self.db.delete(article)
        await self.db.commit()
        logger.info(f"Deleted article: {slug} from namespace={namespace}")
        return True

    async def bulk_create_articles(self, articles: List[dict], namespace: str = "default") -> dict:
        """Bulk create articles. Each dict should match ArticleService.create_article() parameters."""
        created = 0
        failed = 0
        errors = []

        for article_data in articles:
            slug = article_data.get("slug", "<unknown>")
            try:
                await self.create_article(
                    slug=slug,
                    content=article_data["content"],
                    status=article_data.get("status", "published"),
                    created_by=article_data.get("created_by", "system"),
                    namespace=namespace
                )
                created += 1
            except Exception as e:
                failed += 1
                errors.append({"slug": slug, "error": str(e)})
                logger.warning(f"bulk_create_articles: failed to create '{slug}': {e}")
                # Roll back to clean state so subsequent articles can proceed
                await self.db.rollback()

        return {"created": created, "failed": failed, "errors": errors}

    def article_to_dict(self, article: Article) -> Dict:
        """Convert article to response dict"""
        content_dict = {}
        for c in article.content_entries:
            content_dict[c.language] = {
                "title": c.title,
                "body": c.body
            }

        return {
            "id": str(article.id),
            "slug": article.slug,
            "status": article.status,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat() if article.updated_at else None,
            "content": content_dict
        }
