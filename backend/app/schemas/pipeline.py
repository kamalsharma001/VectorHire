"""
VectorHire Pipeline State and Error Contracts.
Enables per-candidate failure isolation and granular stage tracking.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from app.schemas.common import CandidateId, PipelineStage


class PipelineErrorRecord(BaseModel):
    """
    Structured error record capturing failure during a specific stage.
    Enables partial batch failure isolation so one corrupt file does not abort the batch.
    """
    candidate_id: Optional[CandidateId] = None
    filename: str
    stage: PipelineStage
    error_type: str = Field(..., max_length=100)
    error_message: str = Field(..., max_length=1000)
    is_fatal_for_candidate: bool = Field(default=True)


class CandidatePipelineRecord(BaseModel):
    """
    Per-candidate state tracking record maintained during batch screening.
    """
    candidate_id: CandidateId
    filename: str
    current_stage: PipelineStage = Field(default=PipelineStage.QUEUED)
    is_successful: bool = Field(default=True)
    error: Optional[PipelineErrorRecord] = Field(default=None)


class ScreeningSessionState(BaseModel):
    """
    Ephemeral session state managing batch progress and candidate isolation.
    """
    session_id: str = Field(..., min_length=1, max_length=64)
    active_stage: PipelineStage = Field(default=PipelineStage.QUEUED)
    candidate_records: Dict[CandidateId, CandidatePipelineRecord] = Field(default_factory=dict)
    total_submitted: int = Field(default=0, ge=0)
    total_completed: int = Field(default=0, ge=0)
    total_failed: int = Field(default=0, ge=0)
    is_terminal: bool = Field(default=False)
