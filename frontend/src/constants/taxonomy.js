/**
 * VectorHire Domain Taxonomy Constants.
 * Matches backend schemas: EvidenceStatus, RequirementCategory, CandidateReviewStatus.
 */

export const EvidenceStatus = {
  EXPLICIT_SUPPORT: 'explicitly_supported',
  PARTIAL_OR_UNCERTAIN: 'partial_or_uncertain_support',
  UNVERIFIABLE_OR_CONTRADICTED: 'unverifiable_or_contradicted',
  MISSING_EVIDENCE: 'missing_evidence',
};

export const EvidenceStatusConfig = {
  [EvidenceStatus.EXPLICIT_SUPPORT]: {
    label: 'Explicit Support',
    shortLabel: 'Verified',
    badgeClass: 'bg-[#E8FBF5] text-[#0B5B44] border-[#A3F3DC] font-semibold',
    dotClass: 'bg-[#00D294] shadow-[0_0_6px_rgba(0,210,148,0.7)]',
    description: 'Verbatim physical passage verified; candidate directly performed or fulfilled the criterion.',
  },
  [EvidenceStatus.PARTIAL_OR_UNCERTAIN]: {
    label: 'Partial / Uncertain Support',
    shortLabel: 'Uncertain (γ Discount)',
    badgeClass: 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A] font-semibold',
    dotClass: 'bg-[#F59E0B] shadow-[0_0_6px_rgba(245,158,11,0.6)]',
    description: 'Related coursework, assisted capacity, or adjacent mention. Subject to uncertainty discount.',
  },
  [EvidenceStatus.UNVERIFIABLE_OR_CONTRADICTED]: {
    label: 'Unverifiable / Contradicted',
    shortLabel: 'Unverifiable',
    badgeClass: 'bg-[#FFF1F2] text-[#9F1239] border-[#FECDD3] font-semibold',
    dotClass: 'bg-[#E11D48] shadow-[0_0_6px_rgba(225,29,72,0.6)]',
    description: 'Fabricated quote, failed provenance check, or directly contradicted by context.',
  },
  [EvidenceStatus.MISSING_EVIDENCE]: {
    label: 'Missing Evidence',
    shortLabel: 'No Evidence Found',
    badgeClass: 'bg-[#F1F5F9] text-[#475569] border-[#E2E8F0] font-medium',
    dotClass: 'bg-[#94A3B8]',
    description: 'Absence of evidence in extracted text. Dignified absence; not proof of incompetence.',
  },
};

export const RequirementCategory = {
  MANDATORY_COMPETENCY: 'mandatory_competencies',
  LICENSE_REGISTRATION: 'license_registration',
  EXPERIENCE_TENURE: 'experience_tenure',
  EDUCATION: 'education',
  PREFERRED_COMPETENCY: 'preferred_competencies',
  // Aliases for compatibility
  REQUIRED_LICENSE: 'license_registration',
  RELEVANT_EXPERIENCE: 'experience_tenure',
};

export const RequirementCategoryConfig = {
  [RequirementCategory.MANDATORY_COMPETENCY]: {
    label: 'Mandatory Competency',
    defaultWeight: 0.40,
    badgeColor: 'bg-[#F0F9FF] text-[#0369A1] border-[#BAE6FD] font-semibold',
  },
  [RequirementCategory.LICENSE_REGISTRATION]: {
    label: 'Required License / Certification',
    defaultWeight: 0.30,
    badgeColor: 'bg-[#ECFEFF] text-[#0E7490] border-[#A5F3FC] font-semibold',
  },
  [RequirementCategory.EXPERIENCE_TENURE]: {
    label: 'Relevant Experience',
    defaultWeight: 0.20,
    badgeColor: 'bg-[#F5F3FF] text-[#6D28D9] border-[#DDD6FE] font-semibold',
  },
  [RequirementCategory.EDUCATION]: {
    label: 'Education',
    defaultWeight: 0.05,
    badgeColor: 'bg-[#E8FBF5] text-[#0B5B44] border-[#A3F3DC] font-semibold',
  },
  [RequirementCategory.PREFERRED_COMPETENCY]: {
    label: 'Preferred Competency',
    defaultWeight: 0.05,
    badgeColor: 'bg-[#F8FAFC] text-[#334155] border-[#CBD5E1] font-medium',
  },
};

export const CandidateReviewStatus = {
  SHORTLIST: 'Shortlist',
  REVIEW: 'Review',
  REJECT: 'Reject',
};

export const ReviewStatusConfig = {
  [CandidateReviewStatus.SHORTLIST]: {
    label: 'Recommended / Shortlist',
    badgeClass: 'bg-[#E8FBF5] text-[#0B5B44] border-[#A3F3DC] font-bold shadow-sm',
  },
  [CandidateReviewStatus.REVIEW]: {
    label: 'Recruiter Review Required',
    badgeClass: 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A] font-semibold shadow-sm',
  },
  [CandidateReviewStatus.REJECT]: {
    label: 'Declined / Re-evaluate',
    badgeClass: 'bg-[#FFF1F2] text-[#9F1239] border-[#FECDD3] font-semibold shadow-sm',
  },
};
