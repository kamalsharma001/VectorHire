"""
VectorHire Deterministic Evidence Provenance Verification Service.
Stage 1: Deterministically verifies whether proposed evidence quotes exist
verbatim or as recoverable normalized spans in the candidate's extracted document text.
Guarantees:
- Exact verbatim verification with exact character offset recovery.
- Normalized whitespace and line-wrap recovery (distinguished as fuzzy_recovered).
- Token-overlap heuristic (Jaccard >= 0.85) assists discovery but CANNOT independently verify provenance.
- Rejection of fabricated, materially altered, or unlocatable text.
- Full provenance record with candidate_id, requirement_id, passage_id, page, and offsets.
"""

import re
from typing import List, Optional, Set, Tuple

from app.schemas.candidate import ResumePassage
from app.schemas.common import CandidateId, PassageId, RequirementId
from app.schemas.evidence import SourceProvenance


def calculate_token_jaccard(text_a: str, text_b: str) -> float:
    """
    Computes token-level Jaccard similarity between two strings:
    Jaccard = |Tokens(A) & Tokens(B)| / |Tokens(A) | Tokens(B)|
    """
    tokens_a: Set[str] = set(re.findall(r"\b[a-zA-Z0-9]+\b", text_a.lower()))
    tokens_b: Set[str] = set(re.findall(r"\b[a-zA-Z0-9]+\b", text_b.lower()))

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return float(intersection / union) if union > 0 else 0.0


def normalize_whitespace(text: str) -> str:
    """Collapses multiple spaces, newlines, and tabs into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def locate_passage_metadata(
    character_start: int,
    character_end: int,
    passages: Optional[List[ResumePassage]]
) -> Tuple[Optional[PassageId], Optional[int], Optional[str]]:
    """
    Finds the passage ID, page number, and section name containing the character span.
    """
    if not passages:
        return None, None, None

    for passage in passages:
        # Check if the character span overlaps or is contained in this passage
        if passage.character_start <= character_start and character_end <= passage.character_end:
            return passage.passage_id, passage.page_number, passage.section_name

    # If not completely contained, find best overlapping passage
    best_passage: Optional[ResumePassage] = None
    max_overlap = -1
    for passage in passages:
        start_ov = max(passage.character_start, character_start)
        end_ov = min(passage.character_end, character_end)
        overlap = end_ov - start_ov
        if overlap > max_overlap and overlap > 0:
            max_overlap = overlap
            best_passage = passage

    if best_passage:
        return best_passage.passage_id, best_passage.page_number, best_passage.section_name

    return None, None, None


MAX_PROVENANCE_QUOTE_LENGTH = 1500


def extract_concise_source_span(
    raw_document_text: str,
    char_start: int,
    char_end: int,
    max_length: int = MAX_PROVENANCE_QUOTE_LENGTH,
    search_terms: Optional[List[str]] = None,
) -> Tuple[int, int, str]:
    """
    Extracts a contiguous verbatim excerpt from raw_document_text within [char_start, char_end]
    guaranteeing length <= max_length (default 1500) and exact offset recalculation.
    
    Guarantees:
    - Never fabricates text or joins non-contiguous spans with ellipses.
    - raw_document_text[new_start:new_end] == exact_span_quote.
    - Prioritizes sentences containing key search terms where available.
    - Preserves sentence or word boundaries where possible.
    """
    full_span = raw_document_text[char_start:char_end]
    if len(full_span) <= max_length:
        return char_start, char_end, full_span

    # Segment the span into sentences while preserving relative offsets
    sentence_matches = list(re.finditer(r"(?:[.!?]\s+|\n+)", full_span))
    sentence_spans: List[Tuple[int, int]] = []
    prev_pos = 0
    for sm in sentence_matches:
        end_pos = sm.end()
        sentence_spans.append((prev_pos, end_pos))
        prev_pos = end_pos
    if prev_pos < len(full_span):
        sentence_spans.append((prev_pos, len(full_span)))

    # Determine anchor sentence: sentence with highest concentration of search terms
    anchor_idx = 0
    if search_terms:
        max_hits = -1
        for idx, (s_start, s_end) in enumerate(sentence_spans):
            s_text = full_span[s_start:s_end].lower()
            hits = sum(1 for term in search_terms if term.lower() in s_text)
            if hits > max_hits and hits > 0:
                max_hits = hits
                anchor_idx = idx

    # Expand outward from anchor sentence to include surrounding context up to max_length
    win_start_idx = anchor_idx
    win_end_idx = anchor_idx

    while True:
        # Try expanding forward
        if win_end_idx + 1 < len(sentence_spans):
            cand_len = sentence_spans[win_end_idx + 1][1] - sentence_spans[win_start_idx][0]
            if cand_len <= max_length:
                win_end_idx += 1
                continue

        # Try expanding backward
        if win_start_idx > 0:
            cand_len = sentence_spans[win_end_idx][1] - sentence_spans[win_start_idx - 1][0]
            if cand_len <= max_length:
                win_start_idx -= 1
                continue

        break

    sub_start_rel = sentence_spans[win_start_idx][0]
    sub_end_rel = sentence_spans[win_end_idx][1]

    # If the single anchor sentence itself is longer than max_length, cut at last word boundary
    if (sub_end_rel - sub_start_rel) > max_length:
        cand_chunk = full_span[sub_start_rel : sub_start_rel + max_length]
        last_space = cand_chunk.rfind(" ")
        if last_space > 50:
            sub_end_rel = sub_start_rel + last_space
        else:
            sub_end_rel = sub_start_rel + max_length

    abs_start = char_start + sub_start_rel
    abs_end = char_start + sub_end_rel

    # Strip boundary whitespace while keeping offsets exact
    raw_sub = raw_document_text[abs_start:abs_end]
    l_strip = len(raw_sub) - len(raw_sub.lstrip())
    r_strip = len(raw_sub) - len(raw_sub.rstrip())

    final_start = abs_start + l_strip
    final_end = abs_end - r_strip
    final_quote = raw_document_text[final_start:final_end]

    # Hard clamp to guarantee len <= max_length
    if len(final_quote) > max_length:
        final_quote = final_quote[:max_length]
        final_end = final_start + len(final_quote)

    return final_start, final_end, final_quote


def verify_text_provenance(
    candidate_id: CandidateId,
    requirement_id: RequirementId,
    proposed_quote: str,
    raw_document_text: str,
    passages: Optional[List[ResumePassage]] = None,
    passage_id: Optional[PassageId] = None,
    page_number: Optional[int] = None,
    section_name: Optional[str] = None,
    jaccard_recovery_threshold: float = 0.85,
) -> SourceProvenance:
    """
    Stage 1 Verification: Deterministically verifies whether proposed_quote exists
    in raw_document_text.

    Returns:
        SourceProvenance with explicit verification status and exact character bounds.
    """
    clean_quote = proposed_quote.strip() if proposed_quote else ""

    # Guard 1: Empty quote
    if not clean_quote:
        return SourceProvenance(
            provenance_verified=False,
            candidate_id=candidate_id,
            requirement_id=requirement_id,
            passage_id=passage_id,
            source_page=page_number,
            source_section=section_name,
            exact_match=False,
            fuzzy_recovered=False,
            token_jaccard_similarity=0.0,
            failure_reason="Proposed evidence quote is empty.",
        )

    # Guard 2: Empty document text
    if not raw_document_text or not raw_document_text.strip():
        return SourceProvenance(
            provenance_verified=False,
            candidate_id=candidate_id,
            requirement_id=requirement_id,
            passage_id=passage_id,
            source_page=page_number,
            source_section=section_name,
            exact_match=False,
            fuzzy_recovered=False,
            token_jaccard_similarity=0.0,
            failure_reason="Candidate document text is empty.",
        )

    # 1. Exact verbatim match check
    exact_idx = raw_document_text.find(clean_quote)
    if exact_idx != -1:
        char_start = exact_idx
        char_end = exact_idx + len(clean_quote)
        if len(clean_quote) > MAX_PROVENANCE_QUOTE_LENGTH:
            char_start, char_end, quote_to_use = extract_concise_source_span(
                raw_document_text, char_start, char_end, max_length=MAX_PROVENANCE_QUOTE_LENGTH
            )
        else:
            quote_to_use = clean_quote
        found_pid, found_page, found_sec = locate_passage_metadata(char_start, char_end, passages)

        return SourceProvenance(
            provenance_verified=True,
            candidate_id=candidate_id,
            requirement_id=requirement_id,
            passage_id=found_pid or passage_id,
            source_page=found_page or page_number or 1,
            source_section=found_sec or section_name or "General",
            character_start=char_start,
            character_end=char_end,
            exact_span_quote=quote_to_use,
            token_jaccard_similarity=1.0,
            exact_match=True,
            fuzzy_recovered=False,
            failure_reason=None,
        )

    # 2. Normalized line-wrap and whitespace match check
    # Breaks quote into tokens and constructs a flexible regex matching whitespace or hyphen wraps
    quote_tokens = re.split(r"\s+", clean_quote)
    if quote_tokens:
        escaped_tokens = [re.escape(tok) for tok in quote_tokens if tok]
        # Match tokens separated by whitespace or soft hyphen line-wraps
        pattern = r"(?:\s+|-\s*|\s*-\s*)".join(escaped_tokens)
        match = re.search(pattern, raw_document_text, re.IGNORECASE)

        if match:
            char_start = match.start()
            char_end = match.end()
            matched_span = raw_document_text[char_start:char_end]
            if len(matched_span) > MAX_PROVENANCE_QUOTE_LENGTH:
                char_start, char_end, quote_to_use = extract_concise_source_span(
                    raw_document_text, char_start, char_end, max_length=MAX_PROVENANCE_QUOTE_LENGTH
                )
            else:
                quote_to_use = matched_span
            jaccard = calculate_token_jaccard(clean_quote, quote_to_use)

            # Check if this was verbatim or recovered due to formatting
            is_identical_str = (clean_quote == quote_to_use)
            found_pid, found_page, found_sec = locate_passage_metadata(char_start, char_end, passages)

            return SourceProvenance(
                provenance_verified=True,
                candidate_id=candidate_id,
                requirement_id=requirement_id,
                passage_id=found_pid or passage_id,
                source_page=found_page or page_number or 1,
                source_section=found_sec or section_name or "General",
                character_start=char_start,
                character_end=char_end,
                exact_span_quote=quote_to_use,
                token_jaccard_similarity=round(jaccard, 4),
                exact_match=is_identical_str,
                fuzzy_recovered=not is_identical_str,
                failure_reason=None,
            )

    # 3. Candidate Recovery Heuristic Evaluation
    # If the exact sequence is not in the text, find the best overlapping passage or block
    best_jaccard = 0.0
    best_passage_meta = (passage_id, page_number, section_name)

    if passages:
        for p in passages:
            sim = calculate_token_jaccard(clean_quote, p.text_content)
            if sim > best_jaccard:
                best_jaccard = sim
                best_passage_meta = (p.passage_id, p.page_number, p.section_name)
    else:
        # Fallback to computing similarity against entire document
        best_jaccard = calculate_token_jaccard(clean_quote, raw_document_text)

    # Rule: Token overlap threshold >= 0.85 can indicate a high-overlap candidate,
    # but CANNOT independently verify provenance if key terms were fabricated or altered.
    if best_jaccard >= jaccard_recovery_threshold:
        failure_msg = (
            f"Altered or unlocatable text: High token overlap ({best_jaccard:.2f} >= "
            f"{jaccard_recovery_threshold}) detected, but exact/normalized sequence does not "
            f"exist in document text. Provenance unverified."
        )
    else:
        failure_msg = (
            f"Proposed evidence quote not found in document (maximum token overlap "
            f"{best_jaccard:.2f} below threshold {jaccard_recovery_threshold})."
        )

    return SourceProvenance(
        provenance_verified=False,
        candidate_id=candidate_id,
        requirement_id=requirement_id,
        passage_id=best_passage_meta[0],
        source_page=best_passage_meta[1],
        source_section=best_passage_meta[2],
        character_start=None,
        character_end=None,
        exact_span_quote=None,
        token_jaccard_similarity=round(best_jaccard, 4),
        exact_match=False,
        fuzzy_recovered=False,
        failure_reason=failure_msg,
    )


def verify_passage_provenance(
    candidate_id: CandidateId,
    requirement_id: RequirementId,
    passage: ResumePassage,
    raw_document_text: str,
) -> SourceProvenance:
    """
    Verifies that a segmented ResumePassage physically exists verbatim
    in the raw document text at its declared character offsets.
    """
    start = passage.character_start
    end = passage.character_end

    # Guard bounds
    if 0 <= start < end <= len(raw_document_text):
        expected_span = raw_document_text[start:end]
        if expected_span == passage.text_content:
            char_start = start
            char_end = end
            quote_to_use = passage.text_content
            if len(quote_to_use) > MAX_PROVENANCE_QUOTE_LENGTH:
                char_start, char_end, quote_to_use = extract_concise_source_span(
                    raw_document_text, start, end, max_length=MAX_PROVENANCE_QUOTE_LENGTH
                )
            found_pid, found_page, found_sec = locate_passage_metadata(char_start, char_end, [passage])
            return SourceProvenance(
                provenance_verified=True,
                candidate_id=candidate_id,
                requirement_id=requirement_id,
                passage_id=found_pid or passage.passage_id,
                source_page=found_page or passage.page_number,
                source_section=found_sec or passage.section_name,
                character_start=char_start,
                character_end=char_end,
                exact_span_quote=quote_to_use,
                token_jaccard_similarity=1.0,
                exact_match=True,
                fuzzy_recovered=False,
                failure_reason=None,
            )

    # If character offsets didn't match directly, run text provenance search
    return verify_text_provenance(
        candidate_id=candidate_id,
        requirement_id=requirement_id,
        proposed_quote=passage.text_content,
        raw_document_text=raw_document_text,
        passages=[passage],
        passage_id=passage.passage_id,
        page_number=passage.page_number,
        section_name=passage.section_name,
    )
