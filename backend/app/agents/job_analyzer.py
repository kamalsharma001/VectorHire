"""
VectorHire Job Description Analysis Agent.
Parses raw job descriptions into structured, recruiter-editable JobSpecifications.
Classifies criteria into universal 5-category rubric, identifies hard gates,
and expands normalized terms and domain aliases for hybrid retrieval.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.exceptions import ProviderAPIError
from app.providers.base_llm import BaseLLMProvider
from app.providers.provider_factory import get_llm_provider
from app.schemas.common import RequirementCategory
from app.schemas.job import JobRequirement, JobSpecification
from app.schemas.rubric import ScoringRubric
from app.services.terminology_normalizer import CanonicalTerminologyNormalizer

logger = logging.getLogger(__name__)

JOB_ANALYSIS_SYSTEM_PROMPT = """You are an expert recruitment job architecture specialist for VectorHire.
Your task is to analyze unstructured job descriptions and extract structured, verifiable criteria for evidence-based resume screening.

CRITICAL INSTRUCTIONS:
1. Extract the primary job title, industry domain, seniority level, and minimum years of experience (if stated).
2. Decompose the requirements into granular, distinct, measurable criteria:
   - Granular Criteria Decomposition: Decompose multi-skill enumerations and compound lists into separate, distinct criteria. For example, 'Python fundamentals, DSA/problem solving, REST APIs, SQL, Git, and testing' MUST be broken down into individual criteria: Python Fundamentals, Data Structures & Algorithms, REST API Development, SQL and Relational Databases, Version Control (Git), and Software Testing.
   - Comprehensive Extraction: Extract all stated mandatory requirements AND preferred/nice-to-have qualifications. Classify secondary or 'nice-to-have' skills under "preferred_competencies". Do not drop preferred technologies (e.g. FastAPI, Flask, ORM, pytest).
   - Education Credentials: Degrees (B.Tech, B.E., B.Sc., B.S., BSN, Master's, etc.) MUST be classified under "education".
   - Professional Experience: Never infer mandatory experience tenure if the role is entry-level, fresher, or states experience is not required/optional.
3. Classify EVERY requirement into EXACTLY ONE of the following 5 categories:
   - "mandatory_competencies": Core technical or professional skills essential to perform the role.
   - "license_registration": Required legal, regulatory, medical, or formal certifications/licenses (e.g. RN, MD, Bar, CPA).
   - "experience_tenure": Years of experience, specific domain tenure, or leadership history.
   - "education": Degrees, academic fields, or formal coursework requirements.
   - "preferred_competencies": "Nice to have" or secondary qualifications that are not strictly required.
4. Set "is_hard_gate": true for non-negotiable legal/regulatory licenses, strict minimum degree requirements, or explicit hard constraints.
5. Provide 2-5 canonical "normalized_terms" and domain "controlled_aliases" (standard abbreviations, degree variants, and domain acronyms like DSA, CSE, CPA, RN, CAD, SEO, K8s, CI/CD) to power bidirectional hybrid lexical-semantic retrieval across diverse industries.
6. Assign sequential requirement IDs starting with 'req_01', 'req_02', etc.

OUTPUT SCHEMA:
You MUST respond with a single valid JSON object formatted as follows:
{
  "job_title": "string",
  "detected_domain": "string",
  "seniority_level": "string",
  "min_experience_years": number or null,
  "requirements": [
    {
      "requirement_id": "req_01",
      "name": "Short Name",
      "description": "Specific expected capability",
      "category": "mandatory_competencies | license_registration | experience_tenure | education | preferred_competencies",
      "is_hard_gate": true | false,
      "weight": 1.0,
      "normalized_terms": ["term1", "term2"],
      "controlled_aliases": ["alias1", "alias2"]
    }
  ],
  "analysis_summary": "Brief 1-2 sentence overview of the role and key focal areas."
}
"""


class JobAnalysisAgent:
    """
    Analyzes unstructured Job Descriptions into validated, recruiter-editable JobSpecifications.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()
        self.settings = get_settings()

    def _build_prompt(self, job_description_text: str, job_title_hint: Optional[str] = None) -> str:
        hint_text = f"\nSuggested Job Title: {job_title_hint}" if job_title_hint else ""
        return f"""Analyze the following Job Description:{hint_text}

<job_description>
{job_description_text}
</job_description>

Produce the structured job specification JSON according to instructions:"""

    def _fallback_heuristic_parse(
        self, job_description_text: str, job_title_hint: Optional[str] = None
    ) -> JobSpecification:
        """Fallback deterministic heuristic parser if LLM provider is unavailable."""
        title = job_title_hint or "Professional Role"
        raw_lines = [line.strip() for line in job_description_text.split("\n") if line.strip()]

        # Extract title from explicit header or clean first line if no hint provided
        if not job_title_hint and raw_lines:
            m_title = re.match(r"^title\s*:\s*(.*)$", raw_lines[0], re.IGNORECASE)
            if m_title:
                title = m_title.group(1).strip()
            elif len(raw_lines[0]) < 100 and not any(kw in raw_lines[0].lower() for kw in ["requirement", "responsibilit", "qualificat", "accepts", "looking", "seeking"]):
                title = raw_lines[0].rstrip(".!?")

        # Decompose compound sections, multi-sentence lines, and introductory statements
        lines: List[str] = []
        for raw_line in raw_lines:
            prefix = ""
            content = raw_line

            # Check for section header prefixes (e.g. "Mandatory: ...", "Preferred: ...")
            m_prefix = re.match(r"^(mandatory|required|preferred|responsibilities|duties|qualifications|requirements)\s*:\s*(.*)$", raw_line, re.IGNORECASE)
            if m_prefix:
                prefix = m_prefix.group(1).capitalize() + ": "
                content = m_prefix.group(2)
            elif not job_title_hint and re.match(r"^title\s*:\s*(.*)$", raw_line, re.IGNORECASE):
                continue

            # Extract introductory role sentences (e.g. "Seeking a Staff Security Engineer with ...")
            m_intro = re.match(r"^(?:seeking|looking for|hiring|we are seeking|we are looking for)\s+(?:an?|the)?\s*([A-Za-z0-9\s\-/]+?)\s+(?:with|who has|having)\s+(.*)$", content, re.IGNORECASE)
            if m_intro:
                if title == "Professional Role":
                    title = m_intro.group(1).strip()
                content = m_intro.group(2)

            # Mask parentheticals to prevent breaking inside acronyms or nested descriptions
            parens: List[str] = []
            def _mask_paren(m: re.Match) -> str:
                parens.append(m.group(0))
                return f"___DECOMP_PAREN_{len(parens)-1}___"
            masked = re.sub(r"\([^)]*\)", _mask_paren, content)

            # Split on sentence boundaries (. followed by space/end) or semicolons
            sub_items = re.split(r";|\.(?:\s+|$)", masked)
            final_sub_items = []
            for s in sub_items:
                s_stripped = s.strip()
                if not s_stripped:
                    continue
                # Split compound qualifications connected by 'and' before key requirement anchors
                clause_splits = re.split(
                    r"\s+and\s+(?=(?:\d+\+?\s+years?|experience\s+in|proven\s+track|bachelor|master|ph\.?d|certified|certification|active\s+|must\s+have|strong\s+))",
                    s_stripped,
                    flags=re.IGNORECASE,
                )
                final_sub_items.extend(clause_splits)

            for item in final_sub_items:
                for idx, p in enumerate(parens):
                    item = item.replace(f"___DECOMP_PAREN_{idx}___", p)
                item = item.strip()
                if len(item) >= 4:
                    if prefix and not item.lower().startswith(prefix.lower()):
                        lines.append(f"{prefix}{item}")
                    else:
                        lines.append(item)

        requirements: List[JobRequirement] = []
        seen_names = set()
        req_idx = 1

        for line in lines:
            clean = re.sub(r"^(?:[-*•\s]+|(?:\d+[\.)]\s+))", "", line).strip()
            if len(clean) < 8 or req_idx > 12:
                continue

            lower_clean = clean.lower()

            # Skip header lines, metadata, and framing boilerplate
            # Note: Only match when followed by a colon, when the line IS the header label itself,
            # or when it's an introductory framing statement (e.g. "We are seeking a...")
            if any(lower_clean == prefix or lower_clean.startswith(f"{prefix}:") or lower_clean.startswith(f"{prefix} :") for prefix in [
                "job title", "role", "position", "title", "about the role",
                "requirements", "key responsibilities", "responsibilities",
                "qualifications", "overview", "summary", "about us", "who we are",
                "our company"
            ]) or any(lower_clean.startswith(intro) for intro in [
                "we are seeking", "we are looking for", "our team is seeking",
                "our company is looking", "we are hiring", "about the role", "position summary"
            ]) or lower_clean in {
                "requirements", "responsibilities", "qualifications", "duties",
                "minimum requirements", "core requirements", "preferred qualifications",
                "key requirements", "role requirements"
            }:
                continue

            # 1. Check for explicit statements that experience is NOT mandatory / fresher
            is_fresher_or_no_exp = (
                any(
                    phrase in lower_clean
                    for phrase in [
                        "experience is not mandatory",
                        "experience not mandatory",
                        "experience not required",
                        "no experience required",
                        "freshers can apply",
                        "fresher",
                        "0 years",
                        "entry-level",
                        "entry level",
                    ]
                )
                and ("not mandatory" in lower_clean or "not required" in lower_clean or "fresh" in lower_clean or "entry" in lower_clean)
            )

            # 2. Check for education credentials
            is_education = any(
                deg in lower_clean
                for deg in [
                    "b.tech", "b.e.", "b.e", "b.sc", "b.s.", "bachelor", "master",
                    "m.tech", "m.s.", "ph.d", "degree in", "diploma in", "bca", "mca", "bsn"
                ]
            ) and not any(kw in lower_clean for kw in ["preferred", "nice to have"])

            # 3. Check for license / registration
            is_license = any(
                lic in lower_clean
                for lic in ["license", "certified", "certification", "registered nurse", "cpa", "pmp", "acls", "bls", "pe license"]
            ) and not any(kw in lower_clean for kw in ["preferred", "nice to have"])

            # 4. Check for preferred competencies
            is_preferred = any(
                pref in lower_clean
                for pref in ["preferred", "nice to have", "plus", "bonus", "optional", "good to have"]
            )

            # 5. Check for required experience (only if NOT fresher / not optional)
            is_exp = (
                any(exp in lower_clean for exp in ["year", "years", "tenure"])
                and "experience" in lower_clean
                and not is_fresher_or_no_exp
            )

            if is_education:
                clean_deg = re.sub(r"^(?:education|degree|qualification)\s*[:\-]\s*", "", clean, flags=re.IGNORECASE).strip()
                deg_match = re.search(
                    r"\b(?:bachelor['s]*|master['s]*|doctoral|doctorate|degree|diploma|associate['s]*|ph\.?d\.?|b\.?tech|b\.?e\.?|b\.?sc|b\.?s\.?|m\.?tech|m\.?s\.?|mba|cpa|cfa|bsn|rn|jd|md)\b[^\n.;]*",
                    clean_deg,
                    re.IGNORECASE,
                )
                if deg_match and len(deg_match.group(0).strip()) >= len(clean_deg) * 0.5:
                    deg_name = deg_match.group(0).strip()
                elif clean_deg:
                    deg_name = clean_deg
                else:
                    deg_name = f"Degree or Qualification for {title}"

                if deg_name.lower() not in seen_names:
                    seen_names.add(deg_name.lower())
                    expanded = list(CanonicalTerminologyNormalizer.get_all_requirement_terms(deg_name, clean))
                    norm_terms = list(expanded[:6]) if expanded else [deg_name]
                    
                    # Add common degree abbreviations and domain field keywords
                    lower_deg = deg_name.lower()
                    if any(deg_kw in lower_deg for deg_kw in ["bachelor", "b.s", "b.sc", "b.tech", "b.e."]):
                        for abbr in ["bachelor", "b.s.", "b.sc", "b.tech", "b.e.", "bs", "degree"]:
                            if abbr not in norm_terms:
                                norm_terms.append(abbr)
                    if "accounting" in lower_deg:
                        for acc_kw in ["accounting", "finance"]:
                            if acc_kw not in norm_terms:
                                norm_terms.append(acc_kw)
                    if "finance" in lower_deg and "finance" not in norm_terms:
                        norm_terms.append("finance")
                    if any(n_kw in lower_deg for n_kw in ["nursing", "bsn"]):
                        for n_kw in ["nursing", "bsn", "rn"]:
                            if n_kw not in norm_terms:
                                norm_terms.append(n_kw)
                    if any(cs_kw in lower_deg for cs_kw in ["computer", "software", "it"]):
                        for cs_kw in ["computer science", "cs", "cse", "it"]:
                            if cs_kw not in norm_terms:
                                norm_terms.append(cs_kw)

                    aliases = [t for t in expanded if t.lower() != deg_name.lower()][:6]

                    requirements.append(
                        JobRequirement(
                            requirement_id=f"req_{req_idx:02d}",
                            name=deg_name[:80],
                            description=clean[:500],
                            category=RequirementCategory.EDUCATION,
                            is_hard_gate=True,
                            weight=2.0,
                            importance="mandatory",
                            normalized_terms=norm_terms[:10],
                            controlled_aliases=aliases,
                        )
                    )
                    req_idx += 1
                continue

            if is_fresher_or_no_exp:
                # Strictly skip creating a mandatory experience tenure requirement
                continue

            # Strip introductory framing boilerplate
            body = re.sub(
                r"^(?:core\s+|key\s+|minimum\s+)?requirements?\s*(?:include|are|:)\s*",
                "", clean, flags=re.IGNORECASE
            )
            body = re.sub(r"^(?:required|mandatory)(?:\s+requirements?)?\s*(?::|include|are)?\s*", "", body, flags=re.IGNORECASE)
            body = re.sub(r"^(?:preferred|nice to have|plus|bonus)(?:\s+requirements?)?\s*(?::|include|are)?\s*", "", body, flags=re.IGNORECASE)
            body = re.sub(r"^(?:responsibilities|duties)\s*(?::|include|are)?\s*", "", body, flags=re.IGNORECASE)
            body = body.lstrip(": -").strip()
            body = re.sub(
                r"^(?:strong\s+(?:foundation|background|skills?|understanding)\s+(?:in|of)\s+|hands-on\s+experience\s+(?:with|in)\s+|experience\s+(?:with|in|building|developing)\s+|familiarity\s+with\s+|knowledge\s+of\s+|proficiency\s+in\s+|working\s+knowledge\s+of\s+|demonstrated\s+ability\s+to\s+|proven\s+ability\s+to\s+|ability\s+to\s+)",
                "", body, flags=re.IGNORECASE
            )
            body = body.rstrip(".!?")

            # Split compound lists on commas, semicolons, and Oxford 'and', preserving multi-word concepts with internal 'and' and parentheticals
            # Mask parentheticals so commas inside them (e.g. '(e.g. PostgreSQL, MySQL)') do not cause fragmented splits
            parens: list = []
            def _mask_paren(m):
                parens.append(m.group(0))
                return f"___PAREN_{len(parens)-1}___"
            masked_body = re.sub(r"\([^)]*\)", _mask_paren, body)

            raw_parts = [
                p.strip().rstrip(".!?")
                for p in re.split(r",\s*(?:and\s+)?|;\s*|(?:\s+as\s+well\s+as\s+)", masked_body, flags=re.IGNORECASE)
                if len(p.strip()) > 1
            ]
            parts = []
            for p in raw_parts:
                for idx, orig in enumerate(parens):
                    p = p.replace(f"___PAREN_{idx}___", orig)
                parts.append(p)

            if len(parts) >= 2 and any(len(p) <= 55 for p in parts):
                for part in parts:
                    clean_part = part.strip()
                    if len(clean_part) < 2 or clean_part.lower() in ["etc", "more", "others"]:
                        continue
                    clean_name = re.sub(r"\b(?:are preferred|is preferred|preferred)\b", "", clean_part, flags=re.IGNORECASE).strip()
                    if len(clean_name) < 2 or clean_name.lower() in seen_names:
                        continue
                    seen_names.add(clean_name.lower())

                    cat = RequirementCategory.PREFERRED_COMPETENCY if is_preferred else RequirementCategory.MANDATORY_COMPETENCY
                    importance_tier = "preferred" if is_preferred else "mandatory"
                    req_weight = 1.0 if is_preferred else 3.0
                    desc_text = f"Demonstrated capability and verified experience with {clean_name}."
                    expanded = list(CanonicalTerminologyNormalizer.get_all_requirement_terms(clean_name, desc_text))
                    norm_terms = expanded[:6] if expanded else [clean_name]
                    aliases = [t for t in expanded if t.lower() != clean_name.lower()][:6]

                    requirements.append(
                        JobRequirement(
                            requirement_id=f"req_{req_idx:02d}",
                            name=clean_name[:80],
                            description=desc_text,
                            category=cat,
                            is_hard_gate=False,
                            weight=req_weight,
                            importance=importance_tier,
                            normalized_terms=norm_terms,
                            controlled_aliases=aliases,
                        )
                    )
                    req_idx += 1
            else:
                cat = (
                    RequirementCategory.LICENSE_REGISTRATION if is_license
                    else RequirementCategory.PREFERRED_COMPETENCY if is_preferred
                    else RequirementCategory.EXPERIENCE_TENURE if is_exp
                    else RequirementCategory.MANDATORY_COMPETENCY
                )
                importance_tier = "preferred" if is_preferred else "mandatory"
                req_weight = (
                    2.0 if is_license
                    else 1.0 if is_preferred
                    else 2.0 if is_exp
                    else 3.0
                )
                clean_name = re.sub(r"\b(?:are preferred|is preferred|preferred|required)\b", "", body, flags=re.IGNORECASE).strip()
                clean_name = clean_name.rstrip(".!?:")
                if len(clean_name) <= 80:
                    req_name = clean_name
                else:
                    first_clause = re.split(r"[;:]", clean_name)[0].strip()
                    words = re.findall(r"\b[A-Za-z0-9+#./-]{2,}\b", first_clause)
                    req_name = " ".join(words[:8]) if words else clean_name[:80]

                if req_name.lower() not in seen_names:
                    seen_names.add(req_name.lower())
                    expanded = set(CanonicalTerminologyNormalizer.get_all_requirement_terms(req_name, clean))
                    expanded.add(req_name)

                    # Extract key substantive sub-clauses for retrieval
                    sub_clauses = re.split(r"\s+(?:from|including|with|across|and|using)\s+", req_name, flags=re.IGNORECASE)
                    for sc in sub_clauses:
                        sc_clean = sc.strip().rstrip(".,;:")
                        if len(sc_clean) >= 2 and sc_clean.lower() not in ["cross-functional", "external", "standards", "preparation", "the", "for"]:
                            expanded.add(sc_clean)

                    norm_terms = list(expanded)[:8]
                    aliases = [t for t in expanded if t.lower() != req_name.lower()][:6]

                    requirements.append(
                        JobRequirement(
                            requirement_id=f"req_{req_idx:02d}",
                            name=req_name[:80],
                            description=clean[:500],
                            category=cat,
                            is_hard_gate=is_license,
                            weight=req_weight,
                            importance=importance_tier,
                            normalized_terms=norm_terms,
                            controlled_aliases=aliases,
                        )
                    )
                    req_idx += 1

        if not requirements:
            requirements.append(
                JobRequirement(
                    requirement_id="req_01",
                    name="Core Professional Competency",
                    description="Demonstrated capability to perform the primary duties specified in the job description.",
                    category=RequirementCategory.MANDATORY_COMPETENCY,
                    is_hard_gate=False,
                    weight=3.0,
                    importance="mandatory",
                )
            )

        return JobSpecification(
            job_title=title[:150],
            detected_domain="General Professional",
            seniority_level="Mid-Level",
            requirements=requirements,
            rubric=ScoringRubric(
                gamma=self.settings.UNCERTAINTY_DISCOUNT_GAMMA,
                rubric_strategy="dynamic_importance",
            ),
        )

    def _sanitize_and_validate_spec(
        self, data: Dict[str, Any], fallback_title: Optional[str] = None
    ) -> JobSpecification:
        """Validates raw LLM response into a robust JobSpecification."""
        title = str(data.get("job_title", fallback_title or "Position Title")).strip() or "Position Title"
        domain = str(data.get("detected_domain", "General Professional")).strip() or "General Professional"
        seniority = str(data.get("seniority_level", "Mid-Level")).strip() or "Mid-Level"

        raw_years = data.get("min_experience_years")
        min_years = None
        if raw_years is not None:
            try:
                min_years = float(raw_years)
                if min_years < 0 or min_years > 50:
                    min_years = None
            except (ValueError, TypeError):
                min_years = None

        raw_reqs = data.get("requirements", [])
        if not isinstance(raw_reqs, list) or not raw_reqs:
            raise ValueError("No requirements list provided in model output")

        valid_requirements: List[JobRequirement] = []
        seen_ids = set()

        category_map = {
            "mandatory_competencies": RequirementCategory.MANDATORY_COMPETENCY,
            "mandatory": RequirementCategory.MANDATORY_COMPETENCY,
            "license_registration": RequirementCategory.LICENSE_REGISTRATION,
            "license": RequirementCategory.LICENSE_REGISTRATION,
            "licenses": RequirementCategory.LICENSE_REGISTRATION,
            "experience_tenure": RequirementCategory.EXPERIENCE_TENURE,
            "experience": RequirementCategory.EXPERIENCE_TENURE,
            "education": RequirementCategory.EDUCATION,
            "degree": RequirementCategory.EDUCATION,
            "preferred_competencies": RequirementCategory.PREFERRED_COMPETENCY,
            "preferred": RequirementCategory.PREFERRED_COMPETENCY,
        }

        for idx, item in enumerate(raw_reqs, start=1):
            if not isinstance(item, dict):
                continue

            raw_id = str(item.get("requirement_id", f"req_{idx:02d}")).strip()
            # Ensure valid ID pattern and uniqueness
            clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_id) or f"req_{idx:02d}"
            if clean_id in seen_ids or len(clean_id) < 3:
                clean_id = f"req_{idx:02d}"
            seen_ids.add(clean_id)

            name = str(item.get("name", f"Requirement {idx}")).strip() or f"Requirement {idx}"
            desc = str(item.get("description", name)).strip() or name
            if len(desc) < 5:
                desc = f"Required experience with {name}."

            cat_str = str(item.get("category", "mandatory_competencies")).strip().lower()
            category = category_map.get(cat_str, RequirementCategory.MANDATORY_COMPETENCY)

            is_hard_gate = bool(item.get("is_hard_gate", False))
            weight = float(item.get("weight", 1.0))
            weight = max(0.1, min(10.0, weight))

            norm_terms = [str(t).strip() for t in item.get("normalized_terms", []) if str(t).strip()]
            aliases = [str(a).strip() for a in item.get("controlled_aliases", []) if str(a).strip()]

            # Enrich normalized_terms and aliases via CanonicalTerminologyNormalizer
            all_canonical = list(CanonicalTerminologyNormalizer.get_all_requirement_terms(name, desc, norm_terms, aliases))
            merged_norm = list(dict.fromkeys(norm_terms + [t for t in all_canonical if t.lower() != name.lower()]))[:10]
            merged_aliases = list(dict.fromkeys(aliases + [t for t in all_canonical if t not in merged_norm]))[:10]

            valid_requirements.append(
                JobRequirement(
                    requirement_id=clean_id,
                    name=name[:150],
                    description=desc,
                    category=category,
                    is_hard_gate=is_hard_gate,
                    weight=weight,
                    importance=str(item.get("importance", "mandatory" if category == RequirementCategory.MANDATORY_COMPETENCY else "preferred")),
                    expected_evidence=item.get("expected_evidence"),
                    weight_rationale=item.get("weight_rationale"),
                    normalized_terms=merged_norm if merged_norm else norm_terms[:10],
                    controlled_aliases=merged_aliases if merged_aliases else aliases[:10],
                )
            )

        if not valid_requirements:
            raise ValueError("Zero valid requirements parsed from response")

        return JobSpecification(
            job_title=title[:150],
            detected_domain=domain[:100],
            seniority_level=seniority[:50],
            min_experience_years=min_years,
            requirements=valid_requirements,
            rubric=ScoringRubric(
                gamma=self.settings.UNCERTAINTY_DISCOUNT_GAMMA,
                rubric_strategy="dynamic_importance",
            ),
        )

    def analyze_job_description(
        self, job_description_text: str, job_title_hint: Optional[str] = None
    ) -> JobSpecification:
        """
        Synchronously analyzes a raw job description into an editable JobSpecification.
        """
        messages = [
            {"role": "system", "content": JOB_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(job_description_text, job_title_hint)},
        ]

        try:
            response_json = self.provider.generate_json(messages)
            return self._sanitize_and_validate_spec(response_json, job_title_hint)
        except Exception as exc:
            logger.warning("JobAnalysisAgent LLM extraction failed: %s. Using heuristic fallback.", str(exc)[:200])
            return self._fallback_heuristic_parse(job_description_text, job_title_hint)

    async def analyze_job_description_async(
        self, job_description_text: str, job_title_hint: Optional[str] = None
    ) -> JobSpecification:
        """
        Asynchronously analyzes a raw job description into an editable JobSpecification.
        """
        messages = [
            {"role": "system", "content": JOB_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(job_description_text, job_title_hint)},
        ]

        try:
            response_json = await self.provider.generate_json_async(messages)
            return self._sanitize_and_validate_spec(response_json, job_title_hint)
        except Exception as exc:
            logger.warning("JobAnalysisAgent async LLM extraction failed: %s. Using heuristic fallback.", str(exc)[:200])
            return self._fallback_heuristic_parse(job_description_text, job_title_hint)
