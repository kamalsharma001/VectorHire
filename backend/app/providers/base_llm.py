"""
VectorHire Base LLM Provider Contract.
Defines the unified interface for LLM providers (Groq, Gemini, etc.)
supporting structured JSON generation with synchronous and asynchronous execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM providers offering structured JSON generation.
    """

    @abstractmethod
    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Synchronously generates a validated JSON dictionary response given chat messages.
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_json_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronously generates a validated JSON dictionary response given chat messages.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def active_model(self) -> str:
        """Identifier of the active primary model."""
        raise NotImplementedError

    @property
    @abstractmethod
    def fallback_model_name(self) -> Optional[str]:
        """Identifier of the fallback model, if any."""
        raise NotImplementedError
