"""
VectorHire Groq LLM Provider Wrapper.
Provides structured JSON generation, automatic fallback from primary to secondary model,
retry with exponential backoff, rate-limit handling, and credential sanitization.
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional
from groq import (
    APIConnectionError,
    APIStatusError,
    AsyncGroq,
    Groq,
    GroqError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderAPIError
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)

# Module-level in-memory cooldown tracker to prevent retry storms on quota exhaustion
_GROQ_COOLDOWN_UNTIL: float = 0.0
_DEFAULT_GROQ_COOLDOWN_SECONDS: float = 60.0


def is_permanent_groq_error(exc: BaseException) -> bool:
    """Returns True if the error is permanent (404, not found, invalid auth)."""
    if isinstance(exc, APIStatusError) and exc.status_code in {400, 401, 403, 404}:
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in [
        "404", "model_not_found", "not_found", "not found",
        "invalid_api_key", "invalid api key", "unauthorized", "401", "403"
    ])


def is_daily_quota_exhausted(exc: BaseException) -> bool:
    """Returns True if the exception indicates hard daily quota exhaustion rather than transient RPM/TPM."""
    msg = str(exc).lower()
    return any(marker in msg for marker in [
        "tokens per day", "tpd", "requests per day", "rpd", "daily limit", "quota exceeded", "quota reached"
    ])


def is_retryable_transient_error(exc: BaseException) -> bool:
    """Returns True if the error is transient and should be retried with backoff on the same model."""
    if is_permanent_groq_error(exc):
        return False
    if is_daily_quota_exhausted(exc):
        return False
    msg = str(exc).lower()
    if "request too large" in msg or "maximum context length" in msg:
        return False
    if isinstance(exc, (RateLimitError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in {429, 500, 502, 503, 504}:
        return True
    return False


def is_transient_error(exc: BaseException) -> bool:
    """Returns True if the exception represents a transient network or rate limit failure."""
    return is_retryable_transient_error(exc)


class GroqProvider(BaseLLMProvider):
    """
    Centralized Groq Cloud LLM provider for structured reasoning and verification.
    Supports primary model (openai/gpt-oss-20b) and fallback model (qwen/qwen3.8-27b).
    """

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def active_model(self) -> str:
        return self.primary_model

    @property
    def fallback_model_name(self) -> Optional[str]:
        return self.fallback_model

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        max_tokens: Optional[int] = None,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
    ):
        settings: Settings = get_settings()
        self.api_key = api_key or settings.GROQ_API_KEY
        self.primary_model = model or settings.GROQ_MODEL
        self.fallback_model = fallback_model or settings.GROQ_FALLBACK_MODEL
        self.temperature = temperature if temperature is not None else settings.GROQ_TEMPERATURE
        self.timeout_seconds = timeout_seconds or settings.GROQ_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GROQ_MAX_RETRIES
        self.max_tokens = max_tokens or getattr(settings, "GROQ_MAX_TOKENS", 1000)

        self._sync_client = client
        self._async_client = async_client

    def _get_sync_client(self) -> Groq:
        if self._sync_client is None:
            if not self.api_key:
                raise ProviderAPIError(
                    "GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable."
                )
            self._sync_client = Groq(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
            )
        return self._sync_client

    def _get_async_client(self) -> AsyncGroq:
        if self._async_client is None:
            if not self.api_key:
                raise ProviderAPIError(
                    "GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable."
                )
            self._async_client = AsyncGroq(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
            )
        return self._async_client

    def _execute_sync_call(
        self,
        client: Groq,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> Dict[str, Any]:
        """Internal synchronous call wrapped with tenacity exponential backoff and jitter."""
        @retry(
            retry=retry_if_exception(is_retryable_transient_error),
            wait=wait_exponential(multiplier=1, min=1, max=4) + wait_random(0.1, 0.5),
            stop=stop_after_attempt(self.max_retries),
            reraise=True,
        )
        def _call() -> Dict[str, Any]:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=self.max_tokens,
            )
            raw_content = response.choices[0].message.content
            if not raw_content:
                raise ValueError("Received empty content from Groq completion")
            return json.loads(raw_content)

        return _call()

    async def _execute_async_call(
        self,
        client: AsyncGroq,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> Dict[str, Any]:
        """Internal asynchronous call with exponential backoff, jitter, and quota awareness."""
        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    max_tokens=self.max_tokens,
                )
                raw_content = response.choices[0].message.content
                if not raw_content:
                    raise ValueError("Received empty content from Groq async completion")
                return json.loads(raw_content)
            except Exception as exc:
                last_exception = exc
                if not is_retryable_transient_error(exc) or attempt >= self.max_retries:
                    raise exc
                delay = min(4.0, (2 ** (attempt - 1))) + random.uniform(0.1, 0.5)
                await asyncio.sleep(delay)

        if last_exception:
            raise last_exception
        raise ProviderAPIError("Max retries exceeded without a response")

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Synchronously requests structured JSON from Groq.
        Attempts primary model first. If primary model fails, falls back to fallback_model.
        """
        global _GROQ_COOLDOWN_UNTIL
        now = time.time()
        if now < _GROQ_COOLDOWN_UNTIL:
            remaining = int(_GROQ_COOLDOWN_UNTIL - now)
            raise ProviderAPIError(
                f"Groq provider is in cooldown for {remaining}s due to recent quota exhaustion. "
                "Failing fast to trigger offline fallback."
            )

        client = self._get_sync_client()
        temp = temperature if temperature is not None else self.temperature
        chosen_primary = model or self.primary_model

        try:
            return self._execute_sync_call(client, chosen_primary, messages, temp)
        except Exception as primary_err:
            if is_daily_quota_exhausted(primary_err):
                _GROQ_COOLDOWN_UNTIL = time.time() + _DEFAULT_GROQ_COOLDOWN_SECONDS
                logger.warning("Groq daily quota exhausted on %s. Setting cooldown until +%ds.", chosen_primary, _DEFAULT_GROQ_COOLDOWN_SECONDS)

            logger.warning(
                "Primary Groq model '%s' failed: %s. Attempting fallback model '%s'",
                chosen_primary,
                str(primary_err)[:200],
                self.fallback_model,
            )
            # Only try fallback model if failure wasn't account-wide daily quota exhaustion
            if self.fallback_model and self.fallback_model != chosen_primary and not is_daily_quota_exhausted(primary_err):
                try:
                    return self._execute_sync_call(client, self.fallback_model, messages, temp)
                except Exception as fallback_err:
                    if is_daily_quota_exhausted(fallback_err):
                        _GROQ_COOLDOWN_UNTIL = time.time() + _DEFAULT_GROQ_COOLDOWN_SECONDS
                    logger.error(
                        "Fallback Groq model '%s' also failed: %s",
                        self.fallback_model,
                        str(fallback_err)[:200],
                    )
                    raise ProviderAPIError(
                        f"Both primary model ({chosen_primary}) and fallback model ({self.fallback_model}) "
                        f"failed. Primary error: {type(primary_err).__name__}: {str(primary_err)[:200]}. "
                        f"Fallback error: {type(fallback_err).__name__}: {str(fallback_err)[:200]}"
                    ) from fallback_err
            raise ProviderAPIError(
                f"Groq API call to {chosen_primary} failed: {type(primary_err).__name__}: {str(primary_err)[:200]}"
            ) from primary_err

    async def generate_json_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronously requests structured JSON from Groq.
        Attempts primary model first. If primary model fails, falls back to fallback_model.
        """
        global _GROQ_COOLDOWN_UNTIL
        now = time.time()
        if now < _GROQ_COOLDOWN_UNTIL:
            remaining = int(_GROQ_COOLDOWN_UNTIL - now)
            raise ProviderAPIError(
                f"Groq provider is in cooldown for {remaining}s due to recent quota exhaustion. "
                "Failing fast to trigger offline fallback."
            )

        client = self._get_async_client()
        temp = temperature if temperature is not None else self.temperature
        chosen_primary = model or self.primary_model

        try:
            return await self._execute_async_call(client, chosen_primary, messages, temp)
        except Exception as primary_err:
            if is_daily_quota_exhausted(primary_err):
                _GROQ_COOLDOWN_UNTIL = time.time() + _DEFAULT_GROQ_COOLDOWN_SECONDS
                logger.warning("Groq daily quota exhausted in async on %s. Setting cooldown until +%ds.", chosen_primary, _DEFAULT_GROQ_COOLDOWN_SECONDS)

            logger.warning(
                "Primary Groq model '%s' failed in async execution: %s. Attempting fallback model '%s'",
                chosen_primary,
                str(primary_err)[:200],
                self.fallback_model,
            )
            if self.fallback_model and self.fallback_model != chosen_primary and not is_daily_quota_exhausted(primary_err):
                try:
                    return await self._execute_async_call(client, self.fallback_model, messages, temp)
                except Exception as fallback_err:
                    if is_daily_quota_exhausted(fallback_err):
                        _GROQ_COOLDOWN_UNTIL = time.time() + _DEFAULT_GROQ_COOLDOWN_SECONDS
                    logger.error(
                        "Fallback Groq model '%s' also failed in async execution: %s",
                        self.fallback_model,
                        str(fallback_err)[:200],
                    )
                    raise ProviderAPIError(
                        f"Both primary model ({chosen_primary}) and fallback model ({self.fallback_model}) "
                        f"failed. Primary error: {type(primary_err).__name__}: {str(primary_err)[:200]}. "
                        f"Fallback error: {type(fallback_err).__name__}: {str(fallback_err)[:200]}"
                    ) from fallback_err
            raise ProviderAPIError(
                f"Groq async API call to {chosen_primary} failed: {type(primary_err).__name__}: {str(primary_err)[:200]}"
            ) from primary_err
