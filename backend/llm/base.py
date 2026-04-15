from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat completion responses"""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings for text"""
        pass
