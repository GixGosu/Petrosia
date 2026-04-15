from typing import AsyncIterator
from mistralai import Mistral
from .base import BaseLLMProvider


class MistralProvider(BaseLLMProvider):
    """Mistral AI provider"""

    def __init__(self, api_key: str, model: str = "mistral-small-latest"):
        super().__init__(api_key, model)
        self.client = Mistral(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Mistral"""

        stream = self.client.chat.stream(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        for chunk in stream:
            if chunk.data.choices[0].delta.content:
                yield chunk.data.choices[0].delta.content

    async def generate_embedding(self, text: str) -> list[float]:
        """Mistral embeddings"""
        response = self.client.embeddings.create(
            model="mistral-embed",
            inputs=[text],
        )
        return response.data[0].embedding
