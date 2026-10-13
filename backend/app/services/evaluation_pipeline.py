"""
VectorHire End-to-End Evaluation Pipeline Service.
Coordinates:
1. Hybrid Semantic Retrieval of candidate passages.
2. Deterministic Stage 1 Provenance Verification.
3. Contextual Stage 2 Support Verification (via GroqProvider).
4. Deterministic Rubric Math & Scorecard Generation.
5. Batch screening with concurrency limits and isolated candidate failure recovery.
"""

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.exceptions import CandidateEvaluationError, VectorHireError
from app.orchestration.scoring import calculate_candidate_scorecard, rank_candidates
from app.orchestration.state import ScreeningSessionContext
from app.providers.embedding_provider import BaseEmbeddingProvider, get_embedding_provider
from app.schemas.candidate import CandidateProfile, ResumePassage
from app.schemas.common import CandidateId, EvidenceStatus, PipelineStage
from app.schemas.evaluation import BatchScreeningResult, CandidateScorecard, CriterionEvaluation
from app.schemas.evidence import SourceProvenance, VerifiedEvidence
from app.schemas.job import JobSpecification
from app.schemas.pipeline import PipelineErrorRecord
from app.services.evidence_verification import extract_concise_source_span, verify_text_provenance
from app.services.semantic_matching import retrieve_relevant_passages
from app.agents.support_verifier import ContextualSupportVerifier

logger = logging.getLogger(__name__)


class EvaluationPipeline:
    """
    Authoritative evaluation engine executing the two-stage verification pipeline
    and deterministic rubric scoring.
    """

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        verifier: Optional[ContextualSupportVerifier] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.verifier = verifier or ContextualSupportVerifier()

    def evaluate_candidate(
        self,
        candidate: CandidateProfile,
        job_spec: JobSpecification,
        raw_document_text: Optional[str] = None,
    ) -> CandidateScorecard:
        """
        Synchronously evaluates a single CandidateProfile against a JobSpecification.
        Ties together Hybrid Retrieval -> Provenance -> Support Verification -> Scorecard.
        """
        raw_text = raw_document_text or "\n\n".join(p.text_content for p in candidate.passages)
        criterion_weights = job_spec.get_normalized_criterion_weights()
        gamma = job_spec.rubric.gamma

        # Precompute embeddings
        passage_vectors: Dict[str, List[float]] = {}
        if candidate.passages:
            p_texts = [p.text_content for p in candidate.passages]
            p_vecs = self.embedding_provider.embed_batch(p_texts)
            for p, v in zip(candidate.passages, p_vecs):
                passage_vectors[p.passage_id] = v

        evaluations: List[CriterionEvaluation] = []

        for req in job_spec.requirements:
            norm_weight = criterion_weights.get(req.requirement_id, 0.0)

            # 1. Hybrid Retrieval (bounded top_k=2 for surrounding evidence context)
            retrieved = retrieve_relevant_passages(
                requirement=req,
                candidate_id=candidate.candidate_id,
                passages=candidate.passages,
                embedding_provider=self.embedding_provider,
                passage_vectors=passage_vectors,
                top_k=2,
            )

            verified_evidence: VerifiedEvidence

            if not retrieved:
                # No passages retrieved above threshold
                verified_evidence = self.verifier.verify_requirement_support(
                    requirement=req,
                    candidate_id=candidate.candidate_id,
                    evidence_text=None,
                    provenance=None,
                    passage_id=None,
                )
            else:
                top_match = retrieved[0]
                top_p = next((p for p in candidate.passages if p.passage_id == top_match.passage_id), None)
                search_terms = top_match.matched_terms or req.normalized_terms or [req.name]

                # Extract concise focused quote (<= 350 chars) from passage around requirement terms
                if top_p and len(top_p.text_content) > 350:
                    _, _, proposed_quote = extract_concise_source_span(
                        raw_document_text=raw_text,
                        char_start=top_p.character_start,
                        char_end=top_p.character_end,
                        max_length=350,
                        search_terms=search_terms,
                    )
                else:
                    proposed_quote = top_match.passage_text

                # 2. Stage 1: Deterministic Provenance Verification for top match
                provenance = verify_text_provenance(
                    candidate_id=candidate.candidate_id,
                    requirement_id=req.requirement_id,
                    proposed_quote=proposed_quote,
                    raw_document_text=raw_text,
                    passages=candidate.passages,
                    passage_id=top_match.passage_id,
                    page_number=top_match.page_number,
                )

                # 3. Stage 2: Contextual Support Verification with optional supporting context
                top_quote = (
                    provenance.exact_span_quote
                    if (provenance and provenance.provenance_verified and provenance.exact_span_quote)
                    else top_match.passage_text[:1000]
                )

                if len(retrieved) > 1:
                    sec_match = retrieved[1]
                    sec_prov = verify_text_provenance(
                        candidate_id=candidate.candidate_id,
                        requirement_id=req.requirement_id,
                        proposed_quote=sec_match.passage_text,
                        raw_document_text=raw_text,
                        passages=candidate.passages,
                        passage_id=sec_match.passage_id,
                        page_number=sec_match.page_number,
                    )
                    sec_quote = (
                        sec_prov.exact_span_quote
                        if (sec_prov and sec_prov.provenance_verified and sec_prov.exact_span_quote)
                        else sec_match.passage_text
                    )
                    evidence_to_audit = (
                        f"Primary Evidence (Page {top_match.page_number}, Section: {top_match.section_name or 'General'}):\n"
                        f"{top_quote[:900]}\n\n"
                        f"Supporting Context (Page {sec_match.page_number}, Section: {sec_match.section_name or 'General'}):\n"
                        f"{sec_quote[:450]}"
                    )
                else:
                    evidence_to_audit = top_quote[:1500]

                verified_evidence = self.verifier.verify_requirement_support(
                    requirement=req,
                    candidate_id=candidate.candidate_id,
                    evidence_text=evidence_to_audit,
                    provenance=provenance,
                    passage_id=top_match.passage_id,
                )

            # Determine mathematical achievement ratio
            if verified_evidence.status == EvidenceStatus.EXPLICITLY_SUPPORTED:
                ratio = 1.0
            elif verified_evidence.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                ratio = gamma
            else:
                ratio = 0.0

            # Determine human review flag
            human_review = False
            review_reason: Optional[str] = None

            if req.is_hard_gate and verified_evidence.status != EvidenceStatus.EXPLICITLY_SUPPORTED:
                human_review = True
                review_reason = (
                    f"Human Review Required: Mandatory requirement '{req.name}' "
                    f"not evidenced in submitted resume."
                )
            elif verified_evidence.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                human_review = True
                review_reason = f"Uncertain Evidence: Evidence for '{req.name}' is partial or ambiguous."

            points_awarded = round(norm_weight * ratio, 4)

            evaluations.append(
                CriterionEvaluation(
                    requirement_id=req.requirement_id,
                    requirement_name=req.name,
                    category=req.category,
                    status=verified_evidence.status,
                    is_hard_gate=req.is_hard_gate,
                    evidence=verified_evidence,
                    achievement_ratio=ratio,
                    points_awarded=points_awarded,
                    max_points=norm_weight if norm_weight > 0 else 1.0,
                    within_category_weight=norm_weight,
                    human_review_required=human_review,
                    review_reason=review_reason,
                )
            )

        # 4. Deterministic Rubric Scoring
        return calculate_candidate_scorecard(
            candidate_id=candidate.candidate_id,
            candidate_name=candidate.candidate_name,
            filename=candidate.filename,
            job_spec=job_spec,
            evaluations=evaluations,
        )

    async def evaluate_candidate_async(
        self,
        candidate: CandidateProfile,
        job_spec: JobSpecification,
        raw_document_text: Optional[str] = None,
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> CandidateScorecard:
        """
        Asynchronously evaluates a single CandidateProfile with semaphore-controlled concurrency.
        """
        raw_text = raw_document_text or "\n\n".join(p.text_content for p in candidate.passages)
        criterion_weights = job_spec.get_normalized_criterion_weights()
        gamma = job_spec.rubric.gamma

        # Precompute embeddings
        passage_vectors: Dict[str, List[float]] = {}
        if candidate.passages:
            p_texts = [p.text_content for p in candidate.passages]
            p_vecs = self.embedding_provider.embed_batch(p_texts)
            for p, v in zip(candidate.passages, p_vecs):
                passage_vectors[p.passage_id] = v

        evaluations: List[CriterionEvaluation] = []

        for req in job_spec.requirements:
            norm_weight = criterion_weights.get(req.requirement_id, 0.0)

            # 1. Hybrid Retrieval (bounded top_k=2 for surrounding evidence context)
            retrieved = retrieve_relevant_passages(
                requirement=req,
                candidate_id=candidate.candidate_id,
                passages=candidate.passages,
                embedding_provider=self.embedding_provider,
                passage_vectors=passage_vectors,
                top_k=2,
            )

            verified_evidence: VerifiedEvidence

            if not retrieved:
                verified_evidence = await self.verifier.verify_requirement_support_async(
                    requirement=req,
                    candidate_id=candidate.candidate_id,
                    evidence_text=None,
                    provenance=None,
                    passage_id=None,
                )
            else:
                top_match = retrieved[0]
                top_p = next((p for p in candidate.passages if p.passage_id == top_match.passage_id), None)
                search_terms = top_match.matched_terms or req.normalized_terms or [req.name]

                # Extract concise focused quote (<= 350 chars) from passage around requirement terms
                if top_p and len(top_p.text_content) > 350:
                    _, _, proposed_quote = extract_concise_source_span(
                        raw_document_text=raw_text,
                        char_start=top_p.character_start,
                        char_end=top_p.character_end,
                        max_length=350,
                        search_terms=search_terms,
                    )
                else:
                    proposed_quote = top_match.passage_text

                provenance = verify_text_provenance(
                    candidate_id=candidate.candidate_id,
                    requirement_id=req.requirement_id,
                    proposed_quote=proposed_quote,
                    raw_document_text=raw_text,
                    passages=candidate.passages,
                    passage_id=top_match.passage_id,
                    page_number=top_match.page_number,
                )

                top_quote = (
                    provenance.exact_span_quote
                    if (provenance and provenance.provenance_verified and provenance.exact_span_quote)
                    else top_match.passage_text[:1000]
                )

                if len(retrieved) > 1:
                    sec_match = retrieved[1]
                    sec_prov = verify_text_provenance(
                        candidate_id=candidate.candidate_id,
                        requirement_id=req.requirement_id,
                        proposed_quote=sec_match.passage_text,
                        raw_document_text=raw_text,
                        passages=candidate.passages,
                        passage_id=sec_match.passage_id,
                        page_number=sec_match.page_number,
                    )
                    sec_quote = (
                        sec_prov.exact_span_quote
                        if (sec_prov and sec_prov.provenance_verified and sec_prov.exact_span_quote)
                        else sec_match.passage_text
                    )
                    evidence_to_audit = (
                        f"Primary Evidence (Page {top_match.page_number}, Section: {top_match.section_name or 'General'}):\n"
                        f"{top_quote[:900]}\n\n"
                        f"Supporting Context (Page {sec_match.page_number}, Section: {sec_match.section_name or 'General'}):\n"
                        f"{sec_quote[:450]}"
                    )
                else:
                    evidence_to_audit = top_quote[:1500]

                if semaphore:
                    async with semaphore:
                        verified_evidence = await self.verifier.verify_requirement_support_async(
                            requirement=req,
                            candidate_id=candidate.candidate_id,
                            evidence_text=evidence_to_audit,
                            provenance=provenance,
                            passage_id=top_match.passage_id,
                        )
                else:
                    verified_evidence = await self.verifier.verify_requirement_support_async(
                        requirement=req,
                        candidate_id=candidate.candidate_id,
                        evidence_text=evidence_to_audit,
                        provenance=provenance,
                        passage_id=top_match.passage_id,
                    )

            if verified_evidence.status == EvidenceStatus.EXPLICITLY_SUPPORTED:
                ratio = 1.0
            elif verified_evidence.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                ratio = gamma
            else:
                ratio = 0.0

            human_review = False
            review_reason: Optional[str] = None

            if req.is_hard_gate and verified_evidence.status != EvidenceStatus.EXPLICITLY_SUPPORTED:
                human_review = True
                review_reason = (
                    f"Human Review Required: Mandatory requirement '{req.name}' "
                    f"not evidenced in submitted resume."
                )
            elif verified_evidence.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                human_review = True
                review_reason = f"Uncertain Evidence: Evidence for '{req.name}' is partial or ambiguous."

            points_awarded = round(norm_weight * ratio, 4)

            evaluations.append(
                CriterionEvaluation(
                    requirement_id=req.requirement_id,
                    requirement_name=req.name,
                    category=req.category,
                    status=verified_evidence.status,
                    is_hard_gate=req.is_hard_gate,
                    evidence=verified_evidence,
                    achievement_ratio=ratio,
                    points_awarded=points_awarded,
                    max_points=norm_weight if norm_weight > 0 else 1.0,
                    within_category_weight=norm_weight,
                    human_review_required=human_review,
                    review_reason=review_reason,
                )
            )

        return calculate_candidate_scorecard(
            candidate_id=candidate.candidate_id,
            candidate_name=candidate.candidate_name,
            filename=candidate.filename,
            job_spec=job_spec,
            evaluations=evaluations,
        )

    def evaluate_batch(
        self,
        candidates_data: List[Tuple[CandidateProfile, str]],
        job_spec: JobSpecification,
    ) -> BatchScreeningResult:
        """
        Synchronously evaluates a batch of candidates against a job specification.
        Isolates failures so a single corrupt candidate does not abort the batch.
        """
        if len(candidates_data) > self.settings.MAX_BATCH_SIZE:
            raise VectorHireError(
                f"Batch size {len(candidates_data)} exceeds maximum allowed limit "
                f"of {self.settings.MAX_BATCH_SIZE} resumes."
            )

        scorecards: Dict[CandidateId, CandidateScorecard] = {}
        validation_errors: List[PipelineErrorRecord] = []
        total_failed = 0

        for candidate, raw_text in candidates_data:
            try:
                card = self.evaluate_candidate(candidate, job_spec, raw_text)
                scorecards[candidate.candidate_id] = card
            except Exception as exc:
                logger.error(
                    "Isolated candidate evaluation failure for %s (%s): %s",
                    candidate.candidate_id,
                    candidate.filename,
                    str(exc)[:200],
                )
                total_failed += 1
                validation_errors.append(
                    PipelineErrorRecord(
                        candidate_id=candidate.candidate_id,
                        filename=candidate.filename,
                        stage=PipelineStage.EVALUATING,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:1000],
                        is_fatal_for_candidate=True,
                    )
                )

        total_successful = len(scorecards)
        ranked = rank_candidates(list(scorecards.values()))

        return BatchScreeningResult(
            job_title=job_spec.job_title,
            rubric_version=job_spec.rubric.rubric_version,
            total_submitted=len(candidates_data),
            total_successful=total_successful,
            total_failed=total_failed,
            ranked_candidates=ranked,
            scorecards=scorecards,
            validation_errors=validation_errors,
        )

    async def evaluate_staged_batch_async(
        self,
        candidates_data: List[Tuple[CandidateProfile, str]],
        job_spec: JobSpecification,
        on_stage_start: Optional[Callable[[int, str, str], Awaitable[None]]] = None,
        on_stage_complete: Optional[Callable[[int, str, str], Awaitable[None]]] = None,
    ) -> BatchScreeningResult:
        """
        Asynchronously evaluates a batch of candidates across stages 3, 4, and 5 with
        genuine progress notifications and failure isolation.
        """
        if len(candidates_data) > self.settings.MAX_BATCH_SIZE:
            raise VectorHireError(
                f"Batch size {len(candidates_data)} exceeds maximum allowed limit "
                f"of {self.settings.MAX_BATCH_SIZE} resumes."
            )

        criterion_weights = job_spec.get_normalized_criterion_weights()
        gamma = job_spec.rubric.gamma

        # =========================================================================
        # Stage 3: Matching Requirements & Retrieving Evidence
        # =========================================================================
        if on_stage_start:
            await on_stage_start(2, "03", "Matching requirements and retrieving candidate evidence spans...")

        candidate_matches: Dict[str, Dict[str, dict]] = {}
        for candidate, raw_text in candidates_data:
            c_matches = {}
            passage_vectors: Dict[str, List[float]] = {}
            if candidate.passages:
                p_texts = [p.text_content for p in candidate.passages]
                p_vecs = self.embedding_provider.embed_batch(p_texts)
                for p, v in zip(candidate.passages, p_vecs):
                    passage_vectors[p.passage_id] = v

            for req in job_spec.requirements:
                norm_weight = criterion_weights.get(req.requirement_id, 0.0)
                retrieved = retrieve_relevant_passages(
                    requirement=req,
                    candidate_id=candidate.candidate_id,
                    passages=candidate.passages,
                    embedding_provider=self.embedding_provider,
                    passage_vectors=passage_vectors,
                    top_k=2,
                )

                if not retrieved:
                    top_match = None
                    sec_match = None
                    proposed_quote = None
                else:
                    top_match = retrieved[0]
                    top_p = next((p for p in candidate.passages if p.passage_id == top_match.passage_id), None)
                    search_terms = top_match.matched_terms or req.normalized_terms or [req.name]

                    if top_p and len(top_p.text_content) > 350:
                        _, _, proposed_quote = extract_concise_source_span(
                            raw_document_text=raw_text,
                            char_start=top_p.character_start,
                            char_end=top_p.character_end,
                            max_length=350,
                            search_terms=search_terms,
                        )
                    else:
                        proposed_quote = top_match.passage_text

                    sec_match = retrieved[1] if len(retrieved) > 1 else None

                c_matches[req.requirement_id] = {
                    "req": req,
                    "norm_weight": norm_weight,
                    "retrieved": retrieved,
                    "top_match": top_match,
                    "sec_match": sec_match,
                    "proposed_quote": proposed_quote,
                }
            candidate_matches[candidate.candidate_id] = c_matches

        if on_stage_complete:
            await on_stage_complete(2, "03", "Requirements matched and candidate evidence spans retrieved.")

        # =========================================================================
        # Stage 4: Verifying Supporting Evidence
        # =========================================================================
        if on_stage_start:
            await on_stage_start(3, "04", "Verifying source provenance and contextual capability support...")

        semaphore = asyncio.Semaphore(self.settings.MAX_CONCURRENT_REQUESTS)
        candidate_evaluations: Dict[str, List[CriterionEvaluation]] = {}
        validation_errors: List[PipelineErrorRecord] = []
        total_failed = 0

        for candidate, raw_text in candidates_data:
            evaluations: List[CriterionEvaluation] = []
            try:
                c_matches = candidate_matches.get(candidate.candidate_id, {})
                for req in job_spec.requirements:
                    match_info = c_matches.get(req.requirement_id)
                    norm_weight = match_info["norm_weight"] if match_info else 0.0
                    retrieved = match_info["retrieved"] if match_info else []
                    top_match = match_info["top_match"] if match_info else None
                    sec_match = match_info["sec_match"] if match_info else None
                    proposed_quote = match_info["proposed_quote"] if match_info else None

                    if not retrieved or not top_match:
                        async with semaphore:
                            verified_evidence = await self.verifier.verify_requirement_support_async(
                                requirement=req,
                                candidate_id=candidate.candidate_id,
                                evidence_text=None,
                                provenance=None,
                                passage_id=None,
                            )
                    else:
                        provenance = verify_text_provenance(
                            candidate_id=candidate.candidate_id,
                            requirement_id=req.requirement_id,
                            proposed_quote=proposed_quote,
                            raw_document_text=raw_text,
                            passages=candidate.passages,
                            passage_id=top_match.passage_id,
                            page_number=top_match.page_number,
                        )

                        top_quote = (
                            provenance.exact_span_quote
                            if (provenance and provenance.provenance_verified and provenance.exact_span_quote)
                            else top_match.passage_text[:1000]
                        )

                        if sec_match:
                            sec_prov = verify_text_provenance(
                                candidate_id=candidate.candidate_id,
                                requirement_id=req.requirement_id,
                                proposed_quote=sec_match.passage_text,
                                raw_document_text=raw_text,
                                passages=candidate.passages,
                                passage_id=sec_match.passage_id,
                                page_number=sec_match.page_number,
                            )
                            sec_quote = (
                                sec_prov.exact_span_quote
                                if (sec_prov and sec_prov.provenance_verified and sec_prov.exact_span_quote)
                                else sec_match.passage_text
                            )
                            evidence_to_audit = (
                                f"Primary Evidence (Page {top_match.page_number}, Section: {top_match.section_name or 'General'}):\n"
                                f"{top_quote[:900]}\n\n"
                                f"Supporting Context (Page {sec_match.page_number}, Section: {sec_match.section_name or 'General'}):\n"
                                f"{sec_quote[:450]}"
                            )
                        else:
                            evidence_to_audit = top_quote[:1500]

                        async with semaphore:
                            verified_evidence = await self.verifier.verify_requirement_support_async(
                                requirement=req,
                                candidate_id=candidate.candidate_id,
                                evidence_text=evidence_to_audit,
                                provenance=provenance,
                                passage_id=top_match.passage_id,
                            )

                    if verified_evidence.status == EvidenceStatus.EXPLICITLY_SUPPORTED:
                        ratio = 1.0
                    elif verified_evidence.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                        ratio = gamma
                    else:
                        ratio = 0.0

                    human_review = False
                    review_reason: Optional[str] = None

                    if req.is_hard_gate and verified_evidence.status != EvidenceStatus.EXPLICITLY_SUPPORTED:
                        human_review = True
                        review_reason = (
                            f"Human Review Required: Mandatory requirement '{req.name}' "
                            f"not evidenced in submitted resume."
                        )
                    elif verified_evidence.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                        human_review = True
                        review_reason = f"Uncertain Evidence: Evidence for '{req.name}' is partial or ambiguous."

                    points_awarded = round(norm_weight * ratio, 4)

                    evaluations.append(
                        CriterionEvaluation(
                            requirement_id=req.requirement_id,
                            requirement_name=req.name,
                            category=req.category,
                            status=verified_evidence.status,
                            is_hard_gate=req.is_hard_gate,
                            evidence=verified_evidence,
                            achievement_ratio=ratio,
                            points_awarded=points_awarded,
                            max_points=norm_weight if norm_weight > 0 else 1.0,
                            within_category_weight=norm_weight,
                            human_review_required=human_review,
                            review_reason=review_reason,
                        )
                    )
                candidate_evaluations[candidate.candidate_id] = evaluations
            except Exception as exc:
                logger.error(
                    "Async isolated candidate evaluation failure for %s (%s): %s",
                    candidate.candidate_id,
                    candidate.filename,
                    str(exc)[:200],
                )
                total_failed += 1
                validation_errors.append(
                    PipelineErrorRecord(
                        candidate_id=candidate.candidate_id,
                        filename=candidate.filename,
                        stage=PipelineStage.EVALUATING,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:1000],
                        is_fatal_for_candidate=True,
                    )
                )

        if on_stage_complete:
            await on_stage_complete(3, "04", "Source provenance and contextual support verified.")

        # =========================================================================
        # Stage 5: Calculating Scores & Preparing Results
        # =========================================================================
        if on_stage_start:
            await on_stage_start(4, "05", "Calculating deterministic rubric scorecards and ranking candidate results...")

        scorecards: Dict[CandidateId, CandidateScorecard] = {}
        for candidate, _ in candidates_data:
            if candidate.candidate_id in candidate_evaluations:
                evals = candidate_evaluations[candidate.candidate_id]
                card = calculate_candidate_scorecard(
                    candidate_id=candidate.candidate_id,
                    candidate_name=candidate.candidate_name,
                    filename=candidate.filename,
                    job_spec=job_spec,
                    evaluations=evals,
                )
                scorecards[candidate.candidate_id] = card

        total_successful = len(scorecards)
        ranked = rank_candidates(list(scorecards.values()))

        batch_result = BatchScreeningResult(
            job_title=job_spec.job_title,
            rubric_version=job_spec.rubric.rubric_version,
            total_submitted=len(candidates_data),
            total_successful=total_successful,
            total_failed=total_failed,
            ranked_candidates=ranked,
            scorecards=scorecards,
            validation_errors=validation_errors,
        )

        if on_stage_complete:
            await on_stage_complete(4, "05", "Deterministic scorecards calculated and candidate results prepared.")

        return batch_result

    async def evaluate_batch_async(
        self,
        candidates_data: List[Tuple[CandidateProfile, str]],
        job_spec: JobSpecification,
    ) -> BatchScreeningResult:
        """
        Asynchronously evaluates a batch of candidates.
        Preserves backward compatibility by delegating to evaluate_staged_batch_async.
        """
        return await self.evaluate_staged_batch_async(candidates_data, job_spec)
