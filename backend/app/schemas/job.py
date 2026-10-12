"""
VectorHire Job Description and Requirement Contracts.
Defines individual criteria, category classification, and job specifications.
"""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator
from app.schemas.common import RequirementCategory, RequirementId
from app.schemas.rubric import ScoringRubric


class JobRequirement(BaseModel):
    """
    Structured job requirement extracted from the job description
    and confirmed or edited by the recruiter.
    """
    requirement_id: RequirementId = Field(
        ...,
        description="Immutable identifier preserved across the entire pipeline"
    )
    name: str = Field(..., min_length=2, max_length=150, description="Short human-readable name")
    description: str = Field(..., min_length=5, description="Specific expected capability or credential")
    category: RequirementCategory = Field(
        ...,
        description="Rubric category to which this requirement belongs"
    )
    is_hard_gate: bool = Field(
        default=False,
        description="Whether failure to evidence this requirement raises a human-review flag"
    )
    weight: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        description="Recruiter-assigned criterion importance weight within its category"
    )
    normalized_terms: List[str] = Field(
        default_factory=list,
        description="Canonical forms and standard spellings for lexical matching"
    )
    controlled_aliases: List[str] = Field(
        default_factory=list,
        description="Approved domain equivalents and acronyms"
    )
    ambiguity_notes: Optional[str] = Field(
        default=None,
        description="Notes regarding potential vagueness in the original text"
    )
    importance: str = Field(
        default="mandatory",
        description="Requirement importance tier: 'mandatory', 'preferred', or 'optional'"
    )
    expected_evidence: Optional[str] = Field(
        default=None,
        description="Expected supporting evidence or verification cues"
    )
    weight_rationale: Optional[str] = Field(
        default=None,
        description="Reasoning for assigned weight"
    )


class JobSpecification(BaseModel):
    """
    Complete frozen evaluation specification for a screening session.
    Combines extracted requirements with the frozen versioned rubric.
    """
    job_title: str = Field(..., min_length=2, max_length=150)
    detected_domain: str = Field(default="General Professional", max_length=100)
    seniority_level: str = Field(default="Not Specified", max_length=50)
    min_experience_years: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    requirements: List[JobRequirement] = Field(
        default_factory=list,
        description="List of all confirmed requirements"
    )
    rubric: ScoringRubric = Field(
        default_factory=ScoringRubric,
        description="Versioned scoring rubric with category weights and gamma"
    )

    @field_validator("requirements")
    @classmethod
    def validate_unique_requirement_ids(cls, v: List[JobRequirement]) -> List[JobRequirement]:
        """Ensures all requirement IDs within a job specification are unique."""
        seen = set()
        for req in v:
            if req.requirement_id in seen:
                raise ValueError(f"Duplicate requirement_id detected: {req.requirement_id}")
            seen.add(req.requirement_id)
        return v

    def get_active_categories(self) -> Set[RequirementCategory]:
        """Returns the set of rubric categories that contain at least one requirement."""
        return {req.category for req in self.requirements}

    def get_requirements_by_category(self, category: RequirementCategory) -> List[JobRequirement]:
        """Returns all requirements assigned to a given category."""
        return [req for req in self.requirements if req.category == category]

    def get_normalized_criterion_weights(self) -> Dict[str, float]:
        """
        Calculates within-category normalized weights (omega_jk) for every requirement.
        For each category, omega_jk = w_jk / sum(w_jm) such that criterion weights
        within the category sum strictly to 1.0.
        """
        normalized: Dict[str, float] = {}
        for cat in RequirementCategory:
            cat_reqs = self.get_requirements_by_category(cat)
            if not cat_reqs:
                continue
            cat_sum = sum(req.weight for req in cat_reqs)
            for req in cat_reqs:
                normalized[req.requirement_id] = req.weight / cat_sum if cat_sum > 0 else (1.0 / len(cat_reqs))
        return normalized

    def get_global_criterion_weights(self) -> Dict[str, float]:
        """
        Calculates globally normalized criterion weights across all requirements in the specification.
        Eliminates category-cardinality distortion: a requirement's contribution is proportional to its
        assigned weight/importance, independent of how many sibling requirements share its category.
        Guarantees that sum(weights) == 1.0 across all active criteria.
        """
        if not self.requirements:
            return {}
        total_weight = sum(req.weight for req in self.requirements)
        if total_weight <= 0:
            equal_share = 1.0 / len(self.requirements)
            return {req.requirement_id: equal_share for req in self.requirements}
        return {req.requirement_id: req.weight / total_weight for req in self.requirements}
