from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import AsyncIterator, List, Optional, Dict, Tuple
from models import ChatHistory, SearchResult, AskResponse
from services.search import SearchService
from llm.factory import get_llm_provider
from config import settings
import re
import logging

logger = logging.getLogger("petrosia.chat")


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_service = SearchService(db)

    async def get_available_providers(self) -> List[Dict[str, any]]:
        """List available LLM providers"""
        providers = []

        if settings.ANTHROPIC_API_KEY:
            providers.append({"name": "claude", "available": True, "model": settings.DEFAULT_LLM_MODEL})
        if settings.OPENAI_API_KEY:
            providers.append({"name": "openai", "available": True, "model": "gpt-4o"})
        if settings.GOOGLE_API_KEY:
            providers.append({"name": "gemini", "available": True, "model": "gemini-1.5-pro"})
        if settings.MISTRAL_API_KEY:
            providers.append({"name": "mistral", "available": True, "model": "mistral-large"})
        if settings.OLLAMA_BASE_URL:
            providers.append({"name": "ollama", "available": True, "model": settings.DEFAULT_LLM_MODEL})

        return providers

    def detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns and common words"""
        text_lower = text.lower()

        # CJK character ranges
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # Hiragana/Katakana
            return "ja"
        if re.search(r'[\u4e00-\u9fff]', text) and not re.search(r'[\u3040-\u309f]', text):
            return "zh"
        if re.search(r'[\uac00-\ud7af]', text):  # Hangul
            return "ko"
        if re.search(r'[\u0e00-\u0e7f]', text):  # Thai
            return "th"
        if re.search(r'[\u0600-\u06ff]', text):  # Arabic
            return "ar"

        # European languages by common words
        es_words = {'cómo', 'como', 'qué', 'que', 'para', 'por', 'una', 'los', 'las', 'del', 'está', 'esto', 'puedo', 'tiene', 'hacer', 'solicito', 'reembolso'}
        fr_words = {'comment', 'pourquoi', 'quoi', 'pour', 'une', 'les', 'des', 'est', 'dans', 'avec', 'faire', 'demander', 'remboursement', "j'ai", "c'est", 'je'}
        de_words = {'wie', 'was', 'warum', 'für', 'ein', 'eine', 'der', 'die', 'das', 'ist', 'kann', 'ich', 'mein', 'nicht', 'werden'}
        pt_words = {'como', 'porque', 'para', 'uma', 'dos', 'das', 'está', 'isso', 'posso', 'fazer', 'reembolso', 'meu', 'não', 'tem'}

        words = set(re.findall(r'\w+', text_lower))

        scores = {
            'es': len(words & es_words),
            'fr': len(words & fr_words),
            'de': len(words & de_words),
            'pt': len(words & pt_words),
        }

        # Also check for accent patterns
        if re.search(r'[ñ¿¡]', text):
            scores['es'] += 3
        if re.search(r"[àâçéèêëîïôùûü]|l'|d'|j'|n'|qu'", text_lower):
            scores['fr'] += 3
        if re.search(r'[äöüß]', text_lower):
            scores['de'] += 3

        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            return best

        return "en"

    async def _prepare_rag_context(
        self,
        query: str,
        language: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        namespace: str = 'default'
    ) -> Tuple:
        """Returns (search_results, messages, resolved_language, provider_name_used, model_used)"""

        # Resolve provider
        resolved_provider = provider_name or settings.DEFAULT_LLM_PROVIDER

        # Auto-detect language if set to auto
        if language == "auto":
            language = self.detect_language(query)

        # Search for relevant articles in detected language
        search_results = await self.search_service.semantic_search(
            query, language, limit=5, threshold=settings.RAG_SIMILARITY_THRESHOLD, namespace=namespace
        )

        # Fallback to English if no results in detected language
        if not search_results and language != "en":
            search_results = await self.search_service.semantic_search(
                query, "en", limit=5, threshold=settings.RAG_SIMILARITY_THRESHOLD, namespace=namespace
            )

        logger.info(f"Found {len(search_results)} relevant articles")

        # Build context from search results
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"[Source {i}: {result.title}]\n{result.body}"
            )

        context = "\n\n".join(context_parts) if context_parts else "No relevant articles found."

        # Build system prompt
        lang_instruction = f"Respond in the same language as the user's question (detected: {language})." if language != "en" else ""
        system_prompt = f"""You are a helpful customer support assistant.
Answer questions based ONLY on the provided knowledge base articles.
If the answer is not in the articles, say "I don't have information about that in my knowledge base."
Always cite sources when providing information.
{lang_instruction}

Knowledge Base Articles:
{context}"""

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        return search_results, messages, language, resolved_provider, model

    async def stream_chat_response(
        self,
        query: str,
        language: str = "auto",
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        namespace: str = 'default'
    ) -> AsyncIterator[str]:
        """Stream RAG-enhanced chat response"""

        search_results, messages, resolved_lang, resolved_provider, resolved_model = await self._prepare_rag_context(
            query, language, provider_name, model, namespace
        )

        logger.info(f"Chat query: provider={resolved_provider}, language={resolved_lang}")
        provider = get_llm_provider(resolved_provider, model=resolved_model)

        full_response = ""
        async for chunk in provider.stream_chat(messages):
            full_response += chunk
            yield chunk

        # Save to history
        history = ChatHistory(
            query=query,
            response=full_response,
            provider=resolved_provider,
            model=provider.model,
            sources=[{
                "slug": r.slug,
                "title": r.title,
                "score": r.score
            } for r in search_results],
            session_id=session_id
        )
        self.db.add(history)
        await self.db.commit()
        logger.debug("Chat response saved to history")

    async def generate_answer(
        self,
        query: str,
        language: str = "auto",
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        namespace: str = 'default'
    ) -> AskResponse:
        """Non-streaming RAG answer. Returns full response with sources and confidence."""

        search_results, messages, resolved_lang, resolved_provider, resolved_model = await self._prepare_rag_context(
            query, language, provider_name, model, namespace
        )

        provider = get_llm_provider(resolved_provider, model=resolved_model)

        # Collect full response
        full_response = ""
        async for chunk in provider.stream_chat(messages):
            full_response += chunk

        # Compute groundedness
        grounded = len(search_results) > 0
        confidence = sum(r.score for r in search_results) / len(search_results) if grounded else 0.0

        # Save to history
        history = ChatHistory(
            query=query,
            response=full_response,
            provider=resolved_provider,
            model=provider.model,
            sources=[{
                "slug": r.slug,
                "title": r.title,
                "score": r.score
            } for r in search_results],
            session_id=session_id
        )
        self.db.add(history)
        await self.db.commit()
        logger.debug("Ask response saved to history")

        return AskResponse(
            answer=full_response,
            sources=search_results,
            provider=resolved_provider,
            model=provider.model,
            grounded=grounded,
            confidence=round(confidence, 4)
        )

    async def get_recent_questions(self, limit: int = 20) -> List[Dict]:
        """Get recent chat questions for analytics"""
        from sqlalchemy import desc
        from models import ChatHistory

        result = await self.db.execute(
            select(ChatHistory)
            .order_by(desc(ChatHistory.created_at))
            .limit(limit)
        )

        questions = []
        for chat in result.scalars():
            questions.append({
                "query": chat.query,
                "response": chat.response[:200] + "..." if len(chat.response) > 200 else chat.response,
                "provider": chat.provider,
                "created_at": chat.created_at.isoformat()
            })

        return questions
