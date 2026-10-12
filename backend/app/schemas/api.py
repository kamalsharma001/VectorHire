"""
VectorHire API Request and Response Schemas.
Defines typed Pydantic v2 contracts for REST endpoints:
- /health
- /analyze-job
- /analyze-resumes
- /generate-questions
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.common import CandidateId, RequirementCategory
from app.schemas.evaluation import CandidateScorecard
from app.schemas.job import JobSpecification


class HealthResponse(BaseModel):
    """System health, readiness, and operational configuration status."""
    status: str = Field(default="healthy", description="Application readiness status")
    version: str = Field(default="1.1.0", description="VectorHire API version")
    llm_provider: str = Field(default="gemini", description="Configured active LLM provider strategy ('gemini' or 'groq')")
    active_llm_model: str = Field(..., description="Configured primary LLM model for the active provider")
    fallback_llm_model: Optional[str] = Field(None, description="Configured internal model fallback for the active provider")
    cross_provider_fallback: Optional[str] = Field(
        default=None,
        description="Configured cross-provider fallback target when primary provider fails"
    )
    embedding_model: str = Field(..., description="Local ONNX embedding model")
    max_batch_size: int = Field(..., description="Maximum allowed resumes per batch")
    max_file_size_mb: int = Field(..., description="Maximum allowed file size in MB")
    max_concurrent_requests: int = Field(..., description="Maximum concurrency for external AI")
    gamma_uncertainty_discount: float = Field(..., description="Configured gamma discount factor")


class JobAnalysisRequest(BaseModel):
    """Recruiter payload submitting raw Job Description text for structured extraction."""
    job_description_text: str = Field(
        ...,
        min_length=20,
        max_length=50000,
        description="Raw unstructured text of the job description"
    )
    job_title_hint: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Optional recruiter-provided job title hint"
    )


class JobAnalysisResponse(BaseModel):
    """Structured, recruiter-editable job specification and versioned rubric."""
    job_spec: JobSpecification = Field(
        ...,
        description="Extracted job specification with categorized requirements and scoring rubric"
    )
    analysis_summary: Optional[str] = Field(
        default=None,
        description="Brief narrative summary of the extracted criteria and detected domain"
    )


class JobTextExtractionResponse(BaseModel):
    """Response containing sanitized text extracted from an uploaded job document."""
    text: str = Field(..., description="Extracted and sanitized text content")
    filename: str = Field(..., description="Original filename")
    format: str = Field(..., description="Detected document format (pdf, docx, txt)")
    character_count: int = Field(..., description="Number of characters in extracted text")


class InterviewQuestion(BaseModel):
    """
    Evidence-grounded interview question tailored to a specific candidate's evaluation.
    Grounded strictly in verified claims or identified evidence gaps without assuming incapacity.
    """
    requirement_id: str = Field(..., description="Referenced requirement ID")
    requirement_name: str = Field(..., description="Short name of the criterion")
    category: RequirementCategory = Field(..., description="Rubric category")
    question: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Targeted, respectful, evidence-probing question"
    )
    rationale: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Reason why this question is asked based on resume evidence or gaps"
    )
    focus_area: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Category of inquiry: verification, depth, or unevidenced requirement"
    )


class GenerateQuestionsRequest(BaseModel):
    """Request payload to generate interview questions for an evaluated candidate."""
    candidate_id: CandidateId = Field(..., description="Candidate ID to probe")
    candidate_name: str = Field(..., description="Candidate display name")
    job_spec: JobSpecification = Field(..., description="Frozen job specification")
    scorecard: CandidateScorecard = Field(..., description="Authoritative candidate scorecard")
    max_questions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of interview questions to generate"
    )


class GenerateQuestionsResponse(BaseModel):
    """Response payload containing generated interview questions."""
    candidate_id: CandidateId
    candidate_name: str
    total_questions: int = Field(..., ge=0)
    questions: List[InterviewQuestion] = Field(default_factory=list)
