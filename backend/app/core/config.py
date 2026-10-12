"""
VectorHire Centralized Application Configuration.
Manages environment-driven settings, operational safeguards, and scoring defaults.
"""

from functools import lru_cache
from typing import Dict, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration for VectorHire backend services.
    All parameters are overridable via environment variables or a .env file.
    """
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API and Environment
    APP_NAME: str = "VectorHire"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins, or '*' for all origins"
    )

    # LLM Provider Configuration (gemini or groq)
    LLM_PROVIDER: str = Field(
        default="gemini",
        description="Active LLM provider: 'gemini' (primary) or 'groq'"
    )
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq Cloud API Key")
    GROQ_MODEL: str = Field(
        default="openai/gpt-oss-20b",
        description="Primary active Groq LLM model"
    )
    GROQ_FALLBACK_MODEL: str = Field(
        default="qwen/qwen3.8-27b",
        description="Fallback Groq LLM model if primary encounters outages"
    )
    GROQ_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=1.0)
    GROQ_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0.0)
    GROQ_MAX_RETRIES: int = Field(default=3, ge=1, le=5)
    GROQ_MAX_TOKENS: int = Field(
        default=1000,
        ge=100,
        le=4096,
        description="Maximum output tokens to respect Groq OTPM rate limits"
    )

    # Gemini LLM Configuration (Google GenAI)
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Primary active Gemini model"
    )
    GEMINI_FALLBACK_MODEL: Optional[str] = Field(
        default="gemini-1.5-flash",
        description="Fallback Gemini model"
    )
    GEMINI_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=1.0)
    GEMINI_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0.0)
    GEMINI_MAX_RETRIES: int = Field(default=3, ge=1, le=5)

    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Local ONNX embedding model for FastEmbed"
    )
    EMBEDDING_BATCH_SIZE: int = Field(default=32, ge=1, le=128)

    # Scoring & Rubric Defaults
    # Initial default gamma for partial/uncertain evidence
    UNCERTAINTY_DISCOUNT_GAMMA: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Score multiplier for relevant_but_uncertain evidence (0.0 to 1.0)"
    )

    # Category default weights (must sum to 1.0)
    DEFAULT_WEIGHT_MANDATORY_COMPETENCIES: float = Field(default=0.40, ge=0.0, le=1.0)
    DEFAULT_WEIGHT_REQUIRED_LICENSES: float = Field(default=0.30, ge=0.0, le=1.0)
    DEFAULT_WEIGHT_RELEVANT_EXPERIENCE: float = Field(default=0.20, ge=0.0, le=1.0)
    DEFAULT_WEIGHT_EDUCATION: float = Field(default=0.05, ge=0.0, le=1.0)
    DEFAULT_WEIGHT_PREFERRED_COMPETENCIES: float = Field(default=0.05, ge=0.0, le=1.0)

    # Operational Safeguards
    MAX_BATCH_SIZE: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Maximum number of resumes processed in a single batch"
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum allowed PDF file size in megabytes"
    )
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent outbound LLM requests via asyncio.Semaphore"
    )

    @field_validator("UNCERTAINTY_DISCOUNT_GAMMA")
    @classmethod
    def validate_gamma(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Gamma must be within [0.0, 1.0], got {v}")
        return v

    def get_default_category_weights(self) -> Dict[str, float]:
        """Returns the default unredistributed category weight mapping."""
        return {
            "mandatory_competencies": self.DEFAULT_WEIGHT_MANDATORY_COMPETENCIES,
            "license_registration": self.DEFAULT_WEIGHT_REQUIRED_LICENSES,
            "experience_tenure": self.DEFAULT_WEIGHT_RELEVANT_EXPERIENCE,
            "education": self.DEFAULT_WEIGHT_EDUCATION,
            "preferred_competencies": self.DEFAULT_WEIGHT_PREFERRED_COMPETENCIES,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Provides a cached singleton instance of Settings."""
    return Settings()
