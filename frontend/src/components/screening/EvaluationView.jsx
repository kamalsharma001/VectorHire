import React from 'react';
import {
  FileText,
  ShieldCheck,
  Search,
  Sparkles,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

export function EvaluationView() {
  const {
    selectedFiles,
    jobSpec,
    evaluationPhase,
    isScreening = false,
    errorMessage,
    handleStartScreening,
    setActiveStep,
  } = useScreening();

  const fileCount = selectedFiles?.length || 0;
  const isFailed = !isScreening && Boolean(errorMessage);
  const isPending = !isFailed;

  // Friendly honest status text supported by genuine state
  const statusMessage =
    evaluationPhase && evaluationPhase !== 'idle'
      ? evaluationPhase
      : 'Evaluating candidate evidence…';

  return (
    <div className="max-w-3xl mx-auto space-y-7 py-4 motion-safe:animate-fade-in">
      {/* Editorial Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#F0F9FF] border border-[#BAE6FD] text-xs font-bold text-[#0369A1]">
          <span>Stage 04 • Candidate Evaluation in Progress</span>
        </div>

        <h1 className="font-sans text-3xl sm:text-4xl font-bold text-[#0F172A] tracking-tight">
          Evaluating candidate evidence
        </h1>

        <p className="text-xs text-[#475569] max-w-lg mx-auto leading-relaxed">
          Matching <strong className="text-[#0F172A]">{fileCount} resume{fileCount === 1 ? '' : 's'}</strong> against{' '}
          <strong className="text-[#0369A1]">{jobSpec?.job_title || 'Role'}</strong> requirements and validating supporting evidence. This may take a little while.
        </p>
      </div>

      {/* Elegant Single Processing Panel */}
      <div className="card-modern p-6 sm:p-8 space-y-6 border-[#BAE6FD]/80 shadow-[0_8px_30px_-6px_rgba(3,105,161,0.1)]">
        {/* Processing State Card */}
        <div className="p-6 sm:p-8 rounded-2xl bg-[#F0F9FF] border border-[#BAE6FD] space-y-5 text-center">
          {/* Subtle Animated Visual using solid cyan #06B6D4 and deep blue #0369A1 */}
          <div className="flex flex-col items-center justify-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-[#0369A1] flex items-center justify-center text-white shadow-sm">
              <Sparkles className="w-6 h-6 text-white" />
            </div>

            {/* Exactly three sequential animated dots directly below the icon */}
            <div className="flex items-center justify-center gap-2 pt-1 h-4" aria-hidden="true">
              <span
                style={
                  isPending
                    ? { animation: 'dotBounceWave 1.2s ease-in-out infinite 0s' }
                    : undefined
                }
                className={`inline-block w-2 h-2 rounded-full bg-[#0369A1] ${
                  isPending ? 'eval-dot-1' : ''
                }`}
              />
              <span
                style={
                  isPending
                    ? { animation: 'dotBounceWave 1.2s ease-in-out infinite 0.2s' }
                    : undefined
                }
                className={`inline-block w-2 h-2 rounded-full bg-[#06B6D4] ${
                  isPending ? 'eval-dot-2' : ''
                }`}
              />
              <span
                style={
                  isPending
                    ? { animation: 'dotBounceWave 1.2s ease-in-out infinite 0.4s' }
                    : undefined
                }
                className={`inline-block w-2 h-2 rounded-full bg-[#0369A1] ${
                  isPending ? 'eval-dot-3' : ''
                }`}
              />
            </div>
          </div>

          {/* Honest Single Fixed Message */}
          <div className="space-y-1.5 max-w-md mx-auto">
            <p className="text-sm font-bold text-[#0F172A] transition-colors">
              {isFailed
                ? 'Evaluation Encountered an Issue'
                : 'Evaluating and processing uploaded documents against the job requirements…'}
            </p>
            {isFailed && (
              <p className="text-xs text-[#E11D48] leading-relaxed">
                {errorMessage}
              </p>
            )}
          </div>

          {/* Failure & Retry Controls */}
          {isFailed && (
            <div className="pt-2 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setActiveStep('resumes')}
                className="btn-secondary text-xs py-2 px-3.5"
              >
                Back to resumes
              </button>
              <button
                type="button"
                onClick={handleStartScreening}
                className="btn-primary text-xs py-2 px-4 flex items-center gap-2"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Retry evaluation</span>
              </button>
            </div>
          )}
        </div>

        {/* Batch File Queue Roster */}
        {selectedFiles && selectedFiles.length > 0 && (
          <div className="pt-4 border-t border-[#E2E8F0] space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#64748B]">
                Batch Document Roster ({selectedFiles.length})
              </span>
              <span className="text-[11px] text-[#0369A1] font-mono font-semibold">
                Stateless In-Memory Verification
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedFiles.map((f, i) => (
                <span
                  key={i}
                  className="font-mono text-[11px] px-3 py-1 rounded-lg bg-[#F8FAFC] text-[#0F172A] border border-[#E2E8F0] hover:border-[#BAE6FD] hover:bg-[#F0F9FF] transition-colors truncate max-w-[220px] shadow-subtle"
                >
                  {f.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
