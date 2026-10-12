"""
VectorHire Scoring Rubric Contracts and Weight Allocation Engine.
Implements category weighting, gamma configuration, and dynamic redistribution.
"""

from typing import Dict, List, Optional, Set
from pydantic import AliasChoices, BaseModel, Field, field_validator
from app.schemas.common import RequirementCategory


class ScoringRubric(BaseModel):
    """
    Versioned rubric contract defining evaluation weights and uncertainty discounts.
    Supports dynamic proportional weight redistribution when categories lack criteria.
    """
    rubric_id: str = Field(default="rubric_default", min_length=1, max_length=64)
    rubric_version: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("rubric_version", "version"),
        description="Incremented upon recruiter edits",
    )
    
    # Category weights mapping - must sum to 1.0
    weights: Dict[RequirementCategory, float] = Field(
        default={
            RequirementCategory.MANDATORY_COMPETENCY: 0.40,
            RequirementCategory.LICENSE_REGISTRATION: 0.30,
            RequirementCategory.EXPERIENCE_TENURE: 0.20,
            RequirementCategory.EDUCATION: 0.05,
            RequirementCategory.PREFERRED_COMPETENCY: 0.05,
        },
        validation_alias=AliasChoices("weights", "category_weights"),
        description="Category weight allocation; initial defaults sum to 1.0",
    )

    # Uncertainty discount factor (gamma) for relevant_but_uncertain evidence
    gamma: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Partial-evidence uncertainty multiplier"
    )

    rubric_strategy: str = Field(
        default="category_fixed",
        description="Weighting strategy: 'dynamic_importance' (proportional to requirement weights) or 'category_fixed' (fixed 5-category buckets)"
    )

    @field_validator("weights")
    @classmethod
    def validate_weights_sum(cls, v: Dict[RequirementCategory, float]) -> Dict[RequirementCategory, float]:
        """Ensures that defined category weights sum to 1.0 within float tolerance."""
        total = sum(v.values())
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"Rubric category weights must sum to 1.0 (got {total:.4f})")
        return v

    def calculate_effective_weights(
        self,
        active_categories: Set[RequirementCategory],
        requirements: Optional[list] = None,
    ) -> Dict[RequirementCategory, float]:
        """
        Calculates effective normalized category weights for a specific job description.
        If requirements are provided and strategy is 'dynamic_importance', category weights
        are proportional to the sum of requirement weights in each category.
        Otherwise, proportionally rescales the rubric's configured category weights.
        """
        if not active_categories:
            return {}

        # 1. Dynamic importance strategy when requirements are provided
        if requirements and self.rubric_strategy == "dynamic_importance":
            total_active_weight = sum(
                r.weight for r in requirements
                if getattr(r, "category", None) in active_categories
            )
            if total_active_weight > 0.0:
                effective: Dict[RequirementCategory, float] = {}
                for cat in active_categories:
                    cat_weight = sum(
                        r.weight for r in requirements
                        if getattr(r, "category", None) == cat
                    )
                    effective[cat] = cat_weight / total_active_weight
                return effective

        # 2. Fixed category weight proportional rescaling (backward-compatible fallback)
        active_sum = sum(
            weight for cat, weight in self.weights.items()
            if cat in active_categories
        )

        if active_sum <= 0.0:
            equal_share = 1.0 / len(active_categories)
            return {cat: equal_share for cat in active_categories}

        effective: Dict[RequirementCategory, float] = {}
        for cat in active_categories:
            raw_weight = self.weights.get(cat, 0.0)
            effective[cat] = raw_weight / active_sum

        return effective
