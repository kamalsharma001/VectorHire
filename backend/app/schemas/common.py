"""
VectorHire Common Schemas, Enums, and Constants.
Defines foundational taxonomies, stable identifier patterns, and pipeline statuses.
"""

from enum import Enum
import re
from typing import Annotated
from pydantic import Field, StringConstraints


class EvidenceStatus(str, Enum):
    """
    Controlled 4-state taxonomy representing verified relationship
    between a job requirement and candidate document evidence.
    """
    EXPLICITLY_SUPPORTED = "explicitly_supported"
    RELEVANT_BUT_UNCERTAIN = "relevant_but_uncertain"
    NOT_MENTIONED = "not_mentioned"
    CONTRADICTORY_OR_UNVERIFIABLE = "contradictory_or_unverifiable"


class RequirementCategory(str, Enum):
    """
    Universal 5-category evaluation rubric dimensions.
    """
    MANDATORY_COMPETENCY = "mandatory_competencies"
    LICENSE_REGISTRATION = "license_registration"
    EXPERIENCE_TENURE = "experience_tenure"
    EDUCATION = "education"
    PREFERRED_COMPETENCY = "preferred_competencies"


class PipelineStage(str, Enum):
    """
    Discrete lifecycle stages for candidate resume processing.
    """
    QUEUED = "queued"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    EMBEDDING = "embedding"
    VERIFYING = "verifying"
    EVALUATING = "evaluating"
    SCORING = "scoring"
    COMPLETED = "completed"
    FAILED = "failed"


class CandidateReviewStatus(str, Enum):
    """
    Recruiter decision designations maintained in session state.
    """
    REVIEW = "Review"
    SHORTLIST = "Shortlist"
    REJECT = "Reject"


# Stable ID constraint definitions
RequirementId = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-]+$"
    )
]

CandidateId = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-]+$"
    )
]

PassageId = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-]+$"
    )
]
