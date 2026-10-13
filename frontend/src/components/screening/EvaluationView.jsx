import React from 'react';
import {
  FileText,
  ShieldCheck,
  Search,
  Sparkles,
  Check,
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
    pipelineStages = [],
  } = useScreening();

  const fileCount = selectedFiles?.length || 0;
  const jobTitle = jobSpec?.job_title || 'Role';

  const stageIcons = [
    FileText,
    Layers,
    Search,
    ShieldCheck,
    Calculator,
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-3 px-2 sm:px-0 motion-safe:animate-fade-in">
      {/* A. Editorial Header (Solid colors, refined hierarchy, no gradients, no elapsed time) */}
      <div className="text-center space-y-2.5">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F0F9FF] border border-[#BAE6FD] text-xs font-semibold text-[#0369A1]">
          <span className="w-2 h-2 rounded-full bg-[#06B6D4]" />
          <span>Stage 04 • Candidate Evaluation in Progress</span>
        </div>

        <h1 className="font-sans text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
          Evaluating Candidate Evidence
        </h1>

        <p className="text-xs sm:text-sm text-[#475569] max-w-lg mx-auto leading-relaxed">
          Reviewing <strong className="text-[#0F172A]">{fileCount} resume{fileCount === 1 ? '' : 's'}</strong> against{' '}
          <strong className="text-[#0369A1]">{jobTitle}</strong> requirements.
        </p>
      </div>

      {/* Main Container Card (Solid background, subtle solid border, no gradients) */}
      <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5 sm:p-7 space-y-5 shadow-subtle">
        
        {/* Active Evaluation Banner (Solid pale blue bg, solid cyan border, rotating perimeter light) */}
        <div className="p-4 sm:p-4.5 rounded-xl bg-[#F0F9FF] border border-[#BAE6FD] flex items-center justify-between gap-3.5">
          <div className="flex items-center gap-3 min-w-0">
            {/* Active marker with rotating perimeter light indicator */}
            <div className="relative flex-shrink-0 w-8 h-8 flex items-center justify-center">
              <div className="absolute inset-0 active-marker-orbiter pointer-events-none" aria-hidden="true">
                <div className="w-2 h-2 rounded-full bg-[#06B6D4] absolute top-[-3px] left-1/2 -translate-x-1/2 shadow-sm" />
              </div>
              <div className="w-8 h-8 rounded-lg bg-[#0369A1] text-white border border-[#06B6D4] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
            </div>

            <div className="min-w-0">
              <h3 className="text-xs sm:text-sm font-bold text-[#0F172A] truncate">
                Evaluating candidate evidence
              </h3>
              <p className="text-[11px] sm:text-xs text-[#475569] mt-0.5 leading-relaxed">
                Matching resumes against the job requirements and validating supporting evidence.
              </p>
            </div>
          </div>

          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#ECFEFF] text-[#0369A1] border border-[#BAE6FD] flex-shrink-0">
            In progress
          </span>
        </div>

        {/* 5-Stage Verification Workflow (Visual architecture of the evaluation pipeline) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] uppercase tracking-wider font-bold text-[#64748B]">
              Evaluation Workflow Architecture
            </span>
            <span className="text-[10px] font-mono font-medium text-[#64748B]">
              5 Verification Stages
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2.5">
            {pipelineStages.map((phase, idx) => {
              const Icon = stageIcons[idx] || Sparkles;

              return (
                <div
                  key={phase.step}
                  className="p-3.5 sm:p-4 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] flex items-start gap-3 sm:gap-3.5 transition-colors"
                >
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]">
                    <Icon className="w-4.5 h-4.5 text-[#0369A1]" />
                  </div>

                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                        <span className="font-mono text-[11px] font-bold text-[#0369A1]">
                          {phase.step}
                        </span>
                        <h4 className="text-xs sm:text-sm font-semibold text-[#0F172A] truncate">
                          {phase.title}
                        </h4>
                      </div>

                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-white text-[#64748B] border border-[#E2E8F0] flex-shrink-0">
                        Pipeline Stage
                      </span>
                    </div>

                    <p className="text-[11px] sm:text-xs text-[#475569] mt-1 leading-relaxed">
                      {phase.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Batch Document Roster (Solid tags, subtle borders, no gradients) */}
        {selectedFiles && selectedFiles.length > 0 && (
          <div className="pt-3.5 border-t border-[#E2E8F0] space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#64748B]">
                Batch Document Roster ({selectedFiles.length})
              </span>
              <span className="text-[11px] text-[#0369A1] font-mono font-semibold">
                In-Memory Verification
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {selectedFiles.map((f, i) => (
                <span
                  key={i}
                  className="font-mono text-[11px] px-2.5 py-1 rounded-md bg-[#F8FAFC] text-[#0F172A] border border-[#E2E8F0] truncate max-w-[200px]"
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
