from sentence_transformers import SentenceTransformer
from config import settings

_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model


from .articles import ArticleService
from .search import SearchService
from .chat import ChatService

__all__ = ["ArticleService", "SearchService", "ChatService", "get_embedding_model"]
