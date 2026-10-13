import React from 'react';
import {
  FileText,
  ShieldCheck,
  Search,
  Sparkles,
  CheckCircle2,
  Layers,
  Calculator,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

export function EvaluationView() {
  const {
    selectedFiles,
    jobSpec,
    evaluationPhase,
    currentStageIndex = 0,
    completedStages = [],
    isScreening = false,
    pipelineStages = [],
  } = useScreening();

  const fileCount = selectedFiles?.length || 0;

  const stageIcons = [
    FileText,
    Layers,
    Search,
    ShieldCheck,
    Calculator,
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-7 py-4 motion-safe:animate-fade-in">
      {/* Editorial Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#F0F9FF] border border-[#BAE6FD] text-xs font-bold text-[#0369A1]">
          <span>Stage 04 • Candidate Evaluation in Progress</span>
        </div>

        <h1 className="font-sans text-3xl sm:text-4xl font-bold text-[#0F172A] tracking-tight">
          Evaluating Candidate Evidence
        </h1>

        <p className="text-xs text-[#475569] max-w-lg mx-auto leading-relaxed">
          Screening <strong className="text-[#0F172A]">{fileCount} resume{fileCount === 1 ? '' : 's'}</strong> against{' '}
          <strong className="text-[#0369A1]">{jobSpec?.job_title || 'Role'}</strong> with zero hallucination tolerance.
        </p>
      </div>

      {/* Live Honest Pipeline Phase Notice with Ambient Pulsing Glow */}
      <div className="card-modern p-6 sm:p-8 space-y-6 border-[#BAE6FD]/80 shadow-[0_8px_30px_-6px_rgba(3,105,161,0.1)]">
        <div className="p-4 sm:p-5 rounded-2xl bg-[#F0F9FF] border border-[#BAE6FD] flex items-start gap-3.5 shadow-sm">
          <div className="w-3 h-3 rounded-full bg-[#06B6D4] animate-ping mt-1 flex-shrink-0" />
          <div className="space-y-0.5 min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#0369A1]">
                Active Pipeline Stage {Math.min(currentStageIndex + 1, 5)} of 5
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#ECFEFF] border border-[#BAE6FD] text-[10px] font-mono text-[#0369A1] font-bold shadow-subtle">
                <span className="w-1.5 h-1.5 rounded-full bg-[#06B6D4] animate-pulse" />
                In Progress
              </span>
            </div>
            <p className="text-xs font-bold text-[#0F172A] truncate">
              {evaluationPhase !== 'idle' ? evaluationPhase : 'Processing candidate documents...'}
            </p>
          </div>
        </div>

        {/* 5 Phased Stages with Connected Visual Step Flow */}
        <div className="space-y-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#64748B]">
              Deterministic Pipeline Architecture
            </span>
            <span className="text-[10px] font-mono font-semibold text-[#06B6D4]">
              5-Stage Verification Flow
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {pipelineStages.map((phase, idx) => {
              const Icon = stageIcons[idx] || Sparkles;
              const isCompleted = completedStages.includes(idx);
              const isActive = idx === currentStageIndex && isScreening && !isCompleted;
              const isPending = !isCompleted && !isActive;

              return (
                <div
                  key={phase.step}
                  className={`p-4 rounded-xl border transition-all duration-200 flex items-start gap-3.5 ${
                    isActive
                      ? 'bg-[#F0F9FF] border-[#06B6D4]'
                      : isCompleted
                      ? 'bg-white border-[#A3F3DC] shadow-subtle'
                      : 'bg-[#F8FAFC] border-[#E2E8F0] opacity-80'
                  }`}
                >
                  <div className="relative flex items-center justify-center w-10 h-10 flex-shrink-0">
                    {isActive && (
                      <>
                        {/* Dedicated 40px circular track */}
                        <div
                          className="absolute inset-0 rounded-full border border-[#BAE6FD]"
                          aria-hidden="true"
                        />
                        {/* Orbital light rotating continuously while evaluation is pending */}
                        <div
                          className={`absolute inset-0 rounded-full pointer-events-none ${
                            isScreening ? 'orbital-light-runner' : ''
                          }`}
                          aria-hidden="true"
                        >
                          <div className="w-2.5 h-2.5 rounded-full bg-[#06B6D4] absolute top-[-5px] left-1/2 -translate-x-1/2" />
                        </div>
                      </>
                    )}

                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm transition-transform ${
                        isActive
                          ? 'bg-[#0369A1] text-white'
                          : isCompleted
                          ? 'bg-[#00D294] text-white'
                          : 'bg-[#F1F5F9] text-[#94A3B8] border border-[#E2E8F0]'
                      }`}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="w-4.5 h-4.5 text-white" />
                      ) : (
                        <Icon className="w-4 h-4" />
                      )}
                    </div>
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-mono text-[11px] font-bold ${
                            isActive
                              ? 'text-[#0369A1]'
                              : isCompleted
                              ? 'text-[#047857]'
                              : 'text-[#94A3B8]'
                          }`}
                        >
                          {phase.step}
                        </span>
                        <h4
                          className={`text-xs font-bold transition-colors ${
                            isActive
                              ? 'text-[#0369A1]'
                              : isCompleted
                              ? 'text-[#0F172A]'
                              : 'text-[#64748B]'
                          }`}
                        >
                          {phase.title}
                        </h4>
                      </div>

                      {/* State Badge */}
                      {isCompleted ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#E8FBF5] text-[#047857] border border-[#A3F3DC]">
                          Completed
                        </span>
                      ) : isActive ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#ECFEFF] text-[#0369A1] border border-[#BAE6FD] animate-pulse">
                          In Progress
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#F1F5F9] text-[#64748B]">
                          Pending
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#475569] mt-1 leading-relaxed">
                      {phase.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
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
