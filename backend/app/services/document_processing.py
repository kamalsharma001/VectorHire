"""
VectorHire In-Memory PDF Document Processing Service.
Handles PDF signature validation, conservative Unicode sanitization,
page-referenced text extraction, and span-exact passage chunking.
"""

import io
import re
from typing import List, Tuple
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import DocumentProcessingError
from app.schemas.candidate import CandidateContact, CandidateProfile, ResumePassage


# PDF magic byte signature
PDF_MAGIC_BYTES = b"%PDF-"

# Standard resume section header regex patterns
SECTION_HEADER_PATTERNS = [
    r"^(?:professional\s+)?summary\b",
    r"^(?:career\s+)?objective\b",
    r"^(?:work\s+|professional\s+|employment\s+)?experience\b",
    r"^(?:employment\s+)?history\b",
    r"^education\b",
    r"^(?:technical\s+|key\s+)?skills\b",
    r"^(?:relevant\s+)?projects\b",
    r"^certifications?(?:\s+and\s+licenses?)?\b",
    r"^licenses?(?:\s+and\s+certifications?)?\b",
    r"^publications\b",
    r"^awards?(?:\s+and\s+honors?)?\b",
    r"^volunteer(?:ing)?\b",
]
SECTION_HEADER_REGEX = re.compile(
    "|".join(f"(?:{p})" for p in SECTION_HEADER_PATTERNS),
    re.IGNORECASE | re.MULTILINE
)


def validate_pdf_bytes(file_bytes: bytes) -> None:
    """
    Validates that input bytes represent a non-empty file with a valid PDF signature.
    Raises DocumentProcessingError on empty streams or invalid signatures.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise DocumentProcessingError("Document stream is empty (0 bytes).")
    
    # Check the first 1024 bytes for standard %PDF- header (handles potential leading BOM/whitespace)
    header = file_bytes[:1024]
    if PDF_MAGIC_BYTES not in header:
        raise DocumentProcessingError(
            "Invalid document format: Missing standard '%PDF-' magic byte signature."
        )


def sanitize_text(raw_text: str) -> str:
    """
    Conservatively normalizes whitespace and Unicode artifacts without inventing content.
    - Replaces common Unicode replacement characters (\ufffd) with a space.
    - Standardizes various non-breaking spaces, soft hyphens, and bullet glyphs.
    - Collapses excessive internal whitespace while preserving line boundaries.
    """
    if not raw_text:
        return ""

    # Replace unicode replacement character (\ufffd) conservatively with a space
    text = raw_text.replace("\ufffd", " ")

    # Strip soft hyphens
    text = text.replace("\u00ad", "")

    # Normalize various typographic bullets to standard bullet token
    for bullet in ("\u2022", "\u25cf", "\u25aa", "\u25b8", "\u2023", "\u2043"):
        text = text.replace(bullet, "- ")

    # Normalize typographical dashes to standard hyphen
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(dash, "-")

    # Normalize non-breaking and special spaces to standard space
    for sp in ("\u00a0", "\u2000", "\u2001", "\u2002", "\u2003", "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u202f", "\u205f", "\u3000"):
        text = text.replace(sp, " ")

    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse consecutive horizontal spaces while keeping newlines
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse excessive consecutive newlines to at most two
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_pages_text(file_bytes: bytes) -> List[Tuple[int, str]]:
    """
    Extracts text page-by-page from raw PDF bytes using pypdf.
    Returns a list of tuples: (page_number_1_indexed, cleaned_page_text).
    Raises DocumentProcessingError on corrupt or encrypted documents.
    """
    validate_pdf_bytes(file_bytes)

    try:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)

        if reader.is_encrypted:
            # Attempt decryption with empty password
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:
                    raise DocumentProcessingError(
                        "Document is encrypted or password-protected and cannot be read."
                    )
            except Exception as e:
                raise DocumentProcessingError(
                    f"Failed to decrypt password-protected PDF: {str(e)}"
                ) from e

        if len(reader.pages) == 0:
            raise DocumentProcessingError("PDF document contains 0 pages.")

        pages_data: List[Tuple[int, str]] = []
        for idx, page in enumerate(reader.pages, start=1):
            try:
                raw_page_text = page.extract_text() or ""
                cleaned = sanitize_text(raw_page_text)
                pages_data.append((idx, cleaned))
            except Exception as page_err:
                # Capture partial page failure gracefully
                pages_data.append((idx, f"[Page {idx} extraction failed: {str(page_err)}]"))

        return pages_data

    except PdfReadError as e:
        raise DocumentProcessingError(f"Malformed or corrupt PDF file: {str(e)}") from e
    except DocumentProcessingError:
        raise
    except Exception as e:
        raise DocumentProcessingError(f"Unexpected document parsing error: {str(e)}") from e


def segment_into_passages(
    pages_data: List[Tuple[int, str]],
    candidate_id: str,
    target_word_count: int = 200,
    overlap_word_count: int = 40
) -> Tuple[str, List[ResumePassage]]:
    """
    Aggregates page texts into a single document string and segments it into coherent
    passages of approximately 150-250 words.
    
    Guarantees:
    - Every passage's character_start and character_end map EXACTLY into aggregated_text.
    - raw_document[character_start:character_end] == passage.text_content.
    - Page numbers accurately reflect where the passage begins.
    """
    # Build continuous text and page boundary index
    # Page index: list of (page_num, start_char, end_char)
    page_bounds: List[Tuple[int, int, int]] = []
    full_text_parts: List[str] = []
    current_offset = 0

    for page_num, ptext in pages_data:
        if not ptext:
            continue
        if full_text_parts:
            # Join pages with double newline
            full_text_parts.append("\n\n")
            current_offset += 2
        
        start_char = current_offset
        full_text_parts.append(ptext)
        current_offset += len(ptext)
        page_bounds.append((page_num, start_char, current_offset))

    full_document_text = "".join(full_text_parts)

    if not full_document_text.strip():
        return "", []

    def get_page_for_offset(offset: int) -> int:
        for pnum, s, e in page_bounds:
            if s <= offset < e:
                return pnum
        return page_bounds[-1][0] if page_bounds else 1

    # Chunking using paragraph / line breaks while respecting section boundaries
    raw_paragraphs = [p.strip() for p in re.split(r"\n\n+", full_document_text) if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [p.strip() for p in full_document_text.splitlines() if p.strip()]

    # Search for paragraph start offsets in full_document_text
    search_pos = 0
    para_offsets: List[Tuple[str, int, int]] = []
    for para in raw_paragraphs:
        idx = full_document_text.find(para, search_pos)
        if idx != -1:
            para_offsets.append((para, idx, idx + len(para)))
            search_pos = idx + len(para)

    # Refine paragraphs longer than 1000 characters into sentence-level blocks
    refined_blocks: List[Tuple[str, int, int]] = []
    for para, p_start, p_end in para_offsets:
        if len(para) > 1000:
            s_matches = list(re.finditer(r"(?:[.!?]\s+|\n+)", para))
            s_prev = 0
            for sm in s_matches:
                s_chunk = para[s_prev : sm.end()].strip()
                if s_chunk:
                    c_idx = full_document_text.find(s_chunk, p_start + s_prev)
                    if c_idx != -1:
                        refined_blocks.append((s_chunk, c_idx, c_idx + len(s_chunk)))
                s_prev = sm.end()
            if s_prev < len(para):
                tail = para[s_prev:].strip()
                if tail:
                    c_idx = full_document_text.find(tail, p_start + s_prev)
                    if c_idx != -1:
                        refined_blocks.append((tail, c_idx, c_idx + len(tail)))
        else:
            refined_blocks.append((para, p_start, p_end))

    if not refined_blocks:
        trimmed = full_document_text.strip()[:1200]
        passages = [
            ResumePassage(
                passage_id="pass_01",
                candidate_id=candidate_id,
                page_number=1,
                section_name="General",
                text_content=trimmed,
                character_start=0,
                character_end=len(trimmed),
            )
        ]
        return full_document_text, passages

    passages: List[ResumePassage] = []
    current_section = "General"
    passage_idx = 1

    # Group blocks into coherent 150-250 word chunks (maximum ~1200 characters)
    current_chunk_blocks: List[Tuple[str, int, int]] = []
    current_chunk_words = 0
    current_chunk_chars = 0

    for block, b_start, b_end in refined_blocks:
        # Check if block acts as a section header
        if SECTION_HEADER_REGEX.match(block) and len(block.split()) <= 4:
            current_section = block.title()

        words = block.split()
        block_word_count = len(words)
        block_char_count = len(block)

        # Finalize chunk if adding block exceeds target words or safe character limit (~1200 chars)
        if current_chunk_blocks and (
            (current_chunk_words + block_word_count > target_word_count) or
            (current_chunk_chars + block_char_count > 1200)
        ):
            chunk_start = current_chunk_blocks[0][1]
            chunk_end = current_chunk_blocks[-1][2]
            chunk_text = full_document_text[chunk_start:chunk_end]

            passages.append(
                ResumePassage(
                    passage_id=f"pass_{passage_idx:02d}",
                    candidate_id=candidate_id,
                    page_number=get_page_for_offset(chunk_start),
                    section_name=current_section,
                    text_content=chunk_text,
                    character_start=chunk_start,
                    character_end=chunk_end,
                )
            )
            passage_idx += 1
            current_chunk_blocks = []
            current_chunk_words = 0
            current_chunk_chars = 0

        current_chunk_blocks.append((block, b_start, b_end))
        current_chunk_words += block_word_count
        current_chunk_chars += block_char_count

    # Flush any remaining blocks
    if current_chunk_blocks:
        chunk_start = current_chunk_blocks[0][1]
        chunk_end = current_chunk_blocks[-1][2]
        chunk_text = full_document_text[chunk_start:chunk_end]

        passages.append(
            ResumePassage(
                passage_id=f"pass_{passage_idx:02d}",
                candidate_id=candidate_id,
                page_number=get_page_for_offset(chunk_start),
                section_name=current_section,
                text_content=chunk_text,
                character_start=chunk_start,
                character_end=chunk_end,
            )
        )

    return full_document_text, passages


def extract_candidate_profile(
    file_bytes: bytes,
    filename: str,
    candidate_id: str
) -> Tuple[CandidateProfile, str]:
    """
    Orchestrates end-to-end PDF processing for a single resume candidate.
    Returns:
        (CandidateProfile, full_document_text)
    Raises:
        DocumentProcessingError on corrupt, encrypted, or invalid files.
    """
    pages_data = extract_pages_text(file_bytes)
    full_text, passages = segment_into_passages(pages_data, candidate_id)

    warnings: List[str] = []
    if len(full_text.strip()) < 30:
        warnings.append(
            "Document contains fewer than 30 readable characters. "
            "Scanned or image-only documents require OCR (not supported in text-only mode)."
        )

    # Basic regex heuristics to locate candidate name or email from early lines
    candidate_name = "Unknown Candidate"
    contact = CandidateContact()

    if full_text:
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        if lines:
            # Candidate name heuristic: first non-empty line with 2-4 capitalized words
            first_line = lines[0]
            if len(first_line.split()) in (2, 3, 4) and len(first_line) < 50:
                candidate_name = first_line

        # Email detection
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", full_text)
        if email_match:
            contact.email = email_match.group(0)

        # Phone detection
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", full_text)
        if phone_match:
            contact.phone = phone_match.group(0)

    profile = CandidateProfile(
        candidate_id=candidate_id,
        filename=filename,
        candidate_name=candidate_name,
        contact_info=contact,
        passages=passages,
        extraction_warnings=warnings,
        raw_text_length=len(full_text),
    )

    return profile, full_text


# Backward compatibility alias
process_resume_pdf = extract_candidate_profile

