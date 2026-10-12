import React from 'react';

export function ScoreBar({ score, showLabel = true, size = 'md' }) {
  const numericScore = typeof score === 'number' ? score : 0;
  const clamped = Math.max(0, Math.min(100, numericScore));

  let barGradient = 'bg-gradient-to-r from-[#0369A1] to-[#06B6D4]';
  let textColor = 'text-[#0369A1]';
  let shadowGlow = 'shadow-glow-blue';

  if (clamped >= 75) {
    barGradient = 'bg-gradient-to-r from-[#06B6D4] via-[#00D294] to-[#00B882]';
    textColor = 'text-[#0B5B44]';
    shadowGlow = 'shadow-glow-mint';
  } else if (clamped >= 50) {
    barGradient = 'bg-gradient-to-r from-[#0369A1] via-[#0284C7] to-[#06B6D4]';
    textColor = 'text-[#0369A1]';
    shadowGlow = 'shadow-glow-cyan';
  } else if (clamped >= 30) {
    barGradient = 'bg-gradient-to-r from-amber-400 to-amber-500';
    textColor = 'text-amber-800';
    shadowGlow = '';
  } else {
    barGradient = 'bg-gradient-to-r from-slate-300 to-slate-400';
    textColor = 'text-[#64748B]';
    shadowGlow = '';
  }

  const heightClass = size === 'sm' ? 'h-1.5' : size === 'lg' ? 'h-3' : 'h-2';

  return (
    <div className="w-full flex items-center gap-2.5">
      <div className={`flex-1 bg-[#E2E8F0] rounded-full overflow-hidden ${heightClass} p-[1px] shadow-inner`}>
        <div
          className={`${barGradient} ${heightClass} rounded-full transition-all duration-700 ease-out ${clamped >= 50 ? shadowGlow : ''}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <span className={`font-mono text-xs font-bold tabular-nums min-w-[3rem] text-right ${textColor}`}>
          {clamped.toFixed(1)}%
        </span>
      )}
    </div>
  );
}
