from typing import AsyncIterator
import openai
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        super().__init__(api_key, model)
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat completion from OpenAI"""

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings using OpenAI"""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding
