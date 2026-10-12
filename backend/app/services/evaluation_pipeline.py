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
from typing import Dict, List, Optional, Tuple

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

    async def evaluate_batch_async(
        self,
        candidates_data: List[Tuple[CandidateProfile, str]],
        job_spec: JobSpecification,
    ) -> BatchScreeningResult:
        """
        Asynchronously evaluates a batch of candidates with Semaphore concurrency limit.
        Isolates failures so a single candidate error does not abort the batch.
        """
        if len(candidates_data) > self.settings.MAX_BATCH_SIZE:
            raise VectorHireError(
                f"Batch size {len(candidates_data)} exceeds maximum allowed limit "
                f"of {self.settings.MAX_BATCH_SIZE} resumes."
            )

        semaphore = asyncio.Semaphore(self.settings.MAX_CONCURRENT_REQUESTS)
        scorecards: Dict[CandidateId, CandidateScorecard] = {}
        validation_errors: List[PipelineErrorRecord] = []
        lock = asyncio.Lock()
        total_failed = 0

        async def _eval_one(candidate: CandidateProfile, raw_text: str):
            nonlocal total_failed
            try:
                card = await self.evaluate_candidate_async(
                    candidate=candidate,
                    job_spec=job_spec,
                    raw_document_text=raw_text,
                    semaphore=semaphore,
                )
                async with lock:
                    scorecards[candidate.candidate_id] = card
            except Exception as exc:
                logger.error(
                    "Async isolated candidate evaluation failure for %s (%s): %s",
                    candidate.candidate_id,
                    candidate.filename,
                    str(exc)[:200],
                )
                async with lock:
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

        tasks = [_eval_one(cand, raw_text) for cand, raw_text in candidates_data]
        await asyncio.gather(*tasks)

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
