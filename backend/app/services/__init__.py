"""
VectorHire Core Services Package.
"""

from app.services.document_processing import (
    extract_candidate_profile,
    extract_pages_text,
    process_resume_pdf,
    sanitize_text,
    segment_into_passages,
    validate_pdf_bytes,
)
from app.services.evidence_verification import (
    calculate_token_jaccard,
    normalize_whitespace,
    verify_passage_provenance,
    verify_text_provenance,
)
from app.services.evaluation_pipeline import EvaluationPipeline
from app.services.resume_validation import (
    ConfidenceBand,
    ResumeValidationResult,
    ResumeValidationService,
    ResumeValidationStatus,
)
from app.services.semantic_matching import (
    calculate_passage_overlap,
    compute_lexical_match,
    cosine_similarity,
    retrieve_relevant_passages,
)

__all__ = [
    "validate_pdf_bytes",
    "sanitize_text",
    "extract_pages_text",
    "segment_into_passages",
    "process_resume_pdf",
    "calculate_token_jaccard",
    "normalize_whitespace",
    "verify_text_provenance",
    "verify_passage_provenance",
    "cosine_similarity",
    "compute_lexical_match",
    "calculate_passage_overlap",
    "retrieve_relevant_passages",
    "EvaluationPipeline",
    "ResumeValidationService",
    "ResumeValidationStatus",
    "ResumeValidationResult",
    "ConfidenceBand",
]
