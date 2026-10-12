"""
VectorHire Deterministic Scoring Engine.
Implements mathematical rubric scoring, weight redistribution, and ranking.
Guarantees that numeric scores are produced exclusively by deterministic logic.
"""

from typing import Dict, List
from app.schemas.common import CandidateReviewStatus, EvidenceStatus, RequirementCategory
from app.schemas.evaluation import CandidateScorecard, CriterionEvaluation, RankedCandidate
from app.schemas.job import JobSpecification


def calculate_candidate_scorecard(
    candidate_id: str,
    candidate_name: str,
    filename: str,
    job_spec: JobSpecification,
    evaluations: List[CriterionEvaluation],
    recruiter_status: CandidateReviewStatus = CandidateReviewStatus.REVIEW
) -> CandidateScorecard:
    """
    Computes an authoritative CandidateScorecard using deterministic mathematical rules.
    
    1. Determines active categories from requirements.
    2. Dynamically redistributes rubric weights across active categories.
    3. Normalizes criterion weights within each category.
    4. Computes achievement ratios using the rubric's configured gamma for uncertainty.
    5. Computes category sub-scores (0-100) and weighted total score (0-100).
    6. Identifies missing hard-gate requirements and attaches human-review flags.
    7. Produces a human-readable mathematical formula explanation.
    """
    # Map evaluations by requirement_id
    eval_map: Dict[str, CriterionEvaluation] = {e.requirement_id: e for e in evaluations}
    
    # Category sub-scores: Category -> score (0-100)
    category_scores: Dict[RequirementCategory, float] = {}
    
    # Active categories with at least one requirement
    active_categories = job_spec.get_active_categories()
    
    # Effective redistributed category weights (proportional to requirements under dynamic strategy)
    effective_weights = job_spec.rubric.calculate_effective_weights(
        active_categories,
        requirements=job_spec.requirements
    )
    
    # Within-category normalized criterion weights (omega_jk)
    criterion_weights = job_spec.get_normalized_criterion_weights()
    
    hard_gate_passed = True
    review_flags: List[str] = []
    gamma = job_spec.rubric.gamma
    
    for category in active_categories:
        cat_reqs = job_spec.get_requirements_by_category(category)
        if not cat_reqs:
            continue
            
        cat_points = 0.0
        for req in cat_reqs:
            norm_weight = criterion_weights.get(req.requirement_id, 1.0 / len(cat_reqs))
            criterion_eval = eval_map.get(req.requirement_id)
            
            if criterion_eval:
                status = criterion_eval.status
            else:
                # Missing evaluation defaults safely to not_mentioned
                status = EvidenceStatus.NOT_MENTIONED
                
            # Determine achievement ratio based on evidence status
            if status == EvidenceStatus.EXPLICITLY_SUPPORTED:
                ratio = 1.0
            elif status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                ratio = gamma
            else:
                # not_mentioned or contradictory_or_unverifiable
                ratio = 0.0
                
            cat_points += norm_weight * ratio
            
            # Check hard gate requirements
            if req.is_hard_gate:
                if status != EvidenceStatus.EXPLICITLY_SUPPORTED:
                    hard_gate_passed = False
                    flag = (
                        f"Human Review Required: Mandatory requirement '{req.name}' "
                        f"not evidenced in submitted resume."
                    )
                    if flag not in review_flags:
                        review_flags.append(flag)
                        
        category_scores[category] = round(cat_points * 100.0, 2)
        
    # Calculate weighted total score
    total_score = 0.0
    formula_parts: List[str] = []
    
    for category, cat_score in category_scores.items():
        weight = effective_weights.get(category, 0.0)
        weighted_cat_score = cat_score * weight
        total_score += weighted_cat_score
        formula_parts.append(f"({cat_score:.1f} * {weight:.2f})")
        
    total_score = round(min(100.0, max(0.0, total_score)), 2)
    formula_explanation = " + ".join(formula_parts) + f" = {total_score:.2f}"
    
    return CandidateScorecard(
        candidate_id=candidate_id,
        filename=filename,
        candidate_name=candidate_name,
        rubric_version=job_spec.rubric.rubric_version,
        total_score=total_score,
        category_scores=category_scores,
        effective_category_weights=effective_weights,
        evaluations=evaluations,
        hard_gate_passed=hard_gate_passed,
        review_flags=review_flags,
        formula_explanation=formula_explanation,
        recruiter_status=recruiter_status,
    )


def rank_candidates(scorecards: List[CandidateScorecard]) -> List[RankedCandidate]:
    """
    Ranks candidate scorecards in descending order of eligibility and total score.
    Candidates who pass all mandatory hard gates are prioritized over candidates
    failing hard gates. Ties preserve secondary score stability.
    """
    sorted_cards = sorted(
        scorecards,
        key=lambda c: (1 if c.hard_gate_passed else 0, c.total_score),
        reverse=True
    )
    
    ranked: List[RankedCandidate] = []
    for rank_idx, card in enumerate(sorted_cards, start=1):
        ranked.append(
            RankedCandidate(
                rank=rank_idx,
                candidate_id=card.candidate_id,
                candidate_name=card.candidate_name,
                filename=card.filename,
                total_score=card.total_score,
                hard_gate_passed=card.hard_gate_passed,
                review_flags=card.review_flags,
                recruiter_status=card.recruiter_status,
            )
        )
    return ranked
