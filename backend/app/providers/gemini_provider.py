"""
VectorHire Gemini LLM Provider Wrapper.
Implements BaseLLMProvider for Google Gemini models via google.genai SDK.
Provides structured JSON generation, automatic fallback model handling,
retries with exponential backoff, and rate-limit handling.
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderAPIError
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)

# Module-level in-memory cooldown tracker to prevent retry storms on quota exhaustion
_GEMINI_COOLDOWN_UNTIL: float = 0.0
_DEFAULT_COOLDOWN_SECONDS: float = 60.0


def is_permanent_gemini_error(exc: BaseException) -> bool:
    """Returns True if the error is permanent (404, not found, deprecated model, invalid auth)."""
    msg = str(exc).lower()
    return any(marker in msg for marker in [
        "404", "not_found", "not found", "is not found", "no longer available",
        "unregistered", "invalid_argument", "400", "401", "403", "unauthenticated",
        "permission_denied", "api key not valid", "invalid api key"
    ])


def is_quota_exhausted_gemini_error(exc: BaseException) -> bool:
    """Returns True if the error represents quota exhaustion / resource limits."""
    msg = str(exc).lower()
    return any(marker in msg for marker in [
        "tokens per day", "tpd", "requests per day", "rpd", "daily limit",
        "quota exceeded", "quota reached", "resource_exhausted", "free tier limit"
    ])


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider for structured reasoning and verification.
    Uses the modern Google GenAI SDK (google.genai).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        client: Optional[Any] = None,
    ):
        settings: Settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.primary_model = model or settings.GEMINI_MODEL
        # Use provided fallback_model if explicitly specified (empty string or False sentinel means disabled)
        self.fallback_model = settings.GEMINI_FALLBACK_MODEL if fallback_model is None else (fallback_model or None)
        self.temperature = temperature if temperature is not None else settings.GEMINI_TEMPERATURE
        self.timeout_seconds = timeout_seconds or settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GEMINI_MAX_RETRIES

        self._client = client

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def active_model(self) -> str:
        return self.primary_model

    @property
    def fallback_model_name(self) -> Optional[str]:
        return self.fallback_model

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ProviderAPIError(
                "GEMINI_API_KEY is not configured. Please set the GEMINI_API_KEY environment variable."
            )
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except Exception as exc:
            raise ProviderAPIError(f"Failed to initialize Google GenAI client: {exc}") from exc

    def _format_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Flattens chat messages into a unified prompt for Gemini.
        Preserves role distinctions (system instructions vs user queries).
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            if role == "SYSTEM":
                parts.append(f"[SYSTEM INSTRUCTION]\n{content}\n")
            elif role == "USER":
                parts.append(f"[USER]\n{content}\n")
            elif role == "ASSISTANT":
                parts.append(f"[ASSISTANT]\n{content}\n")
            else:
                parts.append(f"[{role}]\n{content}\n")
        parts.append("[RESPONSE]\nPlease return strictly valid JSON matching the requested structure:")
        return "\n".join(parts)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parses and sanitizes markdown-fenced or raw JSON from LLM response."""
        clean = text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError as exc:
            raise ProviderAPIError(f"Gemini response could not be parsed as valid JSON: {exc}. Content: {text[:200]}") from exc

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Synchronously generates structured JSON via Gemini with fail-fast guards and cooldown."""
        global _GEMINI_COOLDOWN_UNTIL

        # Check in-memory cooldown before attempting network calls
        now = time.time()
        if now < _GEMINI_COOLDOWN_UNTIL:
            remaining = int(_GEMINI_COOLDOWN_UNTIL - now)
            raise ProviderAPIError(
                f"Gemini provider is in cooldown for {remaining}s due to recent quota exhaustion. "
                "Failing fast to trigger cross-provider fallback."
            )

        client = self._get_client()
        chosen_model = model or self.primary_model
        temp = temperature if temperature is not None else self.temperature
        prompt = self._format_messages_to_prompt(messages)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temp,
            response_mime_type="application/json",
        )

        attempts = 0
        last_error = None
        while attempts < self.max_retries:
            attempts += 1
            try:
                response = client.models.generate_content(
                    model=chosen_model,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise ProviderAPIError("Gemini returned empty response text")
                return self._parse_json_response(response.text)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini sync attempt %d/%d for model %s failed: %s",
                    attempts, self.max_retries, chosen_model, str(exc)[:200]
                )

                # 1. Fail fast immediately on permanent errors (404, not found, deprecated model)
                if is_permanent_gemini_error(exc):
                    logger.info("Permanent error encountered on model %s; breaking retry loop immediately.", chosen_model)
                    break

                # 2. On quota exhaustion, set bounded cooldown and break immediately (no retry storm)
                if is_quota_exhausted_gemini_error(exc):
                    _GEMINI_COOLDOWN_UNTIL = time.time() + _DEFAULT_COOLDOWN_SECONDS
                    logger.warning("Quota exhausted for Gemini. Setting cooldown until +%ds; breaking retries.", _DEFAULT_COOLDOWN_SECONDS)
                    break

                if attempts < self.max_retries:
                    time_delay = min(4.0, (2 ** (attempts - 1))) + random.uniform(0.1, 0.5)
                    time.sleep(time_delay)

        # Fallback model attempt if primary model failed
        if self.fallback_model and self.fallback_model != chosen_model:
            # If error was quota exhaustion, fallback model on same account will also fail; don't thrash
            if not is_quota_exhausted_gemini_error(last_error):
                logger.info("Attempting fallback Gemini model: %s", self.fallback_model)
                try:
                    response = client.models.generate_content(
                        model=self.fallback_model,
                        contents=prompt,
                        config=config,
                    )
                    if response.text:
                        return self._parse_json_response(response.text)
                except Exception as fb_exc:
                    if is_quota_exhausted_gemini_error(fb_exc):
                        _GEMINI_COOLDOWN_UNTIL = time.time() + _DEFAULT_COOLDOWN_SECONDS
                    raise ProviderAPIError(
                        f"Both primary model ({chosen_model}) and fallback model ({self.fallback_model}) failed. "
                        f"Primary: {last_error}; Fallback: {fb_exc}"
                    ) from fb_exc

        raise ProviderAPIError(f"Gemini generate_json failed after {attempts} attempts: {last_error}") from last_error

    async def generate_json_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Asynchronously generates structured JSON via Gemini with fail-fast guards and cooldown."""
        global _GEMINI_COOLDOWN_UNTIL

        # Check in-memory cooldown before attempting network calls
        now = time.time()
        if now < _GEMINI_COOLDOWN_UNTIL:
            remaining = int(_GEMINI_COOLDOWN_UNTIL - now)
            raise ProviderAPIError(
                f"Gemini provider is in cooldown for {remaining}s due to recent quota exhaustion. "
                "Failing fast to trigger cross-provider fallback."
            )

        client = self._get_client()
        chosen_model = model or self.primary_model
        temp = temperature if temperature is not None else self.temperature
        prompt = self._format_messages_to_prompt(messages)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temp,
            response_mime_type="application/json",
        )

        attempts = 0
        last_error = None
        while attempts < self.max_retries:
            attempts += 1
            try:
                response = await client.aio.models.generate_content(
                    model=chosen_model,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise ProviderAPIError("Gemini returned empty async response text")
                return self._parse_json_response(response.text)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini async attempt %d/%d for model %s failed: %s",
                    attempts, self.max_retries, chosen_model, str(exc)[:200]
                )

                # 1. Fail fast immediately on permanent errors (404, not found, deprecated model)
                if is_permanent_gemini_error(exc):
                    logger.info("Permanent error encountered on async model %s; breaking retry loop immediately.", chosen_model)
                    break

                # 2. On quota exhaustion, set bounded cooldown and break immediately
                if is_quota_exhausted_gemini_error(exc):
                    _GEMINI_COOLDOWN_UNTIL = time.time() + _DEFAULT_COOLDOWN_SECONDS
                    logger.warning("Quota exhausted for Gemini in async. Setting cooldown until +%ds; breaking retries.", _DEFAULT_COOLDOWN_SECONDS)
                    break

                if attempts < self.max_retries:
                    delay = min(4.0, (2 ** (attempts - 1))) + random.uniform(0.1, 0.5)
                    await asyncio.sleep(delay)

        # Fallback model attempt
        if self.fallback_model and self.fallback_model != chosen_model:
            if not is_quota_exhausted_gemini_error(last_error):
                logger.info("Attempting fallback Gemini model in async: %s", self.fallback_model)
                try:
                    response = await client.aio.models.generate_content(
                        model=self.fallback_model,
                        contents=prompt,
                        config=config,
                    )
                    if response.text:
                        return self._parse_json_response(response.text)
                except Exception as fb_exc:
                    if is_quota_exhausted_gemini_error(fb_exc):
                        _GEMINI_COOLDOWN_UNTIL = time.time() + _DEFAULT_COOLDOWN_SECONDS
                    raise ProviderAPIError(
                        f"Both primary model ({chosen_model}) and fallback model ({self.fallback_model}) failed. "
                        f"Primary: {last_error}; Fallback: {fb_exc}"
                    ) from fb_exc

        raise ProviderAPIError(f"Gemini generate_json_async failed after {attempts} attempts: {last_error}") from last_error
