import logging
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderAPIError
from app.providers.base_llm import BaseLLMProvider
from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class GeminiWithGroqFallbackProvider(BaseLLMProvider):
    """
    Composite LLM Provider that executes Google Gemini as the primary provider,
    and automatically falls back to Groq if Gemini encounters errors (rate limits,
    quota exhaustion, timeouts, or service exceptions).
    """

    def __init__(
        self,
        gemini_provider: Optional[GeminiProvider] = None,
        groq_provider: Optional[GroqProvider] = None,
    ):
        self.primary_provider = gemini_provider or GeminiProvider()
        self.fallback_provider = groq_provider or GroqProvider()

    @property
    def provider_name(self) -> str:
        return f"{self.primary_provider.provider_name}->{self.fallback_provider.provider_name}"

    @property
    def active_model(self) -> str:
        return self.primary_provider.active_model

    @property
    def fallback_model_name(self) -> Optional[str]:
        return f"{self.primary_provider.fallback_model_name or 'none'} / {self.fallback_provider.active_model}"

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Synchronously attempts primary Gemini, automatically falling back to Groq on failure."""
        try:
            return self.primary_provider.generate_json(
                messages=messages,
                model=model,
                temperature=temperature,
            )
        except Exception as gemini_err:
            logger.warning(
                "Primary LLM provider (Gemini) failed: %s. Initiating cross-provider fallback to Groq.",
                gemini_err,
            )
            try:
                return self.fallback_provider.generate_json(
                    messages=messages,
                    temperature=temperature,
                )
            except Exception as groq_err:
                raise ProviderAPIError(
                    f"Both primary provider (Gemini) and cross-provider fallback (Groq) failed. "
                    f"Gemini: {gemini_err}; Groq: {groq_err}"
                ) from groq_err

    async def generate_json_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Asynchronously attempts primary Gemini, automatically falling back to Groq on failure."""
        try:
            return await self.primary_provider.generate_json_async(
                messages=messages,
                model=model,
                temperature=temperature,
            )
        except Exception as gemini_err:
            logger.warning(
                "Primary LLM provider (Gemini) async failed: %s. Initiating cross-provider fallback to Groq.",
                gemini_err,
            )
            try:
                return await self.fallback_provider.generate_json_async(
                    messages=messages,
                    temperature=temperature,
                )
            except Exception as groq_err:
                raise ProviderAPIError(
                    f"Both primary provider (Gemini) and cross-provider fallback (Groq) failed. "
                    f"Gemini: {gemini_err}; Groq: {groq_err}"
                ) from groq_err


def get_llm_provider(
    provider_type: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> BaseLLMProvider:
    """
    Factory function returning the configured BaseLLMProvider instance.
    Defaults to settings.LLM_PROVIDER ('gemini').
    When 'gemini' is selected, returns GeminiWithGroqFallbackProvider.
    When 'groq' is explicitly selected, returns GroqProvider.
    """
    cfg = settings or get_settings()
    chosen_type = (provider_type or cfg.LLM_PROVIDER).strip().lower()

    if chosen_type == "gemini":
        return GeminiWithGroqFallbackProvider()
    elif chosen_type == "groq":
        return GroqProvider()
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER '{chosen_type}'. Supported providers: 'gemini', 'groq'.")
