"""
VectorHire FastAPI REST Endpoints.
Defines public endpoints:
- GET /health: Readiness and operational limits.
- POST /analyze-job: Extraction of structured JobSpecification from raw text.
- POST /analyze-resumes: Ingestion and multi-stage evaluation of a batch of resumes.
- POST /generate-questions: Evidence-grounded interview question generation.
"""

import json
import logging
import re
from uuid import uuid4
# Ensure compatibility between Starlette 1.x Router and FastAPI 0.115 APIRouter
try:
    import starlette.routing
    _orig_router_init = starlette.routing.Router.__init__

    def _compat_router_init(self, *args, on_startup=None, on_shutdown=None, **kwargs):
        _orig_router_init(self, *args, **kwargs)
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

    starlette.routing.Router.__init__ = _compat_router_init
except Exception:
    pass

from typing import List, Optional, Tuple
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.agents.job_analyzer import JobAnalysisAgent
from app.agents.question_generator import QuestionGeneratorAgent
from app.core.config import get_settings
from app.core.exceptions import (
    DocumentProcessingError,
    ProviderAPIError,
    RubricValidationError,
    VectorHireError,
)
from app.schemas.api import (
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    HealthResponse,
    JobAnalysisRequest,
    JobAnalysisResponse,
    JobTextExtractionResponse,
)
from app.schemas.candidate import CandidateProfile
from app.schemas.common import PipelineStage
from app.schemas.evaluation import BatchScreeningResult
from app.schemas.job import JobSpecification
from app.schemas.pipeline import PipelineErrorRecord
from app.services.document_processing import extract_candidate_profile, validate_pdf_bytes
from app.services.evaluation_pipeline import EvaluationPipeline
from app.services.job_extraction import extract_job_text_from_bytes
from app.services.resume_validation import ResumeValidationService, ResumeValidationStatus

logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
@router.get("/api/health", response_model=HealthResponse, tags=["Health"], include_in_schema=False)
async def get_health() -> HealthResponse:
    """Returns application readiness status, active models, and operational limits."""
    provider = settings.LLM_PROVIDER.strip().lower()
    if provider == "gemini":
        active_model = settings.GEMINI_MODEL
        fallback_model = settings.GEMINI_FALLBACK_MODEL
        cross_fallback = f"groq:{settings.GROQ_MODEL}"
    else:
        active_model = settings.GROQ_MODEL
        fallback_model = settings.GROQ_FALLBACK_MODEL
        cross_fallback = None

    return HealthResponse(
        status="healthy",
        version="1.1.0",
        llm_provider=settings.LLM_PROVIDER,
        active_llm_model=active_model,
        fallback_llm_model=fallback_model,
        cross_provider_fallback=cross_fallback,
        embedding_model=settings.EMBEDDING_MODEL,
        max_batch_size=settings.MAX_BATCH_SIZE,
        max_file_size_mb=settings.MAX_FILE_SIZE_MB,
        max_concurrent_requests=settings.MAX_CONCURRENT_REQUESTS,
        gamma_uncertainty_discount=settings.UNCERTAINTY_DISCOUNT_GAMMA,
    )


@router.post("/extract-job-text", response_model=JobTextExtractionResponse, tags=["Job Analysis"])
@router.post("/api/extract-job-text", response_model=JobTextExtractionResponse, tags=["Job Analysis"], include_in_schema=False)
async def extract_job_text(
    file: UploadFile = File(..., description="Job description document (PDF, DOCX, or TXT)"),
) -> JobTextExtractionResponse:
    """
    Extracts, sanitizes, and returns plain text from an uploaded Job Description document.
    Supports PDF (.pdf), Word (.docx), and plain text (.txt) files.
    """
    settings = get_settings()
    filename = file.filename or "job_description.txt"

    try:
        content = await file.read()
    finally:
        await file.close()

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB.",
        )

    try:
        cleaned_text, detected_format = extract_job_text_from_bytes(content, filename)
        return JobTextExtractionResponse(
            text=cleaned_text,
            filename=filename,
            format=detected_format,
            character_count=len(cleaned_text),
        )
    except DocumentProcessingError as doc_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(doc_err),
        )
    except Exception as exc:
        logger.error("Unexpected error extracting job text from %s: %s", filename, str(exc)[:200])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process job document '{filename}': {str(exc)}",
        )


@router.post("/analyze-job", response_model=JobAnalysisResponse, tags=["Job Analysis"])
@router.post("/api/analyze-job", response_model=JobAnalysisResponse, tags=["Job Analysis"], include_in_schema=False)
async def analyze_job(request: JobAnalysisRequest) -> JobAnalysisResponse:
    """
    Analyzes unstructured Job Description text into a validated, recruiter-editable JobSpecification.
    Categorizes criteria, extracts normalized terms and aliases, and assigns initial rubric weights.
    """
    clean_text = request.job_description_text.strip()
    if len(clean_text) < 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description text must contain at least 20 non-whitespace characters.",
        )

    agent = JobAnalysisAgent()
    try:
        spec = await agent.analyze_job_description_async(clean_text, request.job_title_hint)
        return JobAnalysisResponse(
            job_spec=spec,
            analysis_summary=f"Extracted {len(spec.requirements)} criteria for '{spec.job_title}'.",
        )
    except ProviderAPIError as p_err:
        logger.error("Provider error during job analysis: %s", str(p_err)[:200])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upstream AI provider is temporarily unavailable. Please retry shortly.",
        )
    except Exception as exc:
        logger.error("Error during job analysis: %s", str(exc)[:200])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to analyze job description: {type(exc).__name__}",
        )


@router.post("/analyze-resumes", response_model=BatchScreeningResult, tags=["Screening"])
@router.post("/api/analyze-resumes", response_model=BatchScreeningResult, tags=["Screening"], include_in_schema=False)
async def analyze_resumes(
    resumes: List[UploadFile] = File(..., description="Batch of PDF resume files"),
    job_spec: str = Form(..., description="JSON string of the validated JobSpecification"),
) -> BatchScreeningResult:
    """
    Ingests and screens a batch of PDF resumes against the frozen JobSpecification.
    Coordinates document processing, hybrid retrieval, two-stage evidence verification,
    and deterministic rubric scoring.
    """
    settings = get_settings()

    # 1. Validate batch size
    if not resumes or len(resumes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one resume file must be uploaded.",
        )

    if len(resumes) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batch size of {len(resumes)} resumes exceeds the configured maximum limit "
                f"of {settings.MAX_BATCH_SIZE} resumes."
            ),
        )

    # 2. Parse and validate JobSpecification
    try:
        spec_data = json.loads(job_spec)
        validated_spec = JobSpecification.model_validate(spec_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job_spec format: {str(exc)}",
        )

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    valid_candidates_data: List[Tuple[CandidateProfile, str]] = []
    ingestion_failures: List[PipelineErrorRecord] = []

    # 3. Ingest resumes with individual candidate failure isolation and guaranteed file cleanup
    for idx, upload_file in enumerate(resumes, start=1):
        filename = upload_file.filename or f"resume_{idx}.pdf"
        # Generate safe candidate ID
        stem = re.sub(r"[^a-zA-Z0-9_\-]", "", filename.split(".")[0])[:12] or f"c{idx}"
        candidate_id = f"cand_{idx:02d}_{stem}_{uuid4().hex[:4]}"

        try:
            # Read file bytes
            content = await upload_file.read()

            # Enforce size limit
            if len(content) == 0:
                ingestion_failures.append(
                    PipelineErrorRecord(
                        candidate_id=candidate_id,
                        filename=filename,
                        stage=PipelineStage.INGESTING,
                        error_type="EmptyFileError",
                        error_message="Uploaded document is empty (0 bytes).",
                    )
                )
                continue

            if len(content) > max_bytes:
                ingestion_failures.append(
                    PipelineErrorRecord(
                        candidate_id=candidate_id,
                        filename=filename,
                        stage=PipelineStage.INGESTING,
                        error_type="FileTooLargeError",
                        error_message=(
                            f"File size ({len(content) / (1024 * 1024):.1f}MB) exceeds "
                            f"limit of {settings.MAX_FILE_SIZE_MB}MB."
                        ),
                    )
                )
                continue

            # Phase 4.1: Enforce Resume Validation Gate before hybrid retrieval or candidate scoring
            validator = ResumeValidationService()
            validation_result = await validator.validate_document_async(content, filename)

            if validation_result.status == ResumeValidationStatus.VALID_RESUME:
                # Plausible resume: extract candidate profile and segment into passages
                profile, raw_text = extract_candidate_profile(content, filename, candidate_id)
                valid_candidates_data.append((profile, raw_text))
            elif validation_result.status == ResumeValidationStatus.NOT_RESUME:
                logger.info(
                    "Validation Gate rejected %s as %s: %s",
                    filename,
                    validation_result.detected_document_type,
                    validation_result.reason_codes,
                )
                ingestion_failures.append(
                    PipelineErrorRecord(
                        candidate_id=candidate_id,
                        filename=filename,
                        stage=PipelineStage.INGESTING,
                        error_type="NonResumeDocumentError",
                        error_message=(
                            f"Document '{filename}' was rejected by the resume validation gate: "
                            f"{validation_result.failure_message or 'Document does not exhibit resume or CV structure.'}"
                        ),
                    )
                )
            elif validation_result.status == ResumeValidationStatus.UNCERTAIN:
                logger.info(
                    "Validation Gate marked %s as uncertain: %s",
                    filename,
                    validation_result.reason_codes,
                )
                ingestion_failures.append(
                    PipelineErrorRecord(
                        candidate_id=candidate_id,
                        filename=filename,
                        stage=PipelineStage.INGESTING,
                        error_type="AmbiguousDocumentError",
                        error_message=(
                            f"Document '{filename}' could not be verified as a resume: "
                            f"{validation_result.failure_message or 'Please provide a clear resume or replace this file.'}"
                        ),
                    )
                )
            else:  # UNREADABLE
                logger.info(
                    "Validation Gate marked %s as unreadable: %s",
                    filename,
                    validation_result.reason_codes,
                )
                ingestion_failures.append(
                    PipelineErrorRecord(
                        candidate_id=candidate_id,
                        filename=filename,
                        stage=PipelineStage.INGESTING,
                        error_type="UnreadableDocumentError",
                        error_message=(
                            f"Document '{filename}' could not be read: "
                            f"{validation_result.failure_message or 'Encrypted, corrupted, or image-only PDF lacking extractable text.'}"
                        ),
                    )
                )

        except DocumentProcessingError as doc_err:
            logger.warning("Isolated document processing error for %s: %s", filename, str(doc_err)[:150])
            ingestion_failures.append(
                PipelineErrorRecord(
                    candidate_id=candidate_id,
                    filename=filename,
                    stage=PipelineStage.INGESTING,
                    error_type="DocumentProcessingError",
                    error_message=str(doc_err),
                )
            )
        except Exception as exc:
            logger.error("Unexpected isolated ingestion error for %s: %s", filename, str(exc)[:150])
            ingestion_failures.append(
                PipelineErrorRecord(
                    candidate_id=candidate_id,
                    filename=filename,
                    stage=PipelineStage.INGESTING,
                    error_type=type(exc).__name__,
                    error_message=f"Failed to ingest document: {type(exc).__name__}",
                )
            )
        finally:
            # Guaranteed file closure
            await upload_file.close()

    # 4. Execute evaluation pipeline on healthy candidates
    pipeline = EvaluationPipeline()

    if valid_candidates_data:
        screening_result = await pipeline.evaluate_batch_async(valid_candidates_data, validated_spec)
    else:
        # All candidates encountered ingestion errors
        screening_result = BatchScreeningResult(
            job_title=validated_spec.job_title,
            rubric_version=validated_spec.rubric.rubric_version,
            total_submitted=len(resumes),
            total_successful=0,
            total_failed=len(ingestion_failures),
            ranked_candidates=[],
            scorecards={},
            validation_errors=ingestion_failures,
        )

    # 5. Merge ingestion failures and evaluation failures
    total_submitted_overall = len(resumes)
    all_validation_errors = list(ingestion_failures) + list(screening_result.validation_errors)
    total_failed_overall = len(all_validation_errors)

    if screening_result.total_successful == 0:
        error_details = "; ".join([
            f"{err.filename}: {err.error_message}"
            for err in all_validation_errors
        ]) or "All uploaded candidate resumes failed validation or evaluation."
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Candidate evaluation failed for all submitted resumes. Errors: {error_details}",
        )

    return BatchScreeningResult(
        job_title=screening_result.job_title,
        rubric_version=screening_result.rubric_version,
        total_submitted=total_submitted_overall,
        total_successful=screening_result.total_successful,
        total_failed=total_failed_overall,
        ranked_candidates=screening_result.ranked_candidates,
        scorecards=screening_result.scorecards,
        validation_errors=all_validation_errors,
    )


@router.post("/generate-questions", response_model=GenerateQuestionsResponse, tags=["Interview Questions"])
@router.post("/api/generate-questions", response_model=GenerateQuestionsResponse, tags=["Interview Questions"], include_in_schema=False)
async def generate_questions(request: GenerateQuestionsRequest) -> GenerateQuestionsResponse:
    """
    Generates targeted, evidence-grounded interview questions for an evaluated candidate.
    Grounded strictly in verified claims or identified evidence gaps without asserting candidate deficiencies.
    """
    if request.max_questions < 1 or request.max_questions > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_questions must be between 1 and 10.",
        )

    agent = QuestionGeneratorAgent()
    try:
        questions = await agent.generate_interview_questions_async(
            candidate_id=request.candidate_id,
            candidate_name=request.candidate_name,
            job_spec=request.job_spec,
            scorecard=request.scorecard,
            max_questions=request.max_questions,
        )

        return GenerateQuestionsResponse(
            candidate_id=request.candidate_id,
            candidate_name=request.candidate_name,
            total_questions=len(questions),
            questions=questions,
        )
    except ProviderAPIError as p_err:
        logger.error("Provider error generating interview questions: %s", str(p_err)[:200])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upstream AI provider is temporarily unavailable. Please retry shortly.",
        )
    except Exception as exc:
        logger.error("Error generating interview questions: %s", str(exc)[:200])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate questions: {type(exc).__name__}",
        )
