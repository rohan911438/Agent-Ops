from openai import AsyncOpenAI

from app.config import get_settings
from app.services.llm.provider import LLMProvider, LLMResponse

settings = get_settings()

# Every caller of this provider (report_service, optimization_plan_service)
# already wraps the call in a broad except-Exception that degrades to a
# deterministic fallback — but the openai SDK's own default timeout is long
# enough that a hung request would stall a scan well past what "never
# hangs" should mean in practice. See docs/ASP-6262-Production-Readiness-
# Audit.md finding H-1.
REQUEST_TIMEOUT_SECONDS = 25.0


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self._client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key, timeout=REQUEST_TIMEOUT_SECONDS
        )

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
