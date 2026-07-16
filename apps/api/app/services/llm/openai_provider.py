from openai import AsyncOpenAI

from app.config import get_settings
from app.services.llm.provider import LLMProvider, LLMResponse

settings = get_settings()


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    async def complete(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
