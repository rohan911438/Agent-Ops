"""Provider-agnostic LLM abstraction.

Only OpenAIProvider exists today. Anthropic/Gemini/DeepSeek/Groq/
OpenRouter become additional LLMProvider subclasses later — no call site
outside this package needs to change when they're added.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, model: str, **kwargs) -> LLMResponse: ...
