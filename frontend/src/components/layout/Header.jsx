import React, { useState } from 'react';
import {
  RotateCcw,
  Activity,
  Cpu,
  Database,
  RefreshCw,
  X,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  Terminal,
  ShieldCheck,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import { Logo } from '../common/Logo';
import { API_BASE } from '../../api/client';

export function Header() {
  const {
    backendHealth,
    healthStatus = 'checking',
    isHealthChecking,
    checkHealth,
    resetSession,
  } = useScreening();
  const [showConfirmReset, setShowConfirmReset] = useState(false);
  const [showHealthModal, setShowHealthModal] = useState(false);
  const [copiedField, setCopiedField] = useState(null);

  const isHealthy = healthStatus === 'ready' || (backendHealth && backendHealth.status === 'healthy');
  const isWakingUp = healthStatus === 'waking_up';
  const isChecking = isHealthChecking || healthStatus === 'checking';
  const isDev = import.meta.env.DEV;

  // Derive displayable health URL safely
  const healthUrl = API_BASE ? `${API_BASE}/health` : '/health';

  const copyToClipboard = (text, field) => {
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleConfirmReset = () => {
    resetSession();
    setShowConfirmReset(false);
  };

  return (
    <>
      <header className="h-14 bg-white/95 backdrop-blur-md border-b border-[#E2E8F0] px-4 sm:px-8 flex items-center justify-between transition-colors flex-shrink-0 z-30 sticky top-0 shadow-[0_1px_3px_rgba(15,23,42,0.03)]">
        {/* Canonical Brand Logo */}
        <Logo symbolSize={28} showWordmark={true} showSubtitle={true} />

        {/* Right Actions: System Health Status & Reset Button */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Subtle Backend Readiness Indicator with Glowing Pulse */}
          <button
            onClick={() => setShowHealthModal(true)}
            className="group flex items-center gap-2 px-3 py-1.5 rounded-full text-xs transition-all duration-200 hover:bg-[#F0F9FF] border border-[#E2E8F0] hover:border-[#BAE6FD] hover:shadow-sm"
            title="System readiness & AI infrastructure status"
          >
            <span className="relative flex h-2.5 w-2.5">
              {isHealthy && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D294] opacity-75" />
              )}
              {isWakingUp && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              )}
              <span
                className={`relative inline-flex rounded-full h-2.5 w-2.5 transition-colors ${
                  isHealthy
                    ? 'bg-[#00D294] shadow-[0_0_8px_rgba(0,210,148,0.8)]'
                    : isWakingUp
                    ? 'bg-[#06B6D4] shadow-[0_0_8px_rgba(6,182,212,0.8)]'
                    : isChecking
                    ? 'bg-amber-400'
                    : 'bg-[#E11D48]'
                }`}
              />
            </span>
            <span className="text-xs font-semibold text-[#475569] group-hover:text-[#0369A1] transition-colors hidden md:inline">
              {isHealthy
                ? 'System Ready'
                : isWakingUp
                ? 'Waking Up...'
                : isChecking
                ? 'Checking...'
                : 'Offline'}
            </span>
          </button>

          <div className="h-4 w-px bg-[#E2E8F0]" />

          {/* Discreet Reset Session Action */}
          <button
            onClick={() => setShowConfirmReset(true)}
            className="flex items-center gap-1.5 text-xs font-medium text-[#64748B] hover:text-[#E11D48] px-2.5 py-1.5 rounded-xl transition-all duration-150 hover:bg-[#FFF1F2] active:scale-[0.98]"
            title="Reset active ephemeral screening session"
          >
            <RotateCcw className="w-3.5 h-3.5 transition-transform duration-300 group-hover:-rotate-90" />
            <span className="hidden sm:inline">Reset session</span>
          </button>
        </div>
      </header>

      {/* Reset Confirmation Modal */}
      {showConfirmReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl shadow-elevated border border-[#E2E8F0] max-w-sm w-full p-6 space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-[#FFF1F2] border border-[#FECDD3] flex items-center justify-center flex-shrink-0 text-[#E11D48] shadow-sm">
                <RotateCcw className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <h3 className="font-sans text-base font-bold text-[#0F172A] tracking-tight">
                  Reset this screening session?
                </h3>
                <p className="text-xs text-[#475569] leading-relaxed">
                  All uploaded job descriptions, criteria, and evaluated candidate profiles reside in ephemeral memory and will be permanently cleared.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowConfirmReset(false)}
                className="btn-secondary text-xs py-2 px-3.5"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReset}
                className="inline-flex items-center justify-center px-4 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-[#E11D48] to-[#BE123C] hover:brightness-105 transition-all shadow-sm active:scale-[0.98]"
              >
                Yes, Reset Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Health & Diagnostic Modal with Generous Layout */}
      {showHealthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl shadow-elevated border border-[#E2E8F0] max-w-lg sm:max-w-xl w-full overflow-hidden my-8 animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-[#E2E8F0] flex items-center justify-between bg-gradient-to-r from-[#F0F9FF] via-[#ECFEFF] to-[#F8FAFC]">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0369A1] to-[#06B6D4] flex items-center justify-center text-white shadow-sm">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-sans text-base font-bold text-[#0F172A]">
                    System Readiness & Architecture
                  </h3>
                  <p className="text-xs text-[#475569]">
                    FastAPI 1.1 • Dual-Verification Production AI Stack
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowHealthModal(false)}
                className="text-[#64748B] hover:text-[#0F172A] p-1.5 rounded-lg hover:bg-white/80 transition-colors"
                title="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 sm:p-7 space-y-5 text-xs max-h-[75vh] overflow-y-auto">
              {/* API Service Status Box */}
              {isHealthy ? (
                <div className="flex items-center justify-between p-4 rounded-xl bg-[#E8FBF5] border border-[#A3F3DC] shadow-sm">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-[#00D294]/20 flex items-center justify-center text-[#00D294]">
                      <CheckCircle2 className="w-5 h-5 text-[#00D294]" />
                    </div>
                    <div>
                      <span className="font-bold text-[#0F172A] block text-xs">FastAPI Backend Service</span>
                      <span className="text-[11px] text-[#0B5B44]">Version {backendHealth?.version || '1.1.0'} • Online & Responding</span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-white text-[#0B5B44] border border-[#A3F3DC] text-[11px] font-bold shadow-subtle">
                    Operational
                  </span>
                </div>
              ) : isWakingUp ? (
                <div className="p-4 rounded-xl bg-[#F0F9FF] border border-[#BAE6FD] text-[#0369A1] space-y-2.5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-bold text-xs text-[#0F172A]">
                      <RefreshCw className="w-4 h-4 text-[#06B6D4] animate-spin flex-shrink-0" />
                      <span>Waking up VectorHire...</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-white text-[#0369A1] border border-[#BAE6FD] text-[10px] font-bold">
                      Starting Up
                    </span>
                  </div>
                  <p className="text-[11px] text-[#475569] leading-relaxed">
                    The evaluation service is starting. This can take a little while on the free hosting tier. Please wait.
                  </p>
                </div>
              ) : isChecking ? (
                <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-[#475569] space-y-2.5 shadow-sm">
                  <div className="flex items-center gap-2 font-bold text-xs text-[#0F172A]">
                    <RefreshCw className="w-4 h-4 text-[#0369A1] animate-spin flex-shrink-0" />
                    <span>Checking Service Readiness...</span>
                  </div>
                  <p className="text-[11px] text-[#475569] leading-relaxed">
                    Connecting to the VectorHire backend API service at{' '}
                    <code className="px-1.5 py-0.5 rounded bg-white border border-[#CBD5E1] text-[#0F172A] font-mono break-all">
                      {healthUrl}
                    </code>
                    ...
                  </p>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-[#FFF1F2] border border-[#FECDD3] text-[#9F1239] space-y-2.5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-bold text-xs text-[#E11D48]">
                      <AlertCircle className="w-4.5 h-4.5 text-[#E11D48] flex-shrink-0" />
                      <span>The evaluation service is temporarily unavailable.</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-white text-[#E11D48] border border-[#FECDD3] text-[10px] font-bold">
                      Offline
                    </span>
                  </div>
                  <p className="text-[11px] text-[#475569] leading-relaxed">
                    Please try again in a moment. If the issue persists, the backend hosting container may be restarting.
                  </p>
                </div>
              )}

              {/* AI Inference Models Section Card */}
              <div className="p-4 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] space-y-3 shadow-subtle">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] uppercase tracking-wider font-bold text-[#475569] flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-[#0369A1]" />
                    <span>AI Inference Architecture</span>
                  </span>
                  <span className="text-[10px] font-mono text-[#0369A1] font-semibold">
                    Gemini Primary • Groq Fallback
                  </span>
                </div>

                <div className="space-y-2.5">
                  {/* Primary LLM Model */}
                  <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-subtle">
                    <div>
                      <span className="text-[#475569] font-medium flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-[#0369A1]" />
                        Primary LLM
                      </span>
                      <span className="text-[10px] text-[#64748B] block mt-0.5">Google Gemini (Structured Output)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#0F172A] px-2 py-0.5 rounded bg-[#F8FAFC] border border-[#CBD5E1] break-all">
                        {backendHealth?.active_llm_model || 'gemini-2.5-flash'}
                      </span>
                      <button
                        onClick={() => copyToClipboard(backendHealth?.active_llm_model || 'gemini-2.5-flash', 'primary_llm')}
                        className="text-[#64748B] hover:text-[#0369A1] p-1 rounded transition-colors flex-shrink-0"
                        title="Copy model ID"
                      >
                        {copiedField === 'primary_llm' ? (
                          <Check className="w-3.5 h-3.5 text-[#00D294]" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Fallback LLM Model */}
                  <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-subtle">
                    <div>
                      <span className="text-[#475569] font-medium flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-amber-600" />
                        Fallback LLM
                      </span>
                      <span className="text-[10px] text-[#64748B] block mt-0.5">Groq Cloud (Automatic Failover)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#0F172A] px-2 py-0.5 rounded bg-[#F8FAFC] border border-[#CBD5E1] break-all">
                        {backendHealth?.fallback_llm_model || 'qwen/qwen3.8-27b'}
                      </span>
                      <button
                        onClick={() => copyToClipboard(backendHealth?.fallback_llm_model || 'qwen/qwen3.8-27b', 'fallback_llm')}
                        className="text-[#64748B] hover:text-[#0369A1] p-1 rounded transition-colors flex-shrink-0"
                        title="Copy fallback model ID"
                      >
                        {copiedField === 'fallback_llm' ? (
                          <Check className="w-3.5 h-3.5 text-[#00D294]" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Embedding Model */}
                  <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-subtle">
                    <div>
                      <span className="text-[#475569] font-medium flex items-center gap-2">
                        <Database className="w-3.5 h-3.5 text-[#06B6D4]" />
                        Embedding Model
                      </span>
                      <span className="text-[10px] text-[#64748B] block mt-0.5">Local ONNX Embedding Engine</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#0F172A] px-2 py-0.5 rounded bg-[#F8FAFC] border border-[#CBD5E1] break-all">
                        {backendHealth?.embedding_model || 'BAAI/bge-small-en-v1.5'}
                      </span>
                      <button
                        onClick={() => copyToClipboard(backendHealth?.embedding_model || 'BAAI/bge-small-en-v1.5', 'embedding')}
                        className="text-[#64748B] hover:text-[#0369A1] p-1 rounded transition-colors flex-shrink-0"
                        title="Copy embedding model ID"
                      >
                        {copiedField === 'embedding' ? (
                          <Check className="w-3.5 h-3.5 text-[#00D294]" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Calibrated Operational Safeguards Card */}
              <div className="p-4 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] space-y-3 shadow-subtle">
                <span className="text-[11px] uppercase tracking-wider font-bold text-[#475569] flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#00D294]" />
                  <span>Calibrated Operational Safeguards</span>
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg border border-[#E2E8F0] bg-white shadow-subtle space-y-1">
                    <div className="text-[#64748B] text-[11px] font-medium">Uncertainty Discount (γ)</div>
                    <div className="font-mono text-base font-bold text-[#0369A1]">
                      {backendHealth?.gamma_uncertainty_discount ?? 0.5}
                    </div>
                    <div className="text-[10px] text-[#64748B] leading-tight">
                      Penalizes ambiguous evidence by 50%
                    </div>
                  </div>

                  <div className="p-3 rounded-lg border border-[#E2E8F0] bg-white shadow-subtle space-y-1">
                    <div className="text-[#64748B] text-[11px] font-medium">Batch Upload Limit</div>
                    <div className="font-mono text-base font-bold text-[#06B6D4]">
                      {backendHealth?.max_batch_size || 10} resumes
                    </div>
                    <div className="text-[10px] text-[#64748B] leading-tight">
                      Max {backendHealth?.max_file_size_mb || 10}MB per PDF document
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-between gap-3">
              <span className="text-[11px] text-[#64748B] font-mono hidden sm:inline">
                Zero Retention Ephemeral Architecture
              </span>
              <div className="flex items-center gap-2.5 ml-auto">
                <button
                  onClick={() => checkHealth()}
                  disabled={isHealthChecking}
                  className="btn-secondary text-xs py-2 px-3.5 flex items-center gap-2 disabled:opacity-60"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isHealthChecking ? 'animate-spin text-[#0369A1]' : ''}`} />
                  <span>
                    {isHealthChecking
                      ? 'Checking...'
                      : isHealthy
                      ? 'Refresh Status'
                      : 'Retry Connection'}
                  </span>
                </button>
                <button
                  onClick={() => setShowHealthModal(false)}
                  className="btn-primary text-xs py-2 px-4"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
