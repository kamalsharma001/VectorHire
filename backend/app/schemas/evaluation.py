"""
VectorHire Criterion Evaluation, Scorecard, and Ranking Contracts.
Implements deterministic mathematical aggregation, review flags, and candidate ranking.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import (
    CandidateId,
    CandidateReviewStatus,
    EvidenceStatus,
    RequirementCategory,
    RequirementId,
)
from app.schemas.evidence import VerifiedEvidence
from app.schemas.pipeline import PipelineErrorRecord


class CriterionEvaluation(BaseModel):
    """
    Detailed evaluation record for a single requirement on a specific candidate.
    Binds verified evidence to points awarded based on the deterministic rubric.
    """
    requirement_id: RequirementId
    requirement_name: str
    category: RequirementCategory
    status: EvidenceStatus
    is_hard_gate: bool
    evidence: Optional[VerifiedEvidence] = None
    achievement_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calculated ratio: 1.0 (explicit), gamma (uncertain), 0.0 (not mentioned)"
    )
    points_awarded: float = Field(ge=0.0)
    max_points: float = Field(gt=0.0)
    within_category_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized weight omega_jk within its category"
    )
    human_review_required: bool = Field(
        default=False,
        description="True if an uncertain claim or missing hard gate requires human review"
    )
    review_reason: Optional[str] = Field(default=None)


class CandidateScorecard(BaseModel):
    """
    Authoritative score assessment for a single candidate.
    Calculated exclusively by deterministic mathematical logic using the frozen rubric.
    """
    candidate_id: CandidateId
    filename: str
    candidate_name: str
    rubric_version: int = Field(..., ge=1, description="Rubric version applied to this evaluation")
    total_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Aggregated score out of 100 calculated by deterministic formula"
    )
    category_scores: Dict[RequirementCategory, float] = Field(
        default_factory=dict,
        description="Score per category (0.0 to 100.0)"
    )
    effective_category_weights: Dict[RequirementCategory, float] = Field(
        default_factory=dict,
        description="Category weights after dynamic redistribution of empty categories"
    )
    evaluations: List[CriterionEvaluation] = Field(
        default_factory=list,
        description="Per-criterion evaluation breakdown"
    )
    hard_gate_passed: bool = Field(
        default=True,
        description="False if any is_hard_gate requirement lacks explicit evidence"
    )
    review_flags: List[str] = Field(
        default_factory=list,
        description="Human review warnings (missing hard gates, ambiguous evidence)"
    )
    formula_explanation: str = Field(
        ...,
        description="Human-readable mathematical trace of the total score calculation"
    )
    recruiter_status: CandidateReviewStatus = Field(
        default=CandidateReviewStatus.REVIEW,
        description="Recruiter review decision (Review, Shortlist, Reject)"
    )


class RankedCandidate(BaseModel):
    """
    Summary row in the side-by-side comparison matrix.
    """
    rank: int = Field(..., ge=1)
    candidate_id: CandidateId
    candidate_name: str
    filename: str
    total_score: float = Field(..., ge=0.0, le=100.0)
    hard_gate_passed: bool
    review_flags: List[str] = Field(default_factory=list)
    recruiter_status: CandidateReviewStatus = Field(default=CandidateReviewStatus.REVIEW)


class BatchScreeningResult(BaseModel):
    """
    Session-level evaluation result for an entire batch of resumes.
    """
    job_title: str
    rubric_version: int
    total_submitted: int = Field(..., ge=0)
    total_successful: int = Field(..., ge=0)
    total_failed: int = Field(..., ge=0)
    ranked_candidates: List[RankedCandidate] = Field(default_factory=list)
    scorecards: Dict[CandidateId, CandidateScorecard] = Field(default_factory=dict)
    comparative_summary: Optional[str] = Field(default=None)
    validation_errors: List[PipelineErrorRecord] = Field(
        default_factory=list,
        description="Records for files rejected at the validation gate or during ingestion"
    )

