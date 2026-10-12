"""
VectorHire Hybrid Semantic Retrieval Service.
Combines dense cosine similarity with lexical matching, controlled alias expansion,
and credential guards. Retrieves ranked passage candidates per requirement.
"""

import math
import re
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.candidate import ResumePassage
from app.schemas.common import CandidateId, RequirementCategory
from app.schemas.job import JobRequirement
from app.schemas.matching import PassageMatchCandidate
from app.providers.embedding_provider import BaseEmbeddingProvider
from app.services.terminology_normalizer import CanonicalTerminologyNormalizer, matches_boundary_term


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes cosine similarity between two float vectors.
    Clamps result within [0.0, 1.0] for normalized embedding vectors.
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, float(sim)))


def compute_lexical_match(
    requirement: JobRequirement,
    passage_text: str
) -> Tuple[float, List[str]]:
    """
    Computes a normalized lexical match score in [0.0, 1.0] using:
    1. Exact requirement name presence via boundary-aware matching.
    2. Canonical terms, punctuation variants, and bidirectional acronym expansions.
    3. Keyword token overlap for partial phrasal alignment.
    
    Returns:
        (lexical_score, matched_terms)
    """
    text_lower = passage_text.lower()
    matched_terms: List[str] = []

    # 1. Exact requirement name boundary match
    name_clean = requirement.name.lower().strip()
    exact_name_match = matches_boundary_term(name_clean, text_lower)
    if exact_name_match:
        matched_terms.append(requirement.name)

    # 2. Check canonical expanded terms, aliases, and punctuation variants
    expanded_terms = CanonicalTerminologyNormalizer.get_all_requirement_terms(
        name=requirement.name,
        description=requirement.description,
        normalized_terms=requirement.normalized_terms,
        controlled_aliases=requirement.controlled_aliases,
    )

    term_matches: Set[str] = set()
    for term in expanded_terms:
        term_clean = term.lower().strip()
        if not term_clean:
            continue
        if matches_boundary_term(term_clean, text_lower):
            term_matches.add(term)
            if term not in matched_terms:
                matched_terms.append(term)

    # 3. Keyword token overlap
    # Extract substantive words (> 2 chars, alphanumeric)
    req_tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", (requirement.name + " " + requirement.description).lower()))
    pass_tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", text_lower))

    token_overlap_ratio = len(req_tokens & pass_tokens) / len(req_tokens) if req_tokens else 0.0

    # Composite lexical score
    score = 0.0
    if exact_name_match:
        score += 0.40
    if term_matches:
        # Matching at least one declared alias or normalized term is a direct signal
        base_term_score = 0.35
        extra = 0.15 * min(1.0, len(term_matches) / 2.0)
        score += (base_term_score + extra)
    score += 0.20 * token_overlap_ratio

    # Deduplicate matched terms preserving insertion order
    deduped_matched: List[str] = list(dict.fromkeys(matched_terms))
    return min(1.0, max(0.0, score)), deduped_matched


def calculate_passage_overlap(pass_a: ResumePassage, pass_b: ResumePassage) -> float:
    """Calculates character span overlap ratio between two passages from the same candidate."""
    if pass_a.page_number != pass_b.page_number:
        return 0.0

    start = max(pass_a.character_start, pass_b.character_start)
    end = min(pass_a.character_end, pass_b.character_end)
    if start >= end:
        return 0.0

    overlap_len = end - start
    min_len = min(
        pass_a.character_end - pass_a.character_start,
        pass_b.character_end - pass_b.character_start
    )
    return overlap_len / min_len if min_len > 0 else 0.0


def retrieve_relevant_passages(
    requirement: JobRequirement,
    candidate_id: CandidateId,
    passages: List[ResumePassage],
    embedding_provider: BaseEmbeddingProvider,
    req_vector: Optional[List[float]] = None,
    passage_vectors: Optional[Dict[str, List[float]]] = None,
    alpha_dense: float = 0.65,
    beta_sparse: float = 0.35,
    min_hybrid_threshold: float = 0.45,
    top_k: int = 3
) -> List[PassageMatchCandidate]:
    """
    Retrieves and ranks the top-k candidate passages for a given requirement.
    
    Guarantees:
    - Binds dense cosine similarity and sparse lexical overlap.
    - Credential Guard: For licenses and hard-gate credentials, passages with zero
      lexical keyword match are heavily capped so they cannot pass admission thresholds.
    - Semantic Admission Path: For non-credential competencies, high dense similarity
      (>= 0.75) allows passages through even when phrasing contains previously unseen terms.
    - Suppresses duplicate/overlapping passages from the same candidate.
    - Evaluates strictly within the candidate's passages (session/candidate isolation).
    """
    if not passages:
        return []

    # 1. Obtain dense vector for requirement
    if req_vector is None:
        query_text = f"{requirement.name}: {requirement.description}"
        if requirement.normalized_terms:
            query_text += f" (Terms: {', '.join(requirement.normalized_terms)})"
        req_vector = embedding_provider.embed_text(query_text)

    # 2. Obtain dense vectors for passages
    if passage_vectors is None:
        passage_vectors = {}
        pass_texts = [p.text_content for p in passages]
        raw_vecs = embedding_provider.embed_batch(pass_texts)
        for p, vec in zip(passages, raw_vecs):
            passage_vectors[p.passage_id] = vec

    scored_candidates: List[PassageMatchCandidate] = []

    for p in passages:
        p_vec = passage_vectors.get(p.passage_id)
        if not p_vec:
            continue

        dense_sim = cosine_similarity(req_vector, p_vec)
        lexical_score, matched_terms = compute_lexical_match(requirement, p.text_content)

        # Regulated Credential Guard:
        # Licenses and certifications cannot be satisfied by semantic similarity alone.
        # If no license terms appear, cap score so semantic similarity alone does not hallucinate a license.
        is_credential = (
            requirement.category == RequirementCategory.LICENSE_REGISTRATION or
            any(lic in requirement.name.lower() for lic in ["license", "registration", "certified", "certification", "cpa", "rn license", "bar admission", "pe license"])
        )
        if is_credential and lexical_score == 0.0:
            # Semantic penalty: cap dense similarity contribution
            dense_sim = min(dense_sim, 0.35)

        hybrid_score = (alpha_dense * dense_sim) + (beta_sparse * lexical_score)
        hybrid_score = round(max(0.0, min(1.0, hybrid_score)), 4)

        # Candidate admission:
        # 1. Passes hybrid threshold (>= 0.45), OR
        # 2. For non-credential competencies, high dense similarity (>= 0.75) provides an admission path
        #    for genuine semantic matches lacking exact lexical overlap.
        passes_threshold = (hybrid_score >= min_hybrid_threshold)
        passes_dense_admission = (not is_credential and dense_sim >= 0.75)

        if passes_threshold or passes_dense_admission:
            scored_candidates.append(
                PassageMatchCandidate(
                    candidate_id=candidate_id,
                    requirement_id=requirement.requirement_id,
                    passage_id=p.passage_id,
                    semantic_similarity=round(dense_sim, 4),
                    lexical_overlap=round(lexical_score, 4),
                    hybrid_score=hybrid_score,
                    matched_terms=matched_terms,
                    passage_text=p.text_content,
                    page_number=p.page_number,
                    section_name=p.section_name,
                )
            )

    # Sort candidates descending by hybrid_score
    scored_candidates.sort(key=lambda x: x.hybrid_score, reverse=True)

    # Deduplicate overlapping passages
    deduped: List[PassageMatchCandidate] = []
    passage_map = {p.passage_id: p for p in passages}

    for cand in scored_candidates:
        cand_p = passage_map.get(cand.passage_id)
        if not cand_p:
            continue

        overlap_found = False
        for selected in deduped:
            selected_p = passage_map.get(selected.passage_id)
            if selected_p and calculate_passage_overlap(cand_p, selected_p) > 0.75:
                overlap_found = True
                break

        if not overlap_found:
            deduped.append(cand)
            if len(deduped) >= top_k:
                break

    return deduped
