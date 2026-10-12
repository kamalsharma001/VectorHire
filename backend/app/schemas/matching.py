"""
VectorHire Semantic and Lexical Matching Contracts.
Represents candidate passages retrieved by hybrid search prior to verification.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import CandidateId, PassageId, RequirementId


class PassageMatchCandidate(BaseModel):
    """
    Candidate passage retrieved by the hybrid search engine for a specific requirement.
    Separates statistical/semantic retrieval relevance from factual truth verification.
    """
    candidate_id: CandidateId
    requirement_id: RequirementId
    passage_id: PassageId
    semantic_similarity: float = Field(..., ge=0.0, le=1.0, description="Dense cosine similarity")
    lexical_overlap: float = Field(default=0.0, ge=0.0, le=1.0, description="Exact/alias token score")
    hybrid_score: float = Field(..., ge=0.0, le=1.0, description="Fused retrieval score")
    matched_terms: List[str] = Field(default_factory=list, description="Keywords or aliases matched")
    passage_text: str = Field(..., min_length=1, description="Passage text evaluated")
    page_number: int = Field(..., ge=1, description="Page number of the passage")
    section_name: Optional[str] = Field(default=None, description="Optional section name where passage appears")
