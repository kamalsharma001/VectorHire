"""
VectorHire Typed Exception Hierarchy.
Provides distinct domain error classes for granular failure handling and client sanitization.
"""

from typing import Any, Dict, Optional


class VectorHireError(Exception):
    """Base exception for all VectorHire domain errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DocumentProcessingError(VectorHireError):
    """Raised when PDF reading, signature check, or text extraction fails."""
    pass


class InvalidEvidenceStateError(VectorHireError):
    """Raised when an unapproved or conflicting evidence state is encountered."""
    pass


class RubricValidationError(VectorHireError):
    """Raised when scoring rubric configuration, normalization, or weights are invalid."""
    pass


class ProviderAPIError(VectorHireError):
    """Raised when an upstream LLM or embedding provider call fails or times out."""
    pass


class CandidateEvaluationError(VectorHireError):
    """Raised when evaluation fails for a specific candidate, enabling isolated failure."""
    def __init__(self, candidate_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Evaluation failed for candidate {candidate_id}: {message}", details)
        self.candidate_id = candidate_id
