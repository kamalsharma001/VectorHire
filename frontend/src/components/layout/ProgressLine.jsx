import React from 'react';
import { Check } from 'lucide-react';
import { useScreening, STAGES } from '../../context/ScreeningContext';

export function ProgressLine() {
  const { activeStep, setActiveStep, canNavigateTo } = useScreening();

  const currentStageIndex = STAGES.findIndex((s) => s.id === activeStep);
  const activeStage = STAGES[currentStageIndex] || STAGES[0];
  const progressPercent = ((currentStageIndex + 1) / STAGES.length) * 100;

  return (
    <div className="bg-white/90 backdrop-blur-md border-b border-[#E2E8F0] select-none sticky top-14 z-20 transition-all shadow-[0_1px_2px_rgba(15,23,42,0.02)]">
      {/* Desktop / Tablet: Connected 5-stage line with vibrant animated transitions */}
      <div className="hidden sm:block max-w-5xl mx-auto px-6 py-3.5">
        <nav aria-label="Screening Stages" className="flex items-center justify-between">
          {STAGES.map((stage, idx) => {
            const isCompleted = idx < currentStageIndex;
            const isActive = idx === currentStageIndex;
            const isClickable = canNavigateTo(stage.id) && !isActive;

            return (
              <React.Fragment key={stage.id}>
                {/* Connecting Line between steps with smooth gradient */}
                {idx > 0 && (
                  <div className="flex-1 mx-3 h-[2.5px] transition-colors duration-300 relative rounded-full overflow-hidden bg-[#E2E8F0]">
                    <div
                      className={`h-full transition-all duration-500 ease-out rounded-full ${
                        idx < currentStageIndex
                          ? 'bg-gradient-to-r from-[#00D294] to-[#06B6D4] w-full'
                          : idx === currentStageIndex
                          ? 'bg-gradient-to-r from-[#06B6D4] to-[#0369A1] w-full'
                          : 'w-0'
                      }`}
                    />
                  </div>
                )}

                {/* Step Item */}
                <button
                  type="button"
                  onClick={() => isClickable && setActiveStep(stage.id)}
                  disabled={!isClickable}
                  aria-current={isActive ? 'step' : undefined}
                  className={`flex items-center gap-2.5 transition-all text-left group ${
                    isClickable ? 'cursor-pointer' : 'cursor-default'
                  }`}
                >
                  {/* Step Number / Icon Badge with Vibrant AI Glow */}
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-mono font-bold transition-all duration-200 ${
                      isActive
                        ? 'bg-gradient-to-br from-[#0284C7] via-[#0369A1] to-[#075985] text-white shadow-glow-cyan ring-4 ring-[#06B6D4]/25 scale-105'
                        : isCompleted
                        ? 'bg-gradient-to-br from-[#00D294] to-[#00B882] text-[#0B5B44] shadow-sm group-hover:scale-105 group-hover:shadow-glow-mint'
                        : 'border border-[#E2E8F0] bg-[#F8FAFC] text-[#94A3B8] group-hover:border-[#CBD5E1]'
                    }`}
                  >
                    {isCompleted ? (
                      <Check className="w-3.5 h-3.5 stroke-[3] text-[#0B5B44]" />
                    ) : (
                      <span>0{stage.step}</span>
                    )}
                  </div>

                  {/* Stage Label */}
                  <div className="flex flex-col">
                    <span
                      className={`text-xs tracking-tight transition-colors ${
                        isActive
                          ? 'font-bold text-[#0369A1]'
                          : isCompleted
                          ? 'font-semibold text-[#0F172A] group-hover:text-[#0369A1]'
                          : 'font-normal text-[#94A3B8]'
                      }`}
                    >
                      {stage.label}
                    </span>
                  </div>
                </button>
              </React.Fragment>
            );
          })}
        </nav>
      </div>

      {/* Mobile: Compact Progress Bar (375px viewport optimized) */}
      <div className="sm:hidden px-4 py-2.5 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded-md bg-gradient-to-r from-[#0369A1] to-[#06B6D4] text-white shadow-sm">
              0{activeStage.step} / 0{STAGES.length}
            </span>
            <span className="font-bold text-[#0F172A] truncate max-w-[200px]">
              {activeStage.label}
            </span>
          </div>

          {currentStageIndex > 0 && canNavigateTo(STAGES[currentStageIndex - 1]?.id) && (
            <button
              onClick={() => setActiveStep(STAGES[currentStageIndex - 1].id)}
              className="text-[11px] font-semibold text-[#0369A1] hover:underline"
            >
              Previous
            </button>
          )}
        </div>

        {/* Dynamic Gradient Progress Bar */}
        <div className="w-full h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#0369A1] via-[#06B6D4] to-[#00D294] transition-all duration-500 ease-out rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
