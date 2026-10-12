"""
VectorHire Two-Stage Evidence Verification Contracts.
Separates verbatim source provenance from contextual requirement-support verification.
"""

from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import CandidateId, EvidenceStatus, PassageId, RequirementId


class SourceProvenance(BaseModel):
    """
    Stage 1 Result: Verifies that the proposed text span physically exists
    verbatim in the candidate's raw extracted document text.
    """
    provenance_verified: bool = Field(
        ...,
        description="Whether the exact text span was verified in the raw document"
    )
    candidate_id: Optional[CandidateId] = Field(default=None, description="Candidate ID for isolated provenance")
    requirement_id: Optional[RequirementId] = Field(default=None, description="Requirement ID evaluated")
    passage_id: Optional[PassageId] = Field(default=None, description="Passage ID where text was located")
    source_page: Optional[int] = Field(default=None, ge=1, description="1-indexed PDF page")
    source_section: Optional[str] = Field(default=None, max_length=100)
    character_start: Optional[int] = Field(default=None, ge=0)
    character_end: Optional[int] = Field(default=None, ge=0)
    exact_span_quote: Optional[str] = Field(default=None, max_length=1500)
    token_jaccard_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Token overlap score between proposed quote and document span"
    )
    exact_match: bool = Field(
        default=False,
        description="True if exact verbatim substring match was verified"
    )
    fuzzy_recovered: bool = Field(
        default=False,
        description="True if recovered via normalized line-wrap or whitespace matching"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if provenance verification failed"
    )


class VerifiedEvidence(BaseModel):
    """
    Stage 2 Result: Evaluates whether the proven passage context substantively
    satisfies the specific job requirement, classified under the 4-state taxonomy.
    """
    requirement_id: RequirementId = Field(..., description="Preserved requirement ID")
    candidate_id: CandidateId = Field(..., description="Preserved candidate ID")
    passage_id: Optional[PassageId] = Field(default=None)
    status: EvidenceStatus = Field(
        ...,
        description="4-state evidence classification (explicitly_supported, etc.)"
    )
    provenance: Optional[SourceProvenance] = Field(
        default=None,
        description="Stage 1 provenance details verifying text existence"
    )
    match_rationale: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Explanation of how the evidence satisfies or fails the requirement"
    )
    is_direct_execution: bool = Field(
        default=True,
        description="True if candidate directly executed the capability; False if incidental/assisting"
    )
    verification_notes: Optional[str] = Field(
        default=None,
        description="Human review notes or discrepancies observed in claims"
    )
