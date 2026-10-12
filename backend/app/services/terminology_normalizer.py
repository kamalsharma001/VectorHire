"""
VectorHire Canonical Terminology Normalizer and Cross-Domain Equivalence Service.
Provides robust, boundary-safe lexical matching, punctuation normalization,
and bidirectional acronym-expansion mappings across diverse domains.

Guarantees:
- Boundary-aware regex matching for punctuation-heavy terms (C++, C#, .NET, Node.js, B.Tech.).
- Strict substring isolation: Prevents false positives (e.g. 'c' inside 'cat', '.net' inside 'magnet').
- Cross-domain bidirectional mappings (Tech, Finance, Healthcare, Engineering, Marketing, Operations).
- Strict non-conflation of legally or functionally distinct credentials (RN != LPN != MD; CPA != CFA).
- Clean preservation of exact source text for downstream provenance verification.
"""

import re
from typing import Dict, List, Optional, Set, Tuple


def build_boundary_pattern(term: str) -> str:
    """
    Constructs a robust regex pattern matching `term` as a discrete lexical unit,
    handling punctuation-bearing terms (e.g. 'C++', 'C#', '.NET', 'Node.js', 'B.Tech.')
    without introducing substring false positives.
    """
    term_stripped = term.strip()
    if not term_stripped:
        return ""

    first_is_word = term_stripped[0].isalnum() or term_stripped[0] == "_"
    last_is_word = term_stripped[-1].isalnum() or term_stripped[-1] == "_"

    # Left boundary:
    # If first character is alphanumeric/word, ensure it is not preceded by a word character.
    # If first character is non-word (e.g. '.NET'), ensure preceded by start of string or non-alnum.
    left = r"(?<!\w)" if first_is_word else r"(?:^|(?<=[^\w]))"

    # Right boundary:
    # If last character is alphanumeric/word, ensure it is not followed by a word character.
    # If last character is a symbol (e.g. 'C++', 'C#', 'B.Tech.'), ensure not followed by alnum or same symbol.
    if last_is_word:
        right = r"(?!\w)"
    else:
        last_char_esc = re.escape(term_stripped[-1])
        right = rf"(?![a-zA-Z0-9_{last_char_esc}])"

    return f"{left}{re.escape(term_stripped)}{right}"


AMBIGUOUS_SHORT_TOKENS = {"it", "be", "me", "ce", "in", "to", "or", "an", "at", "as", "is", "am", "do"}


def matches_boundary_term(term: str, text: str) -> bool:
    """
    Tests whether `term` appears as a discrete lexical token in `text`.
    For ambiguous short tokens (e.g. 'it', 'be', 'me'), prevents false matches
    on common English stopwords unless formatted in uppercase (e.g. 'IT', 'BE')
    or qualified by degree/domain context.
    """
    clean_term = term.strip()
    if not clean_term:
        return False
    lower_term = clean_term.lower()

    if lower_term in AMBIGUOUS_SHORT_TOKENS:
        # Require uppercase in text (e.g., " IT ", " BE ", " ME ")
        upper_pat = rf"(?<![a-zA-Z0-9]){re.escape(clean_term.upper())}(?![a-zA-Z0-9])"
        if re.search(upper_pat, text):
            return True
        # Or require degree/department contextual qualifier
        context_pat = rf"\b(?:degree\s+in|major\s+in|department\s+of|field\s+of|bachelor\s+of)\s+{re.escape(lower_term)}\b"
        return bool(re.search(context_pat, text, re.IGNORECASE))

    pattern = build_boundary_pattern(clean_term)
    if not pattern:
        return False
    return bool(re.search(pattern, text, re.IGNORECASE))


class CanonicalTerminologyNormalizer:
    """
    Centralized cross-domain canonical terminology engine.
    Maintains bidirectional equivalence dictionaries, common acronym expansions,
    and punctuation variant resolvers across multiple professional domains.
    """

    # 1. Bidirectional acronym <-> full expansion mappings (normalized lowercase keys)
    # Acronyms map to canonical expansions, and canonical expansions map to canonical acronyms.
    _CROSS_DOMAIN_ACRONYMS: Dict[str, str] = {
        # Software Engineering, IT & Data Science
        "dsa": "data structures and algorithms",
        "oop": "object-oriented programming",
        "os": "operating systems",
        "dbms": "database management systems",
        "rdbms": "relational database management systems",
        "ci/cd": "continuous integration and continuous deployment",
        "cicd": "continuous integration and continuous deployment",
        "ci-cd": "continuous integration and continuous deployment",
        "ai/ml": "artificial intelligence and machine learning",
        "nlp": "natural language processing",
        "cv": "computer vision",
        "k8s": "kubernetes",
        "ts": "typescript",
        "js": "javascript",
        "gcp": "google cloud platform",
        "aws": "amazon web services",
        "rest": "representational state transfer",
        "api": "application programming interface",
        "sql": "structured query language",
        
        # Education & Academic Degrees
        "cse": "computer science and engineering",
        "cs": "computer science",
        "ece": "electronics and communication engineering",
        "ee": "electrical engineering",
        "me": "mechanical engineering",
        "ce": "civil engineering",
        "it": "information technology",
        "b.tech": "bachelor of technology",
        "btech": "bachelor of technology",
        "b-tech": "bachelor of technology",
        "b.e.": "bachelor of engineering",
        "be": "bachelor of engineering",
        "b.s.": "bachelor of science",
        "bs": "bachelor of science",
        "bsc": "bachelor of science",
        "m.tech": "master of technology",
        "mtech": "master of technology",
        "m.s.": "master of science",
        "ms": "master of science",
        "msc": "master of science",
        "mba": "master of business administration",
        "phd": "doctor of philosophy",

        # Finance, Accounting & Operations
        "cpa": "certified public accountant",
        "gaap": "generally accepted accounting principles",
        "ifrs": "international financial reporting standards",
        "fp&a": "financial planning and analysis",
        "fpa": "financial planning and analysis",
        "p&l": "profit and loss",
        "pl": "profit and loss",
        "cfa": "chartered financial analyst",
        "sec": "securities and exchange commission",
        "ebitda": "earnings before interest taxes depreciation and amortization",
        "roi": "return on investment",

        # Healthcare & Allied Health Professions
        "rn": "registered nurse",
        "bls": "basic life support",
        "acls": "advanced cardiovascular life support",
        "ehr": "electronic health records",
        "emr": "electronic medical records",
        "hipaa": "health insurance portability and accountability act",
        "cpr": "cardiopulmonary resuscitation",

        # Mechanical, Electrical & Industrial Engineering
        "cad": "computer-aided design",
        "cam": "computer-aided manufacturing",
        "fea": "finite element analysis",
        "cfd": "computational fluid dynamics",
        "plc": "programmable logic controller",
        "hvac": "heating ventilation and air conditioning",
        "pe": "professional engineer",
        "scada": "supervisory control and data acquisition",

        # Marketing, Sales & Business Operations
        "seo": "search engine optimization",
        "sem": "search engine marketing",
        "ppc": "pay-per-click",
        "ctr": "click-through rate",
        "crm": "customer relationship management",
        "b2b": "business-to-business",
        "b2c": "business-to-consumer",
        "cac": "customer acquisition cost",
        "ltv": "customer lifetime value",
        "pmp": "project management professional",
        "sla": "service level agreement",
        "kpi": "key performance indicators",
        "hris": "human resources information system",
        "ats": "applicant tracking system",
    }

    # 2. Known punctuation variants for common technologies and degree expressions
    _PUNCTUATION_VARIANTS: Dict[str, List[str]] = {
        "c++": ["c++", "cpp"],
        "c#": ["c#", "csharp", "c-sharp"],
        ".net": [".net", "dotnet", ".net core", "dot net"],
        "node.js": ["node.js", "nodejs", "node"],
        "react.js": ["react.js", "reactjs", "react"],
        "vue.js": ["vue.js", "vuejs", "vue"],
        "next.js": ["next.js", "nextjs", "next"],
        "ci/cd": ["ci/cd", "ci-cd", "cicd", "continuous integration"],
        "postgresql": ["postgresql", "postgres", "psql", "sql"],
        "postgres": ["postgres", "postgresql", "psql", "sql"],
        "sql": ["sql", "structured query language", "postgresql", "postgres", "mysql", "sqlite"],
        "testing": ["testing", "unit tests", "unit testing", "automated testing", "test suites"],
        "unit tests": ["unit tests", "unit testing", "testing", "automated testing"],
        "unit testing": ["unit testing", "unit tests", "testing", "automated testing"],
        "k8s": ["k8s", "kubernetes"],
        "golang": ["golang", "go"],
        "b.tech.": ["b.tech.", "b.tech", "btech", "b-tech"],
        "b.tech": ["b.tech", "b.tech.", "btech", "b-tech"],
        "b.e.": ["b.e.", "b.e", "be"],
        "b.s.": ["b.s.", "b.s", "bs", "b.sc.", "bsc"],
        "m.tech.": ["m.tech.", "m.tech", "mtech"],
        "m.s.": ["m.s.", "m.s", "ms", "m.sc.", "msc"],
        "ph.d.": ["ph.d.", "ph.d", "phd"],
    }

    # 3. Functional Tech Equivalency Families
    # Used for controlled expansion or synonym discovery during retrieval
    _FUNCTIONAL_FAMILIES: Dict[str, List[str]] = {
        "rdbms": ["postgresql", "postgres", "mysql", "oracle", "sql server", "mariadb", "sqlite"],
        "relational databases": ["postgresql", "postgres", "mysql", "oracle", "sql server", "mariadb"],
        "nosql": ["mongodb", "cassandra", "dynamodb", "couchbase", "redis"],
        "python web framework": ["fastapi", "flask", "django"],
        "cloud platform": ["aws", "azure", "gcp", "google cloud"],
        "crm": ["salesforce", "hubspot", "zoho crm", "microsoft dynamics"],
    }

    @classmethod
    def expand_term_variants(cls, term: str) -> Set[str]:
        """
        Derives legitimate spelling, punctuation, and acronym variants for a term.
        Bidirectionally maps acronyms to expansions and expansions to acronyms.
        """
        clean = term.strip().lower()
        if not clean:
            return set()

        variants: Set[str] = {term.strip()}

        # Check punctuation variant table
        if clean in cls._PUNCTUATION_VARIANTS:
            variants.update(cls._PUNCTUATION_VARIANTS[clean])

        # Check acronym -> expansion
        if clean in cls._CROSS_DOMAIN_ACRONYMS:
            expansion = cls._CROSS_DOMAIN_ACRONYMS[clean]
            variants.add(expansion)
            # Add capitalized or dotted versions if applicable
            if "." not in clean and len(clean) <= 5:
                variants.add(".".join(list(clean)) + ".")

        # Check expansion -> acronym (reverse lookup)
        for acr, exp in cls._CROSS_DOMAIN_ACRONYMS.items():
            if clean == exp or clean == exp.replace(" and ", " & "):
                variants.add(acr)
                variants.add(acr.upper())

        return variants

    @classmethod
    def get_all_requirement_terms(
        cls,
        name: str,
        description: str,
        normalized_terms: Optional[List[str]] = None,
        controlled_aliases: Optional[List[str]] = None,
    ) -> Set[str]:
        """
        Aggregates declared requirement terms and expands them with safe canonical variants.
        """
        all_terms: Set[str] = set()

        # Seed with declared terms
        if name:
            all_terms.add(name.strip())
            all_terms.update(cls.expand_term_variants(name))

        if normalized_terms:
            for t in normalized_terms:
                if t and t.strip():
                    all_terms.add(t.strip())
                    all_terms.update(cls.expand_term_variants(t))

        if controlled_aliases:
            for a in controlled_aliases:
                if a and a.strip():
                    all_terms.add(a.strip())
                    all_terms.update(cls.expand_term_variants(a))

        # Check key phrases in name or description for known domain terms
        full_text = f"{name} {description}".lower()
        for acr, exp in cls._CROSS_DOMAIN_ACRONYMS.items():
            if matches_boundary_term(acr, full_text) or matches_boundary_term(exp, full_text):
                all_terms.add(acr)
                all_terms.add(exp)

        for p_term, p_vars in cls._PUNCTUATION_VARIANTS.items():
            if matches_boundary_term(p_term, full_text):
                all_terms.update(p_vars)

        return {t for t in all_terms if len(t.strip()) > 0}
