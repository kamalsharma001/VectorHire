import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  Download,
  FileSpreadsheet,
  ArrowUpDown,
  ExternalLink,
  Award,
  CheckCircle2,
  AlertTriangle,
  FileX2,
  ChevronRight,
  ShieldAlert,
  ArrowLeft,
  Sparkles,
  Trophy,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import { ScoreBar } from '../common/ScoreBar';
import { HardGateBadge, ReviewStatusBadge } from '../common/Badge';
import { IngestionFailures } from './IngestionFailures';

export function ComparisonMatrix() {
  const {
    screeningResult,
    jobSpec,
    setInspectedCandidateId,
    setActiveStep,
  } = useScreening();

  const [searchQuery, setSearchQuery] = useState('');
  const [filterGate, setFilterGate] = useState('all'); // 'all' | 'passed' | 'flagged'
  const [sortBy, setSortBy] = useState('rank'); // 'rank' | 'score_desc' | 'score_asc' | 'name'

  const candidates = screeningResult?.ranked_candidates || [];
  const scorecards = screeningResult?.scorecards || {};
  const validationErrors = screeningResult?.validation_errors || [];

  // Summary Metrics
  const totalSubmitted = screeningResult?.total_submitted || candidates.length + validationErrors.length;
  const totalEvaluated = candidates.length;
  const passedGatesCount = candidates.filter((c) => c.hard_gate_passed).length;
  const topScore = candidates.length > 0 ? Math.max(...candidates.map((c) => c.total_score)) : 0;

  // Filtered & Sorted Candidates
  const filteredCandidates = useMemo(() => {
    return candidates
      .filter((cand) => {
        const matchesSearch =
          cand.candidate_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          cand.filename.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesGate =
          filterGate === 'all'
            ? true
            : filterGate === 'passed'
            ? cand.hard_gate_passed
            : !cand.hard_gate_passed;

        return matchesSearch && matchesGate;
      })
      .sort((a, b) => {
        if (sortBy === 'rank') return a.rank - b.rank;
        if (sortBy === 'score_desc') return b.total_score - a.total_score;
        if (sortBy === 'score_asc') return a.total_score - b.total_score;
        if (sortBy === 'name') return a.candidate_name.localeCompare(b.candidate_name);
        return 0;
      });
  }, [candidates, searchQuery, filterGate, sortBy]);

  // CSV Export
  const handleExportCSV = () => {
    if (!candidates.length) return;

    const headers = [
      'Rank',
      'Candidate Name',
      'Filename',
      'Total Score (%)',
      'Hard Gate Passed',
      'Review Flags Count',
      'Review Flags Summary',
      'Recruiter Status',
      'Formula Explanation',
    ];

    const rows = candidates.map((c) => {
      const card = scorecards[c.candidate_id];
      return [
        c.rank,
        `"${c.candidate_name.replace(/"/g, '""')}"`,
        `"${c.filename.replace(/"/g, '""')}"`,
        c.total_score.toFixed(2),
        c.hard_gate_passed ? 'YES' : 'NO',
        (c.review_flags || []).length,
        `"${(c.review_flags || []).join('; ').replace(/"/g, '""')}"`,
        `"${c.recruiter_status || 'Review'}"`,
        `"${(card?.formula_explanation || '').replace(/"/g, '""')}"`,
      ];
    });

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute(
      'download',
      `VectorHire_Screening_${(screeningResult?.job_title || 'Batch').replace(/\s+/g, '_')}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // JSON Export
  const handleExportJSON = () => {
    if (!screeningResult) return;
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(screeningResult, null, 2));
    const link = document.createElement('a');
    link.setAttribute('href', dataStr);
    link.setAttribute(
      'download',
      `VectorHire_Screening_${(screeningResult?.job_title || 'Session').replace(/\s+/g, '_')}.json`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto motion-safe:animate-fade-in">
      {/* Editorial Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-gradient-to-r from-[#F0F9FF] to-[#ECFEFF] text-[#0369A1] border border-[#BAE6FD] shadow-subtle">
              Stage 05
            </span>
            <span className="text-xs font-semibold text-[#475569]">
              Rubric v{screeningResult?.rubric_version || 1} • {totalEvaluated} Candidates Ranked
            </span>
          </div>
          <h1 className="font-sans text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
            Candidate Evaluation Results
          </h1>
          <p className="text-xs text-[#475569] mt-1 leading-relaxed">
            Target Role: <strong className="text-[#0369A1] font-bold">{screeningResult?.job_title || jobSpec?.job_title}</strong> •{' '}
            Deterministic scores computed exclusively from verified textual evidence.
          </p>
        </div>

        {/* Top Actions Bar */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => setActiveStep('resumes')}
            className="btn-secondary text-xs py-2 px-3.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Upload More</span>
          </button>
          <button
            onClick={handleExportCSV}
            disabled={!candidates.length}
            className="btn-secondary text-xs py-2 px-3.5 hover:border-[#0369A1] hover:text-[#0369A1]"
            title="Download CSV report"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-[#0369A1]" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={handleExportJSON}
            disabled={!screeningResult}
            className="btn-secondary text-xs py-2 px-3.5 hover:border-[#06B6D4] hover:text-[#0E7490]"
            title="Download full JSON scorecard payload"
          >
            <Download className="w-3.5 h-3.5 text-[#06B6D4]" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Editorial Summary Strip with Rich Visual Metrics */}
      <div className="card-modern p-5 sm:p-6 bg-white border-[#BAE6FD]/60 shadow-[0_4px_20px_-4px_rgba(7,89,133,0.06)] flex flex-col sm:flex-row sm:items-center justify-between gap-5">
        <div className="flex items-center gap-6 divide-x divide-[#E2E8F0] text-xs">
          <div className="space-y-0.5 pr-2">
            <span className="text-[#64748B] text-[11px] font-semibold uppercase tracking-wider block">Evaluated</span>
            <span className="font-mono text-xl font-bold text-[#0F172A]">
              {totalEvaluated} <span className="text-xs font-normal text-[#64748B]">/ {totalSubmitted}</span>
            </span>
          </div>

          <div className="space-y-0.5 pl-6 pr-2">
            <span className="text-[#64748B] text-[11px] font-semibold uppercase tracking-wider block">Hard Gates Met</span>
            <span className="font-mono text-xl font-bold text-[#0B5B44]">
              {passedGatesCount} <span className="text-xs font-semibold text-[#00D294]">passed</span>
            </span>
          </div>

          <div className="space-y-0.5 pl-6">
            <span className="text-[#64748B] text-[11px] font-semibold uppercase tracking-wider block">Top Composite</span>
            <span className="font-mono text-xl font-bold text-[#0369A1] flex items-center gap-1.5">
              <Trophy className="w-4 h-4 text-amber-500" />
              {topScore.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="text-[11px] text-[#475569] max-w-xs leading-relaxed hidden md:block text-right bg-[#F8FAFC] p-3 rounded-xl border border-[#E2E8F0]">
          Absence of evidence is never scored as proof of incapability; γ discount applied to partial evidence.
        </div>
      </div>

      {/* Partial Batch Notice */}
      {validationErrors.length > 0 && candidates.length > 0 && (
        <div className="flex items-start gap-3.5 p-4 rounded-xl border border-amber-200 bg-amber-50/70 text-amber-900 text-xs shadow-sm">
          <AlertTriangle className="w-4.5 h-4.5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <span className="font-bold block mb-0.5">Partial Batch Evaluation Notice</span>
            <span className="leading-relaxed">
              {candidates.length} of {totalSubmitted} candidate resumes were successfully evaluated and ranked below.{' '}
              {validationErrors.length} document{validationErrors.length > 1 ? 's were' : ' was'} excluded due to validation or processing issues.
            </span>
          </div>
        </div>
      )}

      {/* Excluded Documents (Validation Gate / Ingestion Failures) */}
      {validationErrors.length > 0 && (
        <IngestionFailures failures={validationErrors} />
      )}

      {/* Table Filters & Search Bar */}
      <div className="card-modern p-4 bg-white border-[#BAE6FD]/60 shadow-[0_2px_12px_-2px_rgba(7,89,133,0.05)] flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 text-xs">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-2.5 text-[#64748B]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search candidate name or filename..."
              className="w-full pl-10 pr-3.5 py-2 border border-[#E2E8F0] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1] text-[#0F172A] shadow-subtle"
            />
          </div>
        </div>

        <div className="flex items-center gap-3.5 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-[#64748B] font-semibold">Hard Gates:</span>
            <select
              value={filterGate}
              onChange={(e) => setFilterGate(e.target.value)}
              className="px-3 py-2 border border-[#E2E8F0] rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1] text-[#0F172A] font-medium shadow-subtle"
            >
              <option value="all">All ({candidates.length})</option>
              <option value="passed">Gate Passed Only ({passedGatesCount})</option>
              <option value="flagged">Review Flagged ({candidates.length - passedGatesCount})</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#64748B] font-semibold">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 border border-[#E2E8F0] rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1] text-[#0F172A] font-medium shadow-subtle"
            >
              <option value="rank">Rank (#1 First)</option>
              <option value="score_desc">Score (Highest First)</option>
              <option value="score_asc">Score (Lowest First)</option>
              <option value="name">Candidate Name</option>
            </select>
          </div>
        </div>
      </div>

      {/* Comparison Table with Hover Micro-Lift & Ranked Badges */}
      <div className="card-modern overflow-hidden border-[#BAE6FD]/60 shadow-[0_4px_24px_-4px_rgba(7,89,133,0.08)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F8FAFC] text-[#64748B] uppercase text-[11px] font-bold border-b border-[#E2E8F0] select-none">
              <tr>
                <th className="py-3.5 px-4 w-16">Rank</th>
                <th className="py-3.5 px-4">Candidate & File</th>
                <th className="py-3.5 px-4 w-60">Composite Score</th>
                <th className="py-3.5 px-4">Hard Gate Status</th>
                <th className="py-3.5 px-4">Review Flags</th>
                <th className="py-3.5 px-4">Recruiter Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {filteredCandidates.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-[#64748B] font-medium">
                    No candidates match the selected filters or search query.
                  </td>
                </tr>
              ) : (
                filteredCandidates.map((cand) => {
                  const card = scorecards[cand.candidate_id];
                  const isTopMatch = cand.rank === 1;

                  return (
                    <tr
                      key={cand.candidate_id}
                      className={`transition-colors group cursor-pointer ${
                        isTopMatch
                          ? 'bg-gradient-to-r from-[#F0F9FF]/60 to-transparent hover:bg-[#F0F9FF]'
                          : 'hover:bg-[#F0F9FF]/40'
                      }`}
                      onClick={() => setInspectedCandidateId(cand.candidate_id)}
                    >
                      {/* Rank Badge */}
                      <td className="py-4 px-4 font-mono font-bold text-[#0F172A]">
                        <span
                          className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs transition-transform group-hover:scale-105 ${
                            isTopMatch
                              ? 'bg-gradient-to-br from-[#0284C7] to-[#075985] text-white shadow-glow-cyan font-bold ring-2 ring-[#06B6D4]/30'
                              : cand.rank <= 3
                              ? 'bg-[#F1F5F9] text-[#0F172A] border border-[#CBD5E1] font-bold'
                              : 'bg-[#F8FAFC] text-[#64748B]'
                          }`}
                        >
                          #{cand.rank}
                        </span>
                      </td>

                      {/* Candidate Name & Filename */}
                      <td className="py-4 px-4 min-w-[200px]">
                        <div className="font-bold text-[#0F172A] group-hover:text-[#0369A1] transition-colors text-sm flex items-center gap-1.5">
                          <span>{cand.candidate_name}</span>
                          {isTopMatch && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#E8FBF5] text-[#0B5B44] border border-[#A3F3DC] font-bold">
                              Top Match
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] font-mono text-[#64748B] truncate max-w-xs mt-0.5">
                          {cand.filename}
                        </div>
                      </td>

                      {/* Deterministic Score with Vibrant Dual-Tone Bar */}
                      <td className="py-4 px-4">
                        <ScoreBar score={cand.total_score} />
                      </td>

                      {/* Hard Gate */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <HardGateBadge isHardGate={true} passed={cand.hard_gate_passed} />
                      </td>

                      {/* Review Flags */}
                      <td className="py-4 px-4 max-w-xs">
                        {cand.review_flags && cand.review_flags.length > 0 ? (
                          <div className="flex flex-col gap-1">
                            {cand.review_flags.slice(0, 2).map((flag, fIdx) => (
                              <span
                                key={fIdx}
                                className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-lg bg-amber-50 text-amber-900 border border-amber-200 truncate shadow-subtle"
                                title={flag}
                              >
                                <AlertTriangle className="w-3 h-3 text-amber-600 flex-shrink-0" />
                                <span className="truncate">{flag}</span>
                              </span>
                            ))}
                            {cand.review_flags.length > 2 && (
                              <span className="text-[10px] text-[#64748B] font-semibold pl-1">
                                +{cand.review_flags.length - 2} more review notes
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[11px] text-[#0B5B44] font-bold flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-[#00D294]" />
                            Clean Profile
                          </span>
                        )}
                      </td>

                      {/* Recruiter Status */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <ReviewStatusBadge status={cand.recruiter_status} />
                      </td>

                      {/* Actions */}
                      <td className="py-4 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setInspectedCandidateId(cand.candidate_id);
                          }}
                          className="btn-secondary text-xs py-1.5 px-3 group-hover:bg-[#0369A1] group-hover:text-white group-hover:border-[#0369A1] group-hover:shadow-glow-blue transition-all"
                        >
                          <span>Inspect Evidence</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
