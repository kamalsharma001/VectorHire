import React, { useRef, useState } from 'react';
import {
  UploadCloud,
  FileCheck,
  FileX,
  Trash2,
  ArrowRight,
  ArrowLeft,
  AlertCircle,
  Info,
  CheckCircle2,
  FileText,
  ShieldCheck,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import { Alert } from '../common/Alert';

export function ResumeDropzone() {
  const {
    jobSpec,
    selectedFiles,
    setSelectedFiles,
    isScreening,
    handleStartScreening,
    setActiveStep,
    errorMessage,
    setErrorMessage,
    backendHealth,
  } = useScreening();

  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const maxBatchSize = backendHealth?.max_batch_size || 10;
  const maxFileSizeMB = backendHealth?.max_file_size_mb || 10;
  const maxBytes = maxFileSizeMB * 1024 * 1024;

  const handleFiles = (incomingFileList) => {
    setErrorMessage(null);
    const files = Array.from(incomingFileList);

    const validNewFiles = [];
    const errors = [];

    for (const file of files) {
      // Validate PDF MIME type or extension
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      if (!isPdf) {
        errors.push(`'${file.name}' is not a PDF file. Only PDF documents are accepted.`);
        continue;
      }

      // Validate individual file size
      if (file.size > maxBytes) {
        errors.push(`'${file.name}' (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds the maximum limit of ${maxFileSizeMB}MB.`);
        continue;
      }

      // Prevent duplicate names in the current batch
      const alreadyAdded = selectedFiles.some((f) => f.name === file.name);
      if (alreadyAdded) {
        errors.push(`'${file.name}' is already included in this batch.`);
        continue;
      }

      validNewFiles.push(file);
    }

    if (selectedFiles.length + validNewFiles.length > maxBatchSize) {
      errors.push(`Batch size limit exceeded. Maximum ${maxBatchSize} resumes allowed per screening session.`);
      const remainingSlots = Math.max(0, maxBatchSize - selectedFiles.length);
      validNewFiles.splice(remainingSlots);
    }

    if (errors.length > 0) {
      setErrorMessage(errors.join(' '));
    }

    if (validNewFiles.length > 0) {
      setSelectedFiles((prev) => [...prev, ...validNewFiles]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleRemoveFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
    setErrorMessage(null);
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto motion-safe:animate-fade-in">
      {/* Editorial Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-gradient-to-r from-[#F0F9FF] to-[#ECFEFF] text-[#0369A1] border border-[#BAE6FD] shadow-subtle">
              Stage 03
            </span>
            <span className="text-xs font-semibold text-[#475569]">
              Evaluating against: <strong className="text-[#0F172A] font-bold">{jobSpec?.job_title || 'Role'}</strong>
            </span>
          </div>
          <h1 className="font-sans text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
            Resume Batch Upload
          </h1>
          <p className="text-xs text-[#475569] mt-1 leading-relaxed">
            Upload candidate resumes in PDF format for verifiable provenance retrieval and rubric scoring.
          </p>
        </div>

        <button
          onClick={() => setActiveStep('requirements')}
          className="btn-secondary text-xs self-start sm:self-auto"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to requirements</span>
        </button>
      </div>

      {errorMessage && (
        <Alert
          type="warning"
          title="Batch Notice"
          message={errorMessage}
          onClose={() => setErrorMessage(null)}
        />
      )}

      {/* Dropzone Container with Vibrant Glow on Drag */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 ${
          dragOver
            ? 'border-[#06B6D4] bg-[#ECFEFF]/60 scale-[1.01] shadow-glow-cyan'
            : 'border-[#CBD5E1] bg-white hover:border-[#0369A1] hover:bg-[#F0F9FF]/40 hover:shadow-subtle'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,application/pdf"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = '';
          }}
          className="hidden"
        />

        <div className="max-w-md mx-auto space-y-3.5 pointer-events-none">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-[#F0F9FF] via-[#ECFEFF] to-[#E0F2FE] border border-[#BAE6FD] flex items-center justify-center text-[#0369A1] shadow-glow-cyan transition-transform duration-200 hover:scale-105">
            <UploadCloud className="w-7 h-7 stroke-[1.75]" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#0F172A]">
              Drag and drop PDF resumes here, or <span className="text-[#0369A1] underline font-semibold">browse files</span>
            </h3>
            <p className="text-xs text-[#64748B] mt-1 font-medium">
              Supports up to {maxBatchSize} resumes per batch • Max {maxFileSizeMB}MB per PDF
            </p>
          </div>
        </div>
      </div>

      {/* Validation Gate Pre-flight Notice Card */}
      <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-[#F0F9FF] to-[#ECFEFF] border border-[#BAE6FD] text-xs flex items-start gap-3.5 shadow-subtle">
        <div className="w-8 h-8 rounded-xl bg-white border border-[#BAE6FD] flex items-center justify-center text-[#0369A1] flex-shrink-0 shadow-sm mt-0.5">
          <ShieldCheck className="w-5 h-5 text-[#0369A1]" />
        </div>
        <div className="text-[#475569] leading-relaxed">
          <strong className="text-[#0F172A] font-bold">Resume Validation Gate:</strong> VectorHire performs a pre-flight document classification gate prior to screening. Academic research papers, billing invoices, transcripts, and scanned image-only PDFs lacking an embedded text layer will be flagged and reported with diagnostic codes without halting the batch.
        </div>
      </div>

      {/* Selected Resumes Table with Micro-Lift Cards */}
      {selectedFiles.length > 0 && (
        <div className="card-modern overflow-hidden border-[#BAE6FD]/60 shadow-[0_4px_20px_-4px_rgba(7,89,133,0.06)] motion-safe:animate-slide-up">
          <div className="p-4 sm:p-5 bg-white border-b border-[#E2E8F0] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-lg bg-[#E8FBF5] flex items-center justify-center text-[#00D294]">
                <FileCheck className="w-4 h-4 text-[#00D294]" />
              </div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F172A]">
                Resumes Ready for Evaluation ({selectedFiles.length}/{maxBatchSize})
              </h3>
            </div>
            <button
              onClick={handleClearAll}
              className="text-xs text-[#64748B] hover:text-[#E11D48] font-semibold transition-colors"
            >
              Clear All Files
            </button>
          </div>

          <div className="divide-y divide-[#E2E8F0]">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="p-3.5 sm:p-4 flex items-center justify-between gap-4 hover:bg-[#F0F9FF]/40 transition-colors text-xs group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-[#F0F9FF] border border-[#BAE6FD] flex items-center justify-center text-[#0369A1] flex-shrink-0 shadow-subtle group-hover:border-[#0369A1] transition-colors">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-bold text-[#0F172A] truncate group-hover:text-[#0369A1] transition-colors" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-[11px] font-mono text-[#64748B] mt-0.5">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#E8FBF5] text-[#0B5B44] border border-[#A3F3DC] font-bold shadow-sm">
                    Ready
                  </span>
                  <button
                    onClick={() => handleRemoveFile(idx)}
                    className="p-1.5 rounded-lg text-[#64748B] hover:text-[#E11D48] hover:bg-[#FFF1F2] transition-colors"
                    title="Remove resume"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom Actions Bar */}
          <div className="p-4 sm:p-5 bg-[#F8FAFC] border-t border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <button
              onClick={() => setActiveStep('requirements')}
              className="btn-secondary text-xs"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to requirements</span>
            </button>

            <button
              onClick={handleStartScreening}
              disabled={isScreening || selectedFiles.length === 0}
              className="btn-primary text-xs disabled:opacity-60 disabled:cursor-not-allowed shadow-md"
            >
              {isScreening ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                  <span>Starting evaluation...</span>
                </>
              ) : (
                <>
                  <span>Evaluate candidates ({selectedFiles.length})</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
