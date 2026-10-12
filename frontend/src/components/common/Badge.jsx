import React from 'react';
import {
  EvidenceStatusConfig,
  RequirementCategoryConfig,
  ReviewStatusConfig,
} from '../../constants/taxonomy';

export function EvidenceBadge({ status, showDescription = false }) {
  const config = EvidenceStatusConfig[status] || {
    label: status || 'Unknown',
    badgeClass: 'bg-[#F1F5F9] text-[#64748B] border-[#E2E8F0]',
    dotClass: 'bg-[#94A3B8]',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-all duration-200 ${config.badgeClass}`}
      title={showDescription ? config.description : undefined}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
      <span>{config.label}</span>
    </span>
  );
}

export function CategoryBadge({ category }) {
  const config = RequirementCategoryConfig[category] || {
    label: category || 'Category',
    badgeColor: 'bg-[#F8FAFC] text-[#0F172A] border-[#E2E8F0]',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-semibold border shadow-subtle ${config.badgeColor}`}
    >
      {config.label}
    </span>
  );
}

export function HardGateBadge({ isHardGate, passed = null }) {
  if (!isHardGate) return null;

  if (passed === false) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#FFF1F2] text-[#9F1239] border border-[#FECDD3] shadow-[0_0_8px_rgba(225,29,72,0.15)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[#E11D48] animate-pulse" />
        Gate Flagged
      </span>
    );
  }

  if (passed === true) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#E8FBF5] text-[#0B5B44] border border-[#A3F3DC] shadow-[0_0_8px_rgba(0,210,148,0.15)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[#00D294]" />
        Gate Verified
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#F0F9FF] text-[#0369A1] border border-[#BAE6FD] shadow-subtle">
      Mandatory Gate
    </span>
  );
}

export function ReviewStatusBadge({ status }) {
  const config = ReviewStatusConfig[status] || {
    label: status || 'Review',
    badgeClass: 'bg-[#F1F5F9] text-[#64748B] border-[#E2E8F0]',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.badgeClass}`}
    >
      {config.label}
    </span>
  );
}
