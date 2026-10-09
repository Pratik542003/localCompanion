from app.domain.interfaces import ReasoningProvider
from app.providers.reasoning.demo_provider import DemoReasoningProvider
from app.providers.reasoning.llama_provider import LlamaCppReasoningProvider

__all__ = [
    "DemoReasoningProvider",
    "LlamaCppReasoningProvider",
    "get_reasoning_provider",
]


def get_reasoning_provider() -> ReasoningProvider:
    """Return the appropriate reasoning provider based on application settings."""
    from app.core.config import settings

    if settings.is_demo_mode:
        return DemoReasoningProvider()

    return LlamaCppReasoningProvider(
        base_url=settings.llama_cpp_url,
        model=settings.llama_cpp_model,
        timeout=settings.llama_cpp_timeout,
    )
