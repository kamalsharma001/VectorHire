import React, { useState, useEffect } from 'react';
import {
  X,
  Award,
  ShieldCheck,
  AlertTriangle,
  MessageSquare,
  FileText,
  Calculator,
  ChevronRight,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileQuestion,
  XCircle,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import { ScoreBar } from '../common/ScoreBar';
import { HardGateBadge, ReviewStatusBadge } from '../common/Badge';
import { CriterionCard } from './CriterionCard';
import { QuestionGenerator } from './QuestionGenerator';
import { RequirementCategoryConfig } from '../../constants/taxonomy';

export function EvidenceDrawer() {
  const {
    inspectedCandidateId,
    setInspectedCandidateId,
    screeningResult,
    jobSpec,
  } = useScreening();

  const [activeTab, setActiveTab] = useState('evidence'); // 'evidence' | 'questions'

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setInspectedCandidateId(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setInspectedCandidateId]);

  if (!inspectedCandidateId || !screeningResult) return null;

  const candidate = screeningResult.ranked_candidates.find(
    (c) => c.candidate_id === inspectedCandidateId
  );
  const scorecard = screeningResult.scorecards[inspectedCandidateId];

  if (!candidate || !scorecard) return null;

  const evaluations = scorecard.evaluations || [];
  const categoryScores = scorecard.category_scores || {};
  const effectiveWeights = scorecard.effective_category_weights || {};

  const supportedCount = evaluations.filter(
    (e) => e.status === 'EXPLICIT_SUPPORT' || e.status === 'explicitly_supported'
  ).length;
  const uncertainCount = evaluations.filter(
    (e) => e.status === 'PARTIAL_OR_UNCERTAIN' || e.status === 'relevant_but_uncertain'
  ).length;
  const missingCount = evaluations.filter(
    (e) => e.status === 'MISSING_EVIDENCE' || e.status === 'not_mentioned'
  ).length;
  const contradictedCount = evaluations.filter(
    (e) => e.status === 'CONTRADICTED' || e.status === 'contradicted'
  ).length;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-3xl bg-white h-full shadow-drawer flex flex-col border-l border-[#BAE6FD]/80 animate-in slide-in-from-right duration-300">
        {/* Drawer Header with Vibrant Oceanic Gradient */}
        <div className="p-6 sm:p-7 bg-gradient-to-r from-[#075985] via-[#0369A1] to-[#0C4A6E] text-white flex-shrink-0 flex items-start justify-between gap-4 shadow-sm">
          <div className="space-y-2.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs uppercase px-3 py-1 rounded-full bg-white/20 text-white font-bold border border-white/25 shadow-sm">
                Rank #{candidate.rank}
              </span>
              <HardGateBadge isHardGate={true} passed={candidate.hard_gate_passed} />
              <ReviewStatusBadge status={candidate.recruiter_status} />
            </div>

            <h2 className="font-sans text-xl sm:text-2xl font-bold text-white tracking-tight truncate">
              {candidate.candidate_name}
            </h2>

            <div className="text-xs text-white/85 font-mono truncate flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-[#00D294]" />
              <span>{candidate.filename}</span>
            </div>
          </div>

          <button
            onClick={() => setInspectedCandidateId(null)}
            className="text-white/80 hover:text-white p-2 rounded-xl hover:bg-white/15 transition-all active:scale-[0.96]"
            title="Close drawer (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Score & Formula Header Bar */}
        <div className="p-5 sm:p-6 bg-[#F8FAFC] border-b border-[#E2E8F0] flex-shrink-0 space-y-3.5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center justify-between text-xs font-bold mb-2">
                <span className="text-[#0F172A]">Deterministic Rubric Composite Score:</span>
                <span className="font-mono text-[#0369A1] text-base font-bold">
                  {scorecard.total_score.toFixed(2)}%
                </span>
              </div>
              <ScoreBar score={scorecard.total_score} showLabel={false} size="lg" />
            </div>
          </div>

          {/* Mathematical Formula Trace */}
          {scorecard.formula_explanation && (
            <div className="p-3.5 rounded-xl bg-white border border-[#BAE6FD]/80 text-xs text-[#0F172A] font-mono flex items-start gap-2.5 shadow-subtle">
              <Calculator className="w-4 h-4 text-[#0369A1] flex-shrink-0 mt-0.5" />
              <div className="leading-relaxed truncate" title={scorecard.formula_explanation}>
                <span className="font-bold text-[#0369A1]">Trace:</span> {scorecard.formula_explanation}
              </div>
            </div>
          )}

          {/* Candidate-Level Evidence Summary Tally */}
          <div className="pt-2 border-t border-[#E2E8F0] flex items-center justify-between flex-wrap gap-2.5">
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#64748B]">
              Evidence Tally:
            </span>
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#E8FBF5] text-[#0B5B44] border border-[#A3F3DC] font-bold shadow-subtle">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#00D294]" />
                <span>{supportedCount} Supported</span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#FFFBEB] text-[#92400E] border border-[#FDE68A] font-bold shadow-subtle">
                <AlertCircle className="w-3.5 h-3.5 text-[#F59E0B]" />
                <span>{uncertainCount} Uncertain</span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#F8FAFC] text-[#475569] border border-[#CBD5E1] font-bold shadow-subtle">
                <FileQuestion className="w-3.5 h-3.5 text-[#94A3B8]" />
                <span>{missingCount} Missing</span>
              </span>
              {contradictedCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#FFF1F2] text-[#9F1239] border border-[#FECDD3] font-bold shadow-subtle">
                  <XCircle className="w-3.5 h-3.5 text-[#E11D48]" />
                  <span>{contradictedCount} Contradicted</span>
                </span>
              )}
            </div>
          </div>

          {/* Review Flags Alert if present */}
          {candidate.review_flags && candidate.review_flags.length > 0 && (
            <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-900 text-xs space-y-1.5 shadow-sm">
              <div className="flex items-center gap-2 font-bold text-amber-900">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>Human Review Flags ({candidate.review_flags.length}):</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 pl-1 text-[11px] text-amber-800">
                {candidate.review_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Tab Controls with AI Violet Accent */}
        <div className="flex items-center px-6 border-b border-[#E2E8F0] bg-white flex-shrink-0 text-xs">
          <button
            onClick={() => setActiveTab('evidence')}
            className={`py-3.5 px-4 font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'evidence'
                ? 'border-[#0369A1] text-[#0369A1]'
                : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-[#0369A1]" />
            <span>Criteria & Verified Evidence ({evaluations.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('questions')}
            className={`py-3.5 px-4 font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'questions'
                ? 'border-[#8B5CF6] text-[#8B5CF6]'
                : 'border-transparent text-[#64748B] hover:text-[#8B5CF6]'
            }`}
          >
            <MessageSquare className="w-4 h-4 text-[#8B5CF6]" />
            <span>Interview Questions</span>
          </button>
        </div>

        {/* Tab Content (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-[#F8FAFC]">
          {activeTab === 'evidence' ? (
            <div className="space-y-4">
              {evaluations.length > 0 ? (
                evaluations.map((ev) => (
                  <CriterionCard key={ev.requirement_id} evaluation={ev} />
                ))
              ) : (
                <div className="p-8 text-center text-xs text-[#64748B]">
                  No criteria evaluations available for this candidate.
                </div>
              )}
            </div>
          ) : (
            <QuestionGenerator
              candidate={candidate}
              scorecard={scorecard}
              jobSpec={jobSpec}
            />
          )}
        </div>
      </div>
    </div>
  );
}
