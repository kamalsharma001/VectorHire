import React from 'react';
import { Home, ArrowLeft, AlertCircle, Compass } from 'lucide-react';

export function NotFoundPage({ onNavigateHome }) {
  const handleGoHome = () => {
    if (typeof onNavigateHome === 'function') {
      onNavigateHome();
    } else {
      window.location.pathname = '/';
    }
  };

  return (
    <div className="min-h-[65vh] flex items-center justify-center px-4 py-12">
      <div className="max-w-md w-full text-center space-y-6 motion-safe:animate-fade-in">
        {/* Visual 404 Accent Badge */}
        <div className="relative inline-flex items-center justify-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#F0F9FF] to-[#ECFEFF] border border-[#BAE6FD] flex items-center justify-center text-[#0369A1] shadow-subtle mx-auto">
            <Compass className="w-10 h-10 text-[#0369A1] motion-safe:animate-pulse" />
          </div>
          <span className="absolute -top-1 -right-1 px-2 py-0.5 rounded-full bg-[#E11D48] text-white text-[10px] font-mono font-bold shadow-sm">
            404
          </span>
        </div>

        {/* Heading & Subtext */}
        <div className="space-y-2">
          <h1 className="font-sans text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
            Page Not Found
          </h1>
          <p className="text-xs sm:text-sm text-[#475569] leading-relaxed max-w-sm mx-auto">
            The page or route you requested does not exist or may have been moved. Return to the recruiter workflow to continue screening candidates.
          </p>
        </div>

        {/* Helpful Path Information */}
        <div className="p-3 rounded-xl bg-white border border-[#E2E8F0] shadow-subtle text-left space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#64748B]">
            <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
            <span>Requested Path</span>
          </div>
          <p className="font-mono text-xs text-[#0F172A] break-all bg-[#F8FAFC] p-1.5 rounded border border-[#CBD5E1]">
            {typeof window !== 'undefined' ? window.location.pathname : '/'}
          </p>
        </div>

        {/* Return Button Action */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={handleGoHome}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-[#0369A1] to-[#0284C7] hover:brightness-105 transition-all shadow-sm active:scale-[0.98]"
          >
            <Home className="w-4 h-4" />
            <span>Return to Screening Workflow</span>
          </button>
        </div>
      </div>
    </div>
  );
}
