"""
VectorHire Screening Session Context and State-Machine Scaffold.
Manages ephemeral batch execution, stage transitions, and individual candidate failure isolation.
"""

from typing import Dict, List, Optional
from app.schemas.common import CandidateId, PipelineStage
from app.schemas.job import JobSpecification
from app.schemas.pipeline import (
    CandidatePipelineRecord,
    PipelineErrorRecord,
    ScreeningSessionState,
)


class ScreeningSessionContext:
    """
    In-memory session context for a single job description and its batch of resumes.
    Strictly isolated per request; zero cross-session or persistent leakage.
    """
    def __init__(self, session_id: str, job_spec: JobSpecification):
        self.session_id = session_id
        self.job_spec = job_spec
        self.state = ScreeningSessionState(
            session_id=session_id,
            active_stage=PipelineStage.QUEUED,
            candidate_records={},
            total_submitted=0,
            total_completed=0,
            total_failed=0,
            is_terminal=False,
        )
        self.errors: List[PipelineErrorRecord] = []

    def register_candidate(self, candidate_id: CandidateId, filename: str) -> CandidatePipelineRecord:
        """Enrolls a candidate resume into the batch screening state machine."""
        record = CandidatePipelineRecord(
            candidate_id=candidate_id,
            filename=filename,
            current_stage=PipelineStage.QUEUED,
            is_successful=True,
            error=None
        )
        self.state.candidate_records[candidate_id] = record
        self.state.total_submitted += 1
        return record

    def transition_candidate_stage(self, candidate_id: CandidateId, new_stage: PipelineStage) -> None:
        """Transitions an individual candidate to a subsequent pipeline stage."""
        if candidate_id not in self.state.candidate_records:
            raise KeyError(f"Candidate '{candidate_id}' not found in active session.")
        record = self.state.candidate_records[candidate_id]
        if not record.is_successful:
            return  # Do not advance already failed candidates
        record.current_stage = new_stage

    def record_candidate_failure(
        self,
        candidate_id: CandidateId,
        filename: str,
        stage: PipelineStage,
        error_type: str,
        error_message: str
    ) -> PipelineErrorRecord:
        """
        Isolates a single candidate failure so that other batch resumes continue uninterrupted.
        """
        error_record = PipelineErrorRecord(
            candidate_id=candidate_id,
            filename=filename,
            stage=stage,
            error_type=error_type,
            error_message=error_message,
            is_fatal_for_candidate=True
        )
        self.errors.append(error_record)
        
        if candidate_id in self.state.candidate_records:
            record = self.state.candidate_records[candidate_id]
            record.is_successful = False
            record.current_stage = PipelineStage.FAILED
            record.error = error_record
            
        self.state.total_failed += 1
        return error_record

    def mark_candidate_completed(self, candidate_id: CandidateId) -> None:
        """Marks a candidate as successfully completed through all pipeline stages."""
        if candidate_id in self.state.candidate_records:
            record = self.state.candidate_records[candidate_id]
            if record.is_successful:
                record.current_stage = PipelineStage.COMPLETED
                self.state.total_completed += 1

    def is_candidate_failed(self, candidate_id: CandidateId) -> bool:
        """Checks if a candidate has encountered an isolated fatal error."""
        record = self.state.candidate_records.get(candidate_id)
        return record is not None and not record.is_successful

    def get_successful_candidates(self) -> List[CandidatePipelineRecord]:
        """Returns all candidates that are currently healthy and eligible for scoring."""
        return [r for r in self.state.candidate_records.values() if r.is_successful]

    def get_failed_candidates(self) -> List[PipelineErrorRecord]:
        """Returns all recorded partial failure records."""
        return self.errors

    def transition_session_stage(self, new_stage: PipelineStage) -> None:
        """Advances the overall batch workflow stage."""
        self.state.active_stage = new_stage

    def finalize_session(self) -> ScreeningSessionState:
        """Marks the session as terminal once all resumes have finished."""
        self.state.is_terminal = True
        self.state.active_stage = PipelineStage.COMPLETED
        return self.state
