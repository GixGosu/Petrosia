from typing import AsyncIterator
import google.generativeai as genai
from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider"""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Gemini"""

        # Convert messages to Gemini format
        history = []
        current_message = None

        for msg in messages:
            if msg["role"] == "system":
                # Gemini doesn't have system role, prepend to first user message
                continue
            elif msg["role"] == "user":
                current_message = msg["content"]
            elif msg["role"] == "assistant":
                if current_message:
                    history.append({"role": "user", "parts": [current_message]})
                    current_message = None
                history.append({"role": "model", "parts": [msg["content"]]})

        # Get system message if exists
        system_msg = next((msg["content"] for msg in messages if msg["role"] == "system"), None)
        if system_msg:
            current_message = f"{system_msg}\n\n{current_message}" if current_message else system_msg

        chat = self.client.start_chat(history=history)

        response = chat.send_message(
            current_message,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def generate_embedding(self, text: str) -> list[float]:
        """Gemini embeddings - fallback to OpenAI"""
        from .openai import OpenAIProvider
        from config import settings

        if settings.OPENAI_API_KEY:
            openai_provider = OpenAIProvider(settings.OPENAI_API_KEY)
            return await openai_provider.generate_embedding(text)
        else:
            raise ValueError("OpenAI API key required for embeddings")
