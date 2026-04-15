from typing import AsyncIterator
import anthropic
from .base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key, model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Claude"""

        # Convert messages format if needed
        formatted_messages = []
        system_message = None

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        stream = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_message,
            messages=formatted_messages,
            stream=True,
        )

        async for event in stream:
            if event.type == "content_block_delta":
                if hasattr(event.delta, "text"):
                    yield event.delta.text

    async def generate_embedding(self, text: str) -> list[float]:
        """Claude doesn't provide embeddings, use OpenAI as fallback"""
        # Import here to avoid circular dependency
        from .openai import OpenAIProvider
        from config import settings

        if settings.OPENAI_API_KEY:
            openai_provider = OpenAIProvider(settings.OPENAI_API_KEY)
            return await openai_provider.generate_embedding(text)
        else:
            raise ValueError("OpenAI API key required for embeddings")
