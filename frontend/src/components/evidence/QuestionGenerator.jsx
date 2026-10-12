import React, { useState } from 'react';
import {
  MessageSquare,
  Sparkles,
  HelpCircle,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  Send,
} from 'lucide-react';
import { api } from '../../api/client';
import { Alert } from '../common/Alert';
import { CategoryBadge } from '../common/Badge';

export function QuestionGenerator({ candidate, scorecard, jobSpec }) {
  const [questions, setQuestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedIdx, setCopiedIdx] = useState(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await api.generateQuestions({
        candidateId: candidate.candidate_id,
        candidateName: candidate.candidate_name,
        jobSpec: jobSpec,
        scorecard: scorecard,
        maxQuestions: 5,
      });

      setQuestions(res.questions || []);
    } catch (err) {
      setError(err.message || 'Failed to generate tailored interview questions.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Action Header */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-violet-50/70 via-purple-50/40 to-white border border-violet-100/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-sm">
        <div>
          <h4 className="font-bold text-[#0F172A] tracking-tight flex items-center gap-2">
            <span className="p-1 rounded-lg bg-violet-100/80 text-[#8B5CF6]">
              <MessageSquare className="w-3.5 h-3.5" />
            </span>
            <span>Targeted Interview Questions</span>
          </h4>
          <p className="text-slate-500 mt-1">
            Grounded strictly in verified resume claims and identified evidence gaps without assuming candidate deficiencies.
          </p>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isLoading}
          className="btn-violet text-xs py-1.5 px-3.5 shadow-sm hover:shadow-glow-violet whitespace-nowrap"
        >
          {isLoading ? (
            <>
              <Sparkles className="w-3.5 h-3.5 animate-spin text-violet-200" />
              <span>Generating with AI...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-violet-200" />
              <span>{questions.length > 0 ? 'Regenerate Questions' : 'Generate Questions'}</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <Alert
          type="error"
          title="Interview Agent Error"
          message={error}
          onClose={() => setError(null)}
        />
      )}

      {/* Generated Questions List */}
      {questions.length > 0 ? (
        <div className="space-y-3">
          {questions.map((q, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl border border-slate-200/80 bg-white shadow-sm hover:shadow-card-hover hover:border-[#8B5CF6]/40 transition-all duration-200 space-y-2.5 text-xs"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded-md border border-violet-100">
                    Q{idx + 1}.
                  </span>
                  <CategoryBadge category={q.category} />
                  <span className="font-semibold text-slate-800">{q.requirement_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-[#8B5CF6]/10 text-[#7C3AED] font-semibold border border-[#8B5CF6]/20">
                    Focus: {q.focus_area}
                  </span>
                  <button
                    onClick={() => copyToClipboard(q.question, idx)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-[#7C3AED] hover:bg-violet-50 transition-colors"
                    title="Copy question text"
                  >
                    {copiedIdx === idx ? (
                      <Check className="w-3.5 h-3.5 text-[#00D294]" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* The Actual Question */}
              <p className="text-slate-900 font-medium text-xs leading-relaxed bg-gradient-to-r from-violet-50/40 via-purple-50/20 to-white p-3.5 rounded-xl border border-violet-100 text-slate-800">
                "{q.question}"
              </p>

              {/* Rationale / Context */}
              <div className="text-[11px] text-slate-500 leading-relaxed pl-1">
                <strong className="text-slate-700">Recruiter Probe Rationale:</strong> {q.rationale}
              </div>
            </div>
          ))}
        </div>
      ) : (
        !isLoading && (
          <div className="p-8 text-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 text-xs text-slate-500 space-y-2">
            <MessageSquare className="w-8 h-8 text-violet-300 mx-auto" />
            <p className="font-medium text-slate-600">No interview questions generated yet for this candidate.</p>
            <p className="text-[11px] text-slate-400">
              Click &quot;Generate Questions&quot; above to produce targeted, evidence-grounded inquiry points.
            </p>
          </div>
        )
      )}
    </div>
  );
}
