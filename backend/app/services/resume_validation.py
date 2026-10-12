"""
VectorHire Resume Document Validation Gate Service.
Phase 4.1: Pre-screening gate verifying that each uploaded file is plausibly a resume/CV
before hybrid retrieval or rubric scoring.

Outcomes:
- valid_resume: Sufficient evidence that document is plausibly a resume or CV.
- not_resume: Strong evidence that document is another document type (research paper, invoice, transcript, essay).
- uncertain: Insufficient or ambiguous evidence for confident classification; requests human review.
- unreadable: Encrypted, corrupt, or image-only PDF lacking extractable text.

Guarantees:
- Never rejects solely because a resume lacks a single conventional section (e.g. fresher resumes without employment history).
- Never exposes raw document text in error responses or logs.
- Employs cost-conscious hybrid strategy: fast deterministic heuristics with secondary LLM fallback only on ambiguous edge cases.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.exceptions import DocumentProcessingError
from app.providers.groq_provider import GroqProvider
from app.services.document_processing import extract_pages_text, validate_pdf_bytes

logger = logging.getLogger(__name__)


class ResumeValidationStatus(str, Enum):
    """Controlled 4-state document validation taxonomy."""
    VALID_RESUME = "valid_resume"
    NOT_RESUME = "not_resume"
    UNCERTAIN = "uncertain"
    UNREADABLE = "unreadable"


class ConfidenceBand(str, Enum):
    """Qualitative classification confidence bands."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResumeValidationResult(BaseModel):
    """
    Structured outcome of the resume document validation gate.
    Maintains clean diagnostic reason codes and metadata without leaking raw candidate text.
    """
    status: ResumeValidationStatus = Field(..., description="Validation gate outcome")
    confidence_band: ConfidenceBand = Field(..., description="Qualitative confidence band")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Heuristic agreement index (uncalibrated score indicator)"
    )
    detected_document_type: str = Field(
        default="unknown",
        description="Identified document category (resume, research_paper, invoice, transcript, essay, etc.)"
    )
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Concise diagnostic classification codes"
    )
    diagnostic_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Non-sensitive structural metrics (counts, character length, page count)"
    )
    failure_message: Optional[str] = Field(
        default=None,
        description="Actionable explanation if document is not approved as valid_resume"
    )


# ==============================================================================
# DETERMINISTIC REGEX PATTERNS & SIGNAL DEFINITIONS
# ==============================================================================

# Resume Structural Dimensions
RE_EDUCATION = re.compile(
    r"\b(education|academic\s+background|bachelor|master|ph\.?d|b\.?tech|b\.?e|b\.?s|m\.?tech|"
    r"m\.?s|m\.?b\.?a|diploma|degree|university|college|gpa|cgpa)\b",
    re.IGNORECASE
)

RE_EXPERIENCE = re.compile(
    r"\b((?:work\s+|professional\s+|clinical\s+|relevant\s+|industry\s+|job\s+)?experience|"
    r"employment\s+history|work\s+history|employment|internship|responsibilities|job\s+history)\b",
    re.IGNORECASE
)

RE_ROLE_TITLES = re.compile(
    r"\b(engineer|developer|architect|specialist|analyst|associate|lead|director|"
    r"manager|consultant|nurse|physician|administrator|intern|assistant|officer|"
    r"scientist|designer|coordinator|executive|accountant|auditor|technician|representative)\b",
    re.IGNORECASE
)

RE_SKILLS = re.compile(
    r"\b(skills|technical\s+skills|core\s+competencies|technologies|proficiencies|"
    r"programming\s+languages|tools\s+and\s+technologies|certifications?|licenses?)\b",
    re.IGNORECASE
)

RE_PROJECTS = re.compile(
    r"\b(projects|academic\s+projects|personal\s+projects|relevant\s+projects|portfolio|"
    r"key\s+projects|project\s+experience)\b",
    re.IGNORECASE
)

RE_CONTACT = re.compile(
    r"(?:[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|"
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|"
    r"linkedin\.com/in/|github\.com/)",
    re.IGNORECASE
)

RE_DATE_RANGES = re.compile(
    r"\b(?:20\d\d|19\d\d)\s*(?:-|–|to)\s*(?:20\d\d|present|current)\b",
    re.IGNORECASE
)

# Non-Resume Patterns
RE_RESEARCH_PAPER = re.compile(
    r"\b(abstract|methodology|proposed\s+method|experimental\s+results|related\s+work|"
    r"conclusion\s+and\s+future\s+work|references|bibliography|doi:|arxiv:|ieee\s+transactions|"
    r"proceedings\s+of|volume\s+\d+,\s+issue|citation)\b",
    re.IGNORECASE
)

RE_TRANSCRIPT = re.compile(
    r"\b(transcript\s+of\s+records|official\s+transcript|academic\s+transcript|grade\s+report|"
    r"semester\s+\d+|term\s+\d+|course\s+code|subject\s+code|credits?\s+earned|credits?\s+registered|"
    r"cumulative\s+gpa|cgpa|sgpa|registrar|dean\s+of\s+academic|controller\s+of\s+examinations)\b",
    re.IGNORECASE
)

RE_INVOICE = re.compile(
    r"\b(invoice|tax\s+invoice|bill\s+to|ship\s+to|invoice\s+(?:number|no|#)|remit\s+to|"
    r"subtotal|amount\s+due|total\s+due|balance\s+due|payment\s+due|tax\s+rate|vat|gst|"
    r"unit\s+price|line\s+total|payment\s+terms)\b",
    re.IGNORECASE
)

RE_ESSAY = re.compile(
    r"\b(in\s+conclusion|furthermore|moreover|on\s+the\s+other\s+hand|the\s+thesis\s+of\s+this|"
    r"this\s+essay\s+will|firstly|secondly|in\s+summary,\s+the\s+argument)\b",
    re.IGNORECASE
)


class ResumeValidationService:
    """
    Cost-conscious hybrid document validation service.
    Verifies that uploaded documents exhibit the structural properties of a resume/CV
    before allowing candidates into retrieval and scoring.
    """

    def __init__(self, provider: Optional[GroqProvider] = None):
        self.provider = provider or GroqProvider()

    def _evaluate_deterministic_signals(
        self, full_text: str, page_count: int
    ) -> ResumeValidationResult:
        """
        Extracts structural indicators from extracted text and computes a rule-based
        classification into valid_resume, not_resume, or uncertain.
        """
        text_lower = full_text.lower()
        char_count = len(full_text)
        alpha_count = len(re.findall(r"[a-zA-Z0-9]", full_text))

        # Check 1: Insufficient text volume (e.g. scanned image-only PDF)
        if alpha_count < 60:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=0.95,
                detected_document_type="image_only_or_scanned_pdf",
                reason_codes=["INSUFFICIENT_EXTRACTABLE_TEXT_OCR_REQUIRED"],
                diagnostic_metadata={
                    "char_count": char_count,
                    "alpha_count": alpha_count,
                    "page_count": page_count,
                },
                failure_message=(
                    "Document contains fewer than 60 readable characters. "
                    "Scanned or image-only documents require OCR; please upload a text-based PDF."
                ),
            )

        # Count positive resume dimensions
        has_education = bool(RE_EDUCATION.search(text_lower))
        has_role = bool(RE_ROLE_TITLES.search(text_lower))
        has_exp_section = bool(RE_EXPERIENCE.search(text_lower))
        has_experience = has_exp_section or has_role
        has_skills = bool(RE_SKILLS.search(text_lower))
        has_projects = bool(RE_PROJECTS.search(text_lower))
        has_contact = bool(RE_CONTACT.search(full_text))
        has_dates = bool(RE_DATE_RANGES.search(full_text))

        resume_dimensions = sum([
            has_education,
            has_experience,
            (has_role and has_exp_section),
            has_skills,
            has_projects,
            has_contact,
        ])

        # Count negative / competing document signals
        paper_matches = len(RE_RESEARCH_PAPER.findall(text_lower))
        transcript_matches = len(RE_TRANSCRIPT.findall(text_lower))
        invoice_matches = len(RE_INVOICE.findall(text_lower))
        essay_matches = len(RE_ESSAY.findall(text_lower))

        diag_meta = {
            "char_count": char_count,
            "page_count": page_count,
            "resume_dimensions_count": resume_dimensions,
            "has_education": has_education,
            "has_experience": has_experience,
            "has_skills": has_skills,
            "has_projects": has_projects,
            "has_contact": has_contact,
            "has_dates": has_dates,
            "paper_signal_count": paper_matches,
            "transcript_signal_count": transcript_matches,
            "invoice_signal_count": invoice_matches,
            "essay_signal_count": essay_matches,
        }

        # ----------------------------------------------------------------------
        # Check Negative Signals: Strongly Non-Resume Documents
        # ----------------------------------------------------------------------

        # Category: Research Paper (e.g. abstract + methodology/references + citations)
        if paper_matches >= 3 and (
            "abstract" in text_lower or "references" in text_lower or "doi:" in text_lower
        ) and not has_skills:
            return ResumeValidationResult(
                status=ResumeValidationStatus.NOT_RESUME,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=0.90,
                detected_document_type="research_paper",
                reason_codes=["ACADEMIC_RESEARCH_PAPER_PATTERN", "ABSTRACT_AND_BIBLIOGRAPHY_DETECTED"],
                diagnostic_metadata=diag_meta,
                failure_message=(
                    "Uploaded document exhibits academic research paper formatting (abstract/citations) "
                    "rather than a candidate resume."
                ),
            )

        # Category: Academic Transcript / Marksheet (e.g. course codes, semester grades, registrar)
        if transcript_matches >= 3 and not (has_experience and has_skills):
            return ResumeValidationResult(
                status=ResumeValidationStatus.NOT_RESUME,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=0.90,
                detected_document_type="academic_transcript",
                reason_codes=["TRANSCRIPT_GRADE_REPORT_PATTERN", "COURSE_CODE_TABLES_DETECTED"],
                diagnostic_metadata=diag_meta,
                failure_message=(
                    "Uploaded document appears to be an academic transcript or marksheet, "
                    "not a candidate resume."
                ),
            )

        # Category: Invoice / Financial Bill
        if invoice_matches >= 3 and not (has_education or has_skills):
            return ResumeValidationResult(
                status=ResumeValidationStatus.NOT_RESUME,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=0.95,
                detected_document_type="invoice_or_financial_bill",
                reason_codes=["INVOICE_BILLING_PATTERN", "FINANCIAL_AMOUNTS_DETECTED"],
                diagnostic_metadata=diag_meta,
                failure_message=(
                    "Uploaded document exhibits invoice or billing record formatting, "
                    "not a candidate resume."
                ),
            )

        # Category: Essay / Generic Narrative Prose
        if essay_matches >= 2 and resume_dimensions <= 1 and not has_dates:
            return ResumeValidationResult(
                status=ResumeValidationStatus.NOT_RESUME,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=0.85,
                detected_document_type="essay_or_generic_article",
                reason_codes=["PROSE_ESSAY_STRUCTURE_DETECTED", "ZERO_CHRONOLOGY_OR_SKILLS"],
                diagnostic_metadata=diag_meta,
                failure_message=(
                    "Uploaded document appears to be a generic essay or article without "
                    "resume structure."
                ),
            )

        # Check 2: Very short or trivial text (e.g. 60-180 characters like a one-sentence note) lacking resume structure
        if alpha_count < 180 and not RE_CONTACT.search(full_text) and resume_dimensions < 2:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNCERTAIN,
                confidence_band=ConfidenceBand.LOW,
                confidence_score=0.30,
                detected_document_type="ambiguous_short_document",
                reason_codes=["VERY_LOW_TEXT_VOLUME", "AMBIGUOUS_STRUCTURE"],
                diagnostic_metadata={"char_count": char_count, "page_count": page_count},
                failure_message=(
                    "Document contains insufficient text to establish a resume structure. "
                    "Please replace with a complete resume or CV."
                ),
            )

        # ----------------------------------------------------------------------
        # Check Positive Signals: Resumes (Experienced or Fresher)
        # ----------------------------------------------------------------------

        # Case A: Experienced Professional Resume (3+ dimensions including experience or dates)
        if resume_dimensions >= 3 or (resume_dimensions >= 2 and (has_experience or has_dates)):
            reason_codes = ["RESUME_STRUCTURAL_SIGNALS_VERIFIED"]
            if has_experience:
                reason_codes.append("EXPERIENCE_SECTION_FOUND")
            if has_education:
                reason_codes.append("EDUCATION_SECTION_FOUND")
            if has_skills:
                reason_codes.append("SKILLS_SECTION_FOUND")
            if has_projects:
                reason_codes.append("PROJECTS_SECTION_FOUND")

            return ResumeValidationResult(
                status=ResumeValidationStatus.VALID_RESUME,
                confidence_band=ConfidenceBand.HIGH if resume_dimensions >= 3 else ConfidenceBand.MEDIUM,
                confidence_score=min(0.95, 0.50 + (resume_dimensions * 0.10)),
                detected_document_type="resume",
                reason_codes=reason_codes,
                diagnostic_metadata=diag_meta,
                failure_message=None,
            )

        # Case B: Fresher / Student Resume (education + projects + skills, zero work experience)
        if has_education and (has_projects or has_skills):
            return ResumeValidationResult(
                status=ResumeValidationStatus.VALID_RESUME,
                confidence_band=ConfidenceBand.HIGH if (has_projects and has_skills) else ConfidenceBand.MEDIUM,
                confidence_score=0.80,
                detected_document_type="fresher_resume",
                reason_codes=[
                    "FRESHER_RESUME_SIGNALS_VERIFIED",
                    "EDUCATION_SECTION_FOUND",
                    "PROJECTS_OR_SKILLS_FOUND",
                ],
                diagnostic_metadata=diag_meta,
                failure_message=None,
            )

        # ----------------------------------------------------------------------
        # Borderline / Ambiguous Document
        # ----------------------------------------------------------------------
        return ResumeValidationResult(
            status=ResumeValidationStatus.UNCERTAIN,
            confidence_band=ConfidenceBand.LOW,
            confidence_score=0.45,
            detected_document_type="ambiguous_document",
            reason_codes=["INSUFFICIENT_STRUCTURAL_EVIDENCE", "BORDERLINE_RESUME_SIGNALS"],
            diagnostic_metadata=diag_meta,
            failure_message=(
                "Document could not be confidently classified as a resume. "
                "Please replace with a standard CV or request manual recruiter review."
            ),
        )

    def _call_secondary_llm_classifier(
        self, full_text: str, page_count: int
    ) -> Optional[ResumeValidationResult]:
        """
        Secondary LLM classifier invoked ONLY when deterministic heuristics are uncertain.
        Uses structured JSON mode with strict boundaries.
        """
        # Truncate text excerpt to first 2500 characters to keep cost low and latency fast
        excerpt = full_text[:2500]

        prompt = f"""You are a document classifier for VectorHire recruitment platform.
Your ONLY task is to determine whether the following document excerpt is plausibly a candidate resume or curriculum vitae (CV).

DOCUMENT EXCERPT:
<document_excerpt>
{excerpt}
</document_excerpt>

Consider:
- Experienced resumes have work history, skills, and education.
- Fresher resumes may have NO professional employment, but feature education, projects, and skills.
- Non-resumes include: research papers, transcripts/marksheets, invoices/receipts, essays, or generic letters.

Respond in JSON mode with:
{{
  "is_resume": true | false | null,
  "detected_document_type": "resume" | "research_paper" | "academic_transcript" | "invoice" | "essay" | "other",
  "confidence_band": "high" | "medium" | "low",
  "reason": "Brief non-sensitive explanation."
}}"""

        messages = [
            {"role": "system", "content": "You are an impartial document format classifier. Output valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            res_json = self.provider.generate_json(messages)
            is_resume = res_json.get("is_resume")
            doc_type = str(res_json.get("detected_document_type", "unknown")).lower()
            band_str = str(res_json.get("confidence_band", "medium")).lower()

            band = ConfidenceBand.MEDIUM
            if band_str == "high":
                band = ConfidenceBand.HIGH
            elif band_str == "low":
                band = ConfidenceBand.LOW

            if is_resume is True:
                return ResumeValidationResult(
                    status=ResumeValidationStatus.VALID_RESUME,
                    confidence_band=band,
                    confidence_score=0.85 if band == ConfidenceBand.HIGH else 0.70,
                    detected_document_type=doc_type or "resume",
                    reason_codes=["LLM_SECONDARY_CLASSIFIER_CONFIRMED_RESUME"],
                    diagnostic_metadata={"char_count": len(full_text), "page_count": page_count},
                    failure_message=None,
                )
            elif is_resume is False:
                return ResumeValidationResult(
                    status=ResumeValidationStatus.NOT_RESUME,
                    confidence_band=band,
                    confidence_score=0.85 if band == ConfidenceBand.HIGH else 0.70,
                    detected_document_type=doc_type or "not_resume",
                    reason_codes=["LLM_SECONDARY_CLASSIFIER_IDENTIFIED_NON_RESUME"],
                    diagnostic_metadata={"char_count": len(full_text), "page_count": page_count},
                    failure_message=f"Document was classified as a {doc_type}, not a candidate resume.",
                )
        except Exception as exc:
            logger.warning("Secondary LLM document classifier failed: %s", str(exc)[:150])

        return None

    def validate_document(
        self,
        file_bytes: bytes,
        filename: str,
        use_llm_fallback: bool = True,
    ) -> ResumeValidationResult:
        """
        Synchronously validates whether file_bytes represent a plausible candidate resume.
        """
        # Step 1: Physical stream validation
        if not file_bytes or len(file_bytes) == 0:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="empty_file",
                reason_codes=["EMPTY_DOCUMENT_STREAM"],
                diagnostic_metadata={"filename": filename, "byte_size": 0},
                failure_message="Uploaded document is empty (0 bytes).",
            )

        # Step 2: PDF signature validation
        try:
            validate_pdf_bytes(file_bytes)
        except DocumentProcessingError as doc_err:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="invalid_format",
                reason_codes=["INVALID_PDF_MAGIC_BYTES"],
                diagnostic_metadata={"filename": filename, "byte_size": len(file_bytes)},
                failure_message=str(doc_err),
            )

        # Step 3: Text extraction
        try:
            pages_data = extract_pages_text(file_bytes)
            full_text = "\n\n".join(text for _, text in pages_data).strip()
            page_count = len(pages_data)
        except DocumentProcessingError as proc_err:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="corrupted_or_encrypted_pdf",
                reason_codes=["PDF_TEXT_EXTRACTION_FAILURE"],
                diagnostic_metadata={"filename": filename},
                failure_message=str(proc_err),
            )
        except Exception as exc:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="unreadable_pdf",
                reason_codes=["UNEXPECTED_READ_FAILURE"],
                diagnostic_metadata={"filename": filename},
                failure_message=f"Failed to read PDF document: {type(exc).__name__}",
            )

        # Step 4: Deterministic heuristic analysis
        result = self._evaluate_deterministic_signals(full_text, page_count)

        # Step 5: Secondary LLM classifier on ambiguous/uncertain results only
        if result.status == ResumeValidationStatus.UNCERTAIN and use_llm_fallback:
            if self.provider.api_key:
                llm_result = self._call_secondary_llm_classifier(full_text, page_count)
                if llm_result:
                    return llm_result

        return result

    async def validate_document_async(
        self,
        file_bytes: bytes,
        filename: str,
        use_llm_fallback: bool = True,
    ) -> ResumeValidationResult:
        """
        Asynchronously validates whether file_bytes represent a plausible candidate resume.
        """
        # Step 1: Physical stream validation
        if not file_bytes or len(file_bytes) == 0:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="empty_file",
                reason_codes=["EMPTY_DOCUMENT_STREAM"],
                diagnostic_metadata={"filename": filename, "byte_size": 0},
                failure_message="Uploaded document is empty (0 bytes).",
            )

        # Step 2: PDF signature validation
        try:
            validate_pdf_bytes(file_bytes)
        except DocumentProcessingError as doc_err:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="invalid_format",
                reason_codes=["INVALID_PDF_MAGIC_BYTES"],
                diagnostic_metadata={"filename": filename, "byte_size": len(file_bytes)},
                failure_message=str(doc_err),
            )

        # Step 3: Text extraction
        try:
            pages_data = extract_pages_text(file_bytes)
            full_text = "\n\n".join(text for _, text in pages_data).strip()
            page_count = len(pages_data)
        except DocumentProcessingError as proc_err:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="corrupted_or_encrypted_pdf",
                reason_codes=["PDF_TEXT_EXTRACTION_FAILURE"],
                diagnostic_metadata={"filename": filename},
                failure_message=str(proc_err),
            )
        except Exception as exc:
            return ResumeValidationResult(
                status=ResumeValidationStatus.UNREADABLE,
                confidence_band=ConfidenceBand.HIGH,
                confidence_score=1.0,
                detected_document_type="unreadable_pdf",
                reason_codes=["UNEXPECTED_READ_FAILURE"],
                diagnostic_metadata={"filename": filename},
                failure_message=f"Failed to read PDF document: {type(exc).__name__}",
            )

        # Step 4: Deterministic heuristic analysis
        result = self._evaluate_deterministic_signals(full_text, page_count)

        # Step 5: Secondary LLM classifier on ambiguous/uncertain results only
        if result.status == ResumeValidationStatus.UNCERTAIN and use_llm_fallback:
            if self.provider.api_key:
                # Run sync in thread or use sync LLM call safely
                llm_result = self._call_secondary_llm_classifier(full_text, page_count)
                if llm_result:
                    return llm_result

        return result
