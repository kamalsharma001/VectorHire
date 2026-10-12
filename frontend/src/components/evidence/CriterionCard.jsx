import React, { useState } from 'react';
import {
  FileCheck2,
  AlertTriangle,
  FileQuestion,
  ShieldCheck,
  Compass,
  ChevronDown,
  ChevronUp,
  MapPin,
  Sparkles,
} from 'lucide-react';
import {
  EvidenceStatus,
} from '../../constants/taxonomy';
import { EvidenceBadge, CategoryBadge, HardGateBadge } from '../common/Badge';

export function CriterionCard({ evaluation }) {
  const {
    requirement_name,
    category,
    status,
    is_hard_gate,
    evidence,
    achievement_ratio,
    points_awarded,
    max_points,
    within_category_weight,
    human_review_required,
    review_reason,
  } = evaluation;

  const [showFullQuote, setShowFullQuote] = useState(false);

  const provenance = evidence?.provenance;
  const isMissing = status === EvidenceStatus.MISSING_EVIDENCE || status === 'not_mentioned';
  const isExplicit = status === EvidenceStatus.EXPLICIT_SUPPORT || status === 'explicitly_supported';
  const isUncertain = status === EvidenceStatus.PARTIAL_OR_UNCERTAIN || status === 'relevant_but_uncertain';

  const quoteText = provenance?.exact_span_quote || '';
  const isLongQuote = quoteText.length > 220;

  const getImportanceLabel = (cat, isHard) => {
    if (isHard) return 'Hard Gate';
    if (cat === 'mandatory_competency') return 'Core Mandatory';
    if (cat === 'preferred_competency') return 'Preferred';
    if (cat === 'license_registration') return 'License Required';
    if (cat === 'experience_tenure') return 'Tenure Requirement';
    if (cat === 'education') return 'Education Degree';
    return 'Evaluation Criterion';
  };

  return (
    <div
      className={`card-modern p-5 space-y-3.5 transition-all duration-200 hover:shadow-card-hover ${
        human_review_required
          ? 'border-amber-300 bg-amber-50/15'
          : isExplicit
          ? 'border-[#A3F3DC] bg-white'
          : isMissing
          ? 'border-[#E2E8F0] bg-[#F8FAFC]'
          : 'border-[#E2E8F0] bg-white'
      }`}
    >
      {/* Criterion Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]">
              {getImportanceLabel(category, is_hard_gate)}
            </span>
            <CategoryBadge category={category} />
            <HardGateBadge isHardGate={is_hard_gate} passed={isExplicit} />
            <EvidenceBadge status={status} />
          </div>
          <h4 className="font-bold text-[#0F172A] text-sm tracking-tight pt-0.5">
            {requirement_name}
          </h4>
        </div>

        {/* Score & Points Awarded */}
        <div className="text-right sm:self-start flex-shrink-0 bg-[#F8FAFC] px-3.5 py-1.5 rounded-xl border border-[#E2E8F0] shadow-subtle">
          <div className="font-mono font-bold text-xs text-[#0369A1]">
            {points_awarded.toFixed(2)} / {max_points.toFixed(2)} pts
          </div>
          <div className="text-[10px] text-[#64748B] font-mono mt-0.5">
            Ratio: {(achievement_ratio * 100).toFixed(0)}% • Weight: {(within_category_weight * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Review Reason Alert if flag raised */}
      {human_review_required && review_reason && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5 shadow-subtle">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="font-bold">Recruiter Review Alert:</strong> {review_reason}
          </div>
        </div>
      )}

      {/* Two-Stage Evidence Provenance & Contextual Support Section */}
      {!isMissing && evidence ? (
        <div className="space-y-3 pt-1">
          {/* Stage 1: Deterministic Verbatim Provenance Box */}
          <div className="rounded-xl border border-[#BAE6FD]/80 bg-[#F0F9FF]/60 p-3.5 space-y-2.5 text-xs">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 font-bold text-[#0369A1]">
                <ShieldCheck className="w-4 h-4 text-[#0369A1]" />
                <span>Stage 1: Deterministic Source Provenance</span>
              </div>
              <div className="flex items-center gap-2 font-mono text-[10px] text-[#475569] flex-wrap">
                {provenance?.source_section && (
                  <span className="px-2 py-0.5 rounded-md bg-white border border-[#BAE6FD] font-semibold text-[#0369A1] shadow-subtle">
                    Section: {provenance.source_section}
                  </span>
                )}
                {provenance?.source_page && (
                  <span className="px-2 py-0.5 rounded-md bg-white border border-[#BAE6FD] font-semibold text-[#0369A1] shadow-subtle">
                    PDF Page {provenance.source_page}
                  </span>
                )}
                {provenance?.character_start !== null && provenance?.character_end !== null && (
                  <span className="px-2 py-0.5 rounded-md bg-white border border-[#E2E8F0] shadow-subtle">
                    Offsets: {provenance?.character_start}–{provenance?.character_end}
                  </span>
                )}
                {provenance?.exact_match ? (
                  <span className="text-[#0B5B44] font-bold bg-[#E8FBF5] px-2 py-0.5 rounded-md border border-[#A3F3DC]">
                    Verbatim Verified
                  </span>
                ) : provenance?.fuzzy_recovered ? (
                  <span className="text-[#0369A1] font-semibold bg-[#F0F9FF] px-2 py-0.5 rounded-md border border-[#BAE6FD]">
                    Normalized Match
                  </span>
                ) : null}
              </div>
            </div>

            {/* Verbatim Excerpt Quote */}
            {quoteText ? (
              <div className="space-y-1.5">
                <blockquote className="border-l-3 border-[#0369A1] pl-3.5 py-2 font-mono text-xs text-[#0F172A] bg-white rounded-r-xl border border-l-0 border-[#BAE6FD]/60 italic leading-relaxed shadow-subtle">
                  "{isLongQuote && !showFullQuote ? `${quoteText.slice(0, 220)}...` : quoteText}"
                </blockquote>

                {isLongQuote && (
                  <button
                    onClick={() => setShowFullQuote(!showFullQuote)}
                    className="text-[11px] font-semibold text-[#0369A1] hover:text-[#0284C7] flex items-center gap-1 pl-1 transition-colors"
                  >
                    {showFullQuote ? (
                      <>
                        <ChevronUp className="w-3.5 h-3.5" />
                        <span>Show concise excerpt</span>
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3.5 h-3.5" />
                        <span>View full surrounding context ({quoteText.length} chars)</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            ) : (
              <div className="text-[11px] text-[#64748B] italic">
                Exact text span verified against candidate resume text stream.
              </div>
            )}
          </div>

          {/* Stage 2: Contextual Support Verification Box */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5 space-y-2 text-xs shadow-subtle">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 font-bold text-[#0F172A]">
                <Compass className="w-4 h-4 text-[#06B6D4]" />
                <span>Stage 2: Contextual Support Verification</span>
              </div>
              <span
                className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border shadow-subtle ${
                  evidence.is_direct_execution
                    ? 'bg-[#E8FBF5] text-[#0B5B44] border-[#A3F3DC]'
                    : 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]'
                }`}
              >
                {evidence.is_direct_execution ? 'Direct Responsibility' : 'Assisted / Incidental Role'}
              </span>
            </div>

            {/* Recruiter "Why this matters" Assessment */}
            <div className="pt-0.5">
              <span className="text-[10px] uppercase tracking-wider font-bold text-[#0369A1] block mb-0.5">
                Why this matters:
              </span>
              <p className="text-[#334155] leading-relaxed">
                {evidence.match_rationale}
              </p>
            </div>

            {evidence.verification_notes && (
              <div className="text-[11px] text-[#64748B] italic pt-0.5 font-mono">
                Notes: {evidence.verification_notes}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Missing Evidence Dignified Absence Callout */
        <div className="rounded-xl border border-dashed border-[#CBD5E1] bg-[#F8FAFC] p-4 text-xs text-[#64748B] flex items-start gap-3 shadow-subtle">
          <FileQuestion className="w-5 h-5 text-[#94A3B8] flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="text-[#0F172A] font-bold block">
              Dignified Absence of Evidence
            </strong>
            <p className="text-[#475569] leading-relaxed">
              No locatable passage in the candidate's extracted document text supports this requirement. Absence of documented evidence is not interpreted as proof of incapacity, but receives 0.00 pts under the deterministic rubric.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
