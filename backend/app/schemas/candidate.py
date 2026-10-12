"""
VectorHire Candidate Profile and Segmented Passage Contracts.
Preserves page-level source attribution, character offsets, and candidate metadata.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import CandidateId, PassageId


class ResumePassage(BaseModel):
    """
    Segmented text chunk derived from a candidate resume document.
    Maintains exact source page attribution and character bounds.
    """
    passage_id: PassageId = Field(..., description="Unique passage ID within the candidate profile")
    candidate_id: CandidateId = Field(..., description="Parent candidate identifier")
    page_number: int = Field(..., ge=1, description="1-indexed PDF page where passage occurs")
    section_name: str = Field(default="General", max_length=100, description="Section heading context")
    text_content: str = Field(..., min_length=10, max_length=5000, description="Text passage content")
    character_start: int = Field(..., ge=0, description="Character offset start in raw text")
    character_end: int = Field(..., ge=0, description="Character offset end in raw text")


class CandidateContact(BaseModel):
    """Extracted contact information; masked before transmission to external AI."""
    email: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=150)
    linkedin: Optional[str] = Field(default=None, max_length=200)
    github: Optional[str] = Field(default=None, max_length=200)


class CandidateProfile(BaseModel):
    """
    Structured candidate representation produced by the document ingestion stage.
    """
    candidate_id: CandidateId = Field(..., description="Unique candidate ID for the session")
    filename: str = Field(..., min_length=1, max_length=255, description="Original uploaded filename")
    candidate_name: str = Field(default="Unknown Candidate", max_length=150)
    contact_info: CandidateContact = Field(default_factory=CandidateContact)
    professional_summary: Optional[str] = Field(default=None, max_length=1000)
    passages: List[ResumePassage] = Field(default_factory=list, description="Indexed passages")
    extraction_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings regarding formatting or unreadable blocks"
    )
    raw_text_length: int = Field(default=0, ge=0, description="Total extracted character count")
