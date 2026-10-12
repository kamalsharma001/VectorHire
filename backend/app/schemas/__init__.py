"""
VectorHire Schemas Package.
Exposes domain contracts for job analysis, candidate profiles, evidence verification,
scoring rubrics, evaluation records, and pipeline states.
"""

from app.schemas.common import (
    EvidenceStatus,
    RequirementCategory,
    PipelineStage,
    CandidateReviewStatus,
    RequirementId,
    CandidateId,
    PassageId,
)
from app.schemas.rubric import ScoringRubric
from app.schemas.job import JobRequirement, JobSpecification
from app.schemas.candidate import ResumePassage, CandidateContact, CandidateProfile
from app.schemas.matching import PassageMatchCandidate
from app.schemas.evidence import SourceProvenance, VerifiedEvidence
from app.schemas.evaluation import (
    CriterionEvaluation,
    CandidateScorecard,
    RankedCandidate,
    BatchScreeningResult,
)
from app.schemas.pipeline import (
    PipelineErrorRecord,
    CandidatePipelineRecord,
    ScreeningSessionState,
)
from app.schemas.api import (
    HealthResponse,
    JobAnalysisRequest,
    JobAnalysisResponse,
    InterviewQuestion,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
)

__all__ = [
    "EvidenceStatus",
    "RequirementCategory",
    "PipelineStage",
    "CandidateReviewStatus",
    "RequirementId",
    "CandidateId",
    "PassageId",
    "ScoringRubric",
    "JobRequirement",
    "JobSpecification",
    "ResumePassage",
    "CandidateContact",
    "CandidateProfile",
    "PassageMatchCandidate",
    "SourceProvenance",
    "VerifiedEvidence",
    "CriterionEvaluation",
    "CandidateScorecard",
    "RankedCandidate",
    "BatchScreeningResult",
    "PipelineErrorRecord",
    "CandidatePipelineRecord",
    "ScreeningSessionState",
    "HealthResponse",
    "JobAnalysisRequest",
    "JobAnalysisResponse",
    "InterviewQuestion",
    "GenerateQuestionsRequest",
    "GenerateQuestionsResponse",
]
