import React from 'react';
import { AlertOctagon, FileWarning, HelpCircle } from 'lucide-react';

export function IngestionFailures({ failures = [] }) {
  if (!failures || failures.length === 0) return null;

  return (
    <div className="rounded-2xl border border-rose-200/80 bg-white shadow-sm overflow-hidden">
      <div className="p-4 bg-gradient-to-r from-rose-50/90 via-amber-50/30 to-white border-b border-rose-200/70 flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-rose-950">
          <div className="p-1.5 rounded-lg bg-rose-100/80 text-rose-600">
            <AlertOctagon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-rose-900">
              Validation Gate & Ingestion Exclusions ({failures.length})
            </h3>
            <p className="text-[11px] text-rose-600/90 font-normal">
              Documents safely isolated prior to scoring to prevent pipeline pollution
            </p>
          </div>
        </div>
        <span className="text-[11px] font-mono font-medium px-2.5 py-1 rounded-full bg-rose-100/70 text-rose-800 border border-rose-200">
          Isolated ({failures.length})
        </span>
      </div>

      <div className="divide-y divide-rose-100/80 bg-white">
        {failures.map((fail, idx) => {
            const diag = fail.diagnostic_metadata || {};
            const reasonCodes = diag.reason_codes || [];
            const detectedType = diag.detected_document_type || fail.error_type || 'Corrupted / Excluded';
            const confidence = diag.confidence_band || null;
            const stageName = fail.pipeline_stage || fail.stage || 'validation_gate';

            return (
              <div key={idx} className="p-4 text-xs space-y-2.5 hover:bg-rose-50/25 transition-colors duration-150">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2 font-semibold text-slate-900 flex-wrap">
                    <FileWarning className="w-4 h-4 text-rose-500 flex-shrink-0" />
                    <span className="font-mono text-slate-900">{fail.filename || `File #${idx + 1}`}</span>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200/80">
                      Type: {detectedType}
                    </span>
                    {confidence && (
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200/60">
                        Confidence: {confidence}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Stage: {stageName}
                  </span>
                </div>

              <p className="text-slate-700 leading-relaxed bg-slate-50/80 p-3 rounded-xl border border-slate-200/60 text-xs">
                {fail.error_message || 'Document failed structured classification gate.'}
              </p>

              {reasonCodes.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                  <span className="text-[10px] text-slate-500 font-medium">Detection Markers:</span>
                  {reasonCodes.map((code, cIdx) => (
                    <span
                      key={cIdx}
                      className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200/70"
                    >
                      {code}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
