import React from 'react';

export function VectorHireSymbol({ size = 28, className = '' }) {
  const gradientId = 'vh-grad-' + size;
  const accentGradId = 'vh-accent-' + size;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`flex-shrink-0 transition-transform duration-200 hover:scale-105 ${className}`}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0284C7" />
          <stop offset="50%" stopColor="#0369A1" />
          <stop offset="100%" stopColor="#075985" />
        </linearGradient>
        <linearGradient id={accentGradId} x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#06B6D4" />
          <stop offset="100%" stopColor="#00D294" />
        </linearGradient>
        <filter id="vh-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#06B6D4" floodOpacity="0.3" />
        </filter>
      </defs>

      <rect width="32" height="32" rx="8" fill={`url(#${gradientId})`} />
      <path
        d="M8 10L14.5 22.5C14.8 23.1 15.6 23.3 16.2 22.9C16.4 22.8 16.5 22.6 16.6 22.5L24 10"
        stroke="#FFFFFF"
        strokeWidth="2.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M15 16.5L21.5 7.5"
        stroke={`url(#${accentGradId})`}
        strokeWidth="2.75"
        strokeLinecap="round"
      />
      <circle
        cx="21.5"
        cy="7.5"
        r="2.25"
        fill="#00D294"
        stroke="#FFFFFF"
        strokeWidth="1.25"
      />
    </svg>
  );
}

export function Logo({
  symbolSize = 28,
  showWordmark = true,
  showSubtitle = true,
  className = '',
}) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <VectorHireSymbol size={symbolSize} />
      {showWordmark && (
        <div className="flex items-baseline gap-2 leading-none">
          <span className="font-sans font-bold text-lg tracking-tight text-[#0F172A] hover:text-[#0369A1] transition-colors">
            VectorHire
          </span>
          {showSubtitle && (
            <span className="hidden sm:inline-block text-xs font-semibold text-[#64748B] tracking-normal">
              Resume Intelligence
            </span>
          )}
        </div>
      )}
    </div>
  );
}
