import React, { useState } from 'react';
import {
  Check,
  Shield,
  Sliders,
  Plus,
  Trash2,
  ArrowRight,
  ArrowLeft,
  Info,
  CheckCircle,
  AlertCircle,
  Lock,
  Unlock,
  Sparkles,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import {
  RequirementCategory,
  RequirementCategoryConfig,
} from '../../constants/taxonomy';
import { CategoryBadge, HardGateBadge } from '../common/Badge';

export function RubricEditor() {
  const { jobSpec, updateJobSpec, setActiveStep } = useScreening();
  const [showAddModal, setShowAddModal] = useState(false);
  const [newReq, setNewReq] = useState({
    name: '',
    category: RequirementCategory.MANDATORY_COMPETENCY,
    description: '',
    is_hard_gate: false,
    weight: 1.0,
  });

  if (!jobSpec) return null;

  const rubric = jobSpec.rubric || {
    weights: {
      [RequirementCategory.MANDATORY_COMPETENCY]: 0.40,
      [RequirementCategory.LICENSE_REGISTRATION]: 0.30,
      [RequirementCategory.EXPERIENCE_TENURE]: 0.20,
      [RequirementCategory.EDUCATION]: 0.05,
      [RequirementCategory.PREFERRED_COMPETENCY]: 0.05,
    },
    gamma: 0.50,
    rubric_version: 1,
  };

  const weights = rubric.weights || rubric.category_weights || {};
  const currentSum = Object.values(weights).reduce((acc, val) => acc + (Number(val) || 0), 0);
  const isWeightSumValid = Math.abs(currentSum - 1.0) < 0.001;

  const handleWeightChange = (category, val) => {
    const num = Math.max(0, Math.min(1, parseFloat(val) || 0));
    const updatedWeights = {
      ...weights,
      [category]: num,
    };
    updateJobSpec((prev) => ({
      ...prev,
      rubric: {
        ...prev.rubric,
        weights: updatedWeights,
        category_weights: updatedWeights,
        rubric_version: (prev.rubric?.rubric_version || prev.rubric?.version || 1),
      },
    }));
  };

  const handleGammaChange = (val) => {
    const num = Math.max(0, Math.min(1, parseFloat(val) || 0));
    updateJobSpec((prev) => ({
      ...prev,
      rubric: {
        ...prev.rubric,
        gamma: num,
      },
    }));
  };

  const toggleHardGate = (reqId) => {
    updateJobSpec((prev) => ({
      ...prev,
      requirements: prev.requirements.map((r) =>
        r.requirement_id === reqId ? { ...r, is_hard_gate: !r.is_hard_gate } : r
      ),
    }));
  };

  const removeRequirement = (reqId) => {
    if (jobSpec.requirements.length <= 1) {
      alert('Job specification must contain at least one requirement.');
      return;
    }
    updateJobSpec((prev) => ({
      ...prev,
      requirements: prev.requirements.filter((r) => r.requirement_id !== reqId),
    }));
  };

  const handleAddRequirement = (e) => {
    e.preventDefault();
    if (!newReq.name.trim()) return;

    const reqId = `req_custom_${Date.now()}`;
    const requirementToAdd = {
      requirement_id: reqId,
      name: newReq.name.trim(),
      category: newReq.category,
      description: newReq.description.trim() || newReq.name.trim(),
      is_hard_gate: newReq.is_hard_gate,
      weight: parseFloat(newReq.weight) || 1.0,
      normalized_terms: [newReq.name.trim().toLowerCase()],
      controlled_aliases: [],
      aliases: [],
    };

    updateJobSpec((prev) => ({
      ...prev,
      requirements: [...prev.requirements, requirementToAdd],
    }));

    setNewReq({
      name: '',
      category: RequirementCategory.MANDATORY_COMPETENCY,
      description: '',
      is_hard_gate: false,
      weight: 1.0,
    });
    setShowAddModal(false);
  };

  const hardGateCount = jobSpec.requirements.filter((r) => r.is_hard_gate).length;

  // Segment colors for category balance visualizer
  const getCategorySegmentColor = (catKey) => {
    if (catKey === RequirementCategory.MANDATORY_COMPETENCY) return 'bg-[#0369A1]';
    if (catKey === RequirementCategory.LICENSE_REGISTRATION) return 'bg-[#06B6D4]';
    if (catKey === RequirementCategory.EXPERIENCE_TENURE) return 'bg-[#8B5CF6]';
    if (catKey === RequirementCategory.EDUCATION) return 'bg-[#00D294]';
    return 'bg-[#94A3B8]';
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto motion-safe:animate-fade-in">
      {/* Editorial Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-gradient-to-r from-[#F0F9FF] to-[#ECFEFF] text-[#0369A1] border border-[#BAE6FD] shadow-subtle">
              Stage 02
            </span>
            <span className="text-xs font-semibold text-[#475569]">
              {jobSpec.detected_domain || 'General'} • {jobSpec.seniority_level || 'Mid-Senior'}
            </span>
          </div>
          <h1 className="font-sans text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
            {jobSpec.job_title}
          </h1>
          <p className="text-xs text-[#475569] mt-1 leading-relaxed">
            Review extracted criteria, calibrate category weights, and enforce hard-gate constraints.
          </p>
        </div>

        {/* Top Direct Navigation */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setActiveStep('job')}
            className="btn-secondary text-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to job description</span>
          </button>
          <button
            onClick={() => setActiveStep('resumes')}
            disabled={!isWeightSumValid}
            className="btn-primary text-xs"
          >
            <span>Continue to resumes</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Rubric Weights & Uncertainty Parameters */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Weights Card with Interactive Balance Ribbon */}
        <div className="lg:col-span-2 card-modern p-6 space-y-5 border-[#BAE6FD]/60 shadow-[0_4px_20px_-4px_rgba(7,89,133,0.06)]">
          <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[#F0F9FF] border border-[#BAE6FD] flex items-center justify-center text-[#0369A1]">
                <Sliders className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
                Category Weight Distribution
              </h3>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[#64748B] font-medium">Sum:</span>
              <span
                className={`font-mono font-bold px-2.5 py-0.5 rounded-full text-xs shadow-sm ${
                  isWeightSumValid
                    ? 'bg-[#E8FBF5] text-[#0B5B44] border border-[#A3F3DC]'
                    : 'bg-[#FFF1F2] text-[#9F1239] border border-[#FECDD3]'
                }`}
              >
                {(currentSum * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Interactive Proportional Weight Ribbon */}
          <div className="space-y-1.5">
            <div className="w-full h-3 bg-[#F1F5F9] rounded-full overflow-hidden flex p-[1px] shadow-inner">
              {Object.entries(RequirementCategoryConfig).map(([catKey]) => {
                const weightVal = weights[catKey] !== undefined ? weights[catKey] : 0;
                const pct = (weightVal / Math.max(0.001, currentSum)) * 100;
                if (weightVal <= 0) return null;
                return (
                  <div
                    key={catKey}
                    className={`${getCategorySegmentColor(catKey)} h-full transition-all duration-300 first:rounded-l-full last:rounded-r-full`}
                    style={{ width: `${pct}%` }}
                    title={`${RequirementCategoryConfig[catKey].label}: ${(weightVal * 100).toFixed(0)}%`}
                  />
                );
              })}
            </div>
            <div className="flex items-center justify-between text-[10px] text-[#64748B] font-mono px-1">
              <span>0%</span>
              <span className="font-semibold text-[#0369A1]">Calibrated 100% Target</span>
              <span>100%</span>
            </div>
          </div>

          {/* Individual Category Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(RequirementCategoryConfig).map(([catKey, config]) => {
              const currentVal = weights[catKey] !== undefined ? weights[catKey] : config.defaultWeight;
              return (
                <div key={catKey} className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] space-y-2 hover:bg-white hover:border-[#BAE6FD] hover:shadow-subtle transition-all">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#0F172A] truncate">{config.label}</span>
                    <span className="font-mono text-xs font-bold text-[#0369A1] px-1.5 py-0.5 rounded bg-[#F0F9FF]">
                      {(currentVal * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={currentVal}
                    onChange={(e) => handleWeightChange(catKey, e.target.value)}
                    className="w-full accent-[#0369A1] cursor-pointer h-1.5"
                  />
                </div>
              );
            })}
          </div>

          {!isWeightSumValid && (
            <p className="text-xs text-[#9F1239] flex items-center gap-2 font-medium bg-[#FFF1F2] p-3 rounded-xl border border-[#FECDD3] animate-in fade-in">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-[#E11D48]" />
              Category weights must sum to exactly 100% (1.00) to ensure deterministic calibration.
            </p>
          )}
        </div>

        {/* Gamma Uncertainty Discount Card */}
        <div className="card-modern p-6 space-y-4 border-[#BAE6FD]/60 shadow-[0_4px_20px_-4px_rgba(7,89,133,0.06)]">
          <div className="flex items-center gap-2 pb-3 border-b border-[#E2E8F0]">
            <div className="w-7 h-7 rounded-lg bg-[#F0F9FF] border border-[#BAE6FD] flex items-center justify-center text-[#0369A1]">
              <Shield className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              Partial Evidence Discount (γ)
            </h3>
          </div>

          <div className="space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#475569] font-medium">Uncertainty Multiplier:</span>
              <span className="font-mono text-xs font-bold text-[#0369A1] px-2.5 py-1 rounded-full bg-[#F0F9FF] border border-[#BAE6FD] shadow-subtle">
                γ = {rubric.gamma.toFixed(2)}
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={rubric.gamma}
              onChange={(e) => handleGammaChange(e.target.value)}
              className="w-full accent-[#06B6D4] cursor-pointer h-2"
            />

            <div className="text-[11px] text-[#475569] leading-relaxed bg-[#F8FAFC] p-3.5 rounded-xl border border-[#E2E8F0]">
              Criteria with uncertain, assisted, or coursework-only evidence are awarded{' '}
              <strong className="text-[#0F172A] font-bold">{(rubric.gamma * 100).toFixed(0)}%</strong> of full points,
              penalizing ambiguity while maintaining dignity of unevidenced claims.
            </div>
          </div>
        </div>
      </div>

      {/* Evaluated Requirements Matrix */}
      <div className="card-modern overflow-hidden border-[#BAE6FD]/60 shadow-[0_4px_20px_-4px_rgba(7,89,133,0.06)]">
        <div className="p-5 sm:p-6 bg-white border-b border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-sans text-base font-bold text-[#0F172A] tracking-tight">
              Calibrated Evaluation Criteria ({jobSpec.requirements.length})
            </h3>
            <p className="text-xs text-[#475569] mt-0.5">
              Review extracted criteria. Toggle mandatory hard gates or add custom requirements.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-[#0F172A] font-semibold px-3 py-1 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] shadow-subtle">
              Hard Gates: <strong className="text-[#E11D48]">{hardGateCount}</strong>
            </span>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-secondary text-xs py-2 px-3.5"
            >
              <Plus className="w-3.5 h-3.5 text-[#0369A1]" />
              <span>Add Criterion</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F8FAFC] text-[#64748B] uppercase text-[11px] font-bold border-b border-[#E2E8F0]">
              <tr>
                <th className="py-3.5 px-4">Requirement / Competency</th>
                <th className="py-3.5 px-4">Category</th>
                <th className="py-3.5 px-4">Hard Gate</th>
                <th className="py-3.5 px-4">Description & Aliases</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {jobSpec.requirements.map((req) => (
                <tr key={req.requirement_id} className="hover:bg-[#F0F9FF]/40 transition-colors group">
                  <td className="py-3.5 px-4 font-bold text-[#0F172A] max-w-[200px]">
                    <div className="truncate text-sm group-hover:text-[#0369A1] transition-colors" title={req.name}>{req.name}</div>
                    <div className="text-[10px] font-mono text-[#64748B] mt-0.5">{req.requirement_id}</div>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <CategoryBadge category={req.category} />
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <button
                      onClick={() => toggleHardGate(req.requirement_id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border transition-all duration-200 active:scale-[0.97] ${
                        req.is_hard_gate
                          ? 'bg-[#FFF1F2] text-[#9F1239] border-[#FECDD3] shadow-[0_0_8px_rgba(225,29,72,0.15)]'
                          : 'bg-white text-[#64748B] border-[#E2E8F0] hover:border-[#BAE6FD] hover:text-[#0369A1]'
                      }`}
                      title={req.is_hard_gate ? 'Click to make standard' : 'Click to enforce as Hard Gate'}
                    >
                      {req.is_hard_gate ? (
                        <>
                          <Lock className="w-3 h-3 text-[#E11D48]" />
                          <span>Hard Gate</span>
                        </>
                      ) : (
                        <>
                          <Unlock className="w-3 h-3 text-[#94A3B8]" />
                          <span>Standard</span>
                        </>
                      )}
                    </button>
                  </td>
                  <td className="py-3.5 px-4 max-w-[320px]">
                    <p className="text-[#334155] line-clamp-2 leading-relaxed">{req.description}</p>
                    {req.aliases && req.aliases.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {req.aliases.map((alias, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]"
                          >
                            {alias}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <button
                      onClick={() => removeRequirement(req.requirement_id)}
                      className="text-[#64748B] hover:text-[#E11D48] p-1.5 rounded-lg hover:bg-[#FFF1F2] transition-colors"
                      title="Remove requirement"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Bottom Actions Bar */}
        <div className="p-5 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-between">
          <button
            onClick={() => setActiveStep('job')}
            className="btn-secondary text-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to job description</span>
          </button>
          <button
            onClick={() => setActiveStep('resumes')}
            disabled={!isWeightSumValid}
            className="btn-primary text-xs"
          >
            <span>Continue to resumes</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Add Custom Requirement Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl shadow-elevated border border-[#E2E8F0] max-w-lg w-full overflow-hidden animate-in zoom-in-95 duration-150">
            <form onSubmit={handleAddRequirement}>
              <div className="p-5 bg-gradient-to-r from-[#0369A1] via-[#0284C7] to-[#075985] text-white flex items-center justify-between">
                <div>
                  <h3 className="font-sans font-bold text-sm tracking-tight">Add Custom Evaluation Requirement</h3>
                  <p className="text-[11px] text-[#BAE6FD]">Configure criterion and assign category</p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10"
                >
                  ✕
                </button>
              </div>

              <div className="p-6 space-y-4 text-xs">
                <div className="space-y-1">
                  <label className="font-bold text-[#0F172A]">Requirement Name *</label>
                  <input
                    type="text"
                    required
                    value={newReq.name}
                    onChange={(e) => setNewReq({ ...newReq, name: e.target.value })}
                    placeholder="e.g. Distributed Caching with Redis"
                    className="w-full text-xs px-3.5 py-2.5 border border-[#E2E8F0] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3.5">
                  <div className="space-y-1">
                    <label className="font-bold text-[#0F172A]">Category *</label>
                    <select
                      value={newReq.category}
                      onChange={(e) => setNewReq({ ...newReq, category: e.target.value })}
                      className="w-full text-xs px-3 py-2.5 border border-[#E2E8F0] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1] bg-white text-[#0F172A]"
                    >
                      {Object.entries(RequirementCategoryConfig).map(([key, cfg]) => (
                        <option key={key} value={key}>{cfg.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="font-bold text-[#0F172A]">Hard Gate Status</label>
                    <div className="pt-2">
                      <label className="inline-flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={newReq.is_hard_gate}
                          onChange={(e) => setNewReq({ ...newReq, is_hard_gate: e.target.checked })}
                          className="rounded text-[#0369A1] focus:ring-[#0369A1]"
                        />
                        <span className="text-[#0F172A] font-semibold">Mandatory Hard Gate</span>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="font-bold text-[#0F172A]">Requirement Description</label>
                  <textarea
                    rows={3}
                    value={newReq.description}
                    onChange={(e) => setNewReq({ ...newReq, description: e.target.value })}
                    placeholder="Specify evidence expectation for candidates..."
                    className="w-full text-xs p-3 border border-[#E2E8F0] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1]"
                  />
                </div>
              </div>

              <div className="p-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary text-xs py-2 px-3.5"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-xs py-2 px-4">
                  Add Criterion
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
