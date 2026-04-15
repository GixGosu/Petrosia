from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List
from models import ArticleContent, SearchResult
from services import get_embedding_model
import logging

logger = logging.getLogger("petrosia.search")


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_model = get_embedding_model()

    async def semantic_search(self, query: str, language: str = "en", limit: int = 5, threshold: float = 0.5, namespace: str = "default") -> List[SearchResult]:
        """Perform semantic search using pgvector"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Convert embedding to pgvector format
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

        # Perform vector similarity search
        # Use CAST() instead of :: to avoid conflict with SQLAlchemy's :param syntax
        sql = text("""
            SELECT
                ac.article_id,
                a.slug,
                ac.language,
                ac.title,
                ac.body,
                1 - (ac.embedding <=> CAST(:embedding AS vector)) as score
            FROM article_content ac
            JOIN articles a ON a.id = ac.article_id
            WHERE ac.language = :language
                AND a.status = 'published'
                AND a.namespace = :namespace
                AND 1 - (ac.embedding <=> CAST(:embedding AS vector)) > :threshold
            ORDER BY ac.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        result = await self.db.execute(
            sql,
            {
                "embedding": embedding_str,
                "language": language,
                "namespace": namespace,
                "threshold": threshold,
                "limit": limit
            }
        )

        results = []
        for row in result:
            results.append(SearchResult(
                article_id=row.article_id,
                slug=row.slug,
                language=row.language,
                title=row.title,
                body=row.body,
                score=float(row.score)
            ))

        logger.info(f"Search: query='{query[:50]}', language={language}, results={len(results)}")

        return results

    async def hybrid_search(self, query: str, language: str = "en", limit: int = 5, namespace: str = "default") -> List[SearchResult]:
        """Hybrid search combining semantic + keyword (simplified for MVP)"""
        # For MVP, just use semantic search
        # In production, you'd combine with BM25 or full-text search
        return await self.semantic_search(query, language, limit, namespace=namespace)
