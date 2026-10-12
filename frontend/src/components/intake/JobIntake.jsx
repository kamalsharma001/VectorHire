import React, { useState, useRef } from 'react';
import {
  FileText,
  Sparkles,
  ArrowRight,
  HelpCircle,
  RotateCcw,
  UploadCloud,
  CheckCircle2,
  FileCode,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import { Alert } from '../common/Alert';

export function JobIntake() {
  const {
    rawJobText,
    setRawJobText,
    jobTitleHint,
    setJobTitleHint,
    jobSpec,
    isAnalyzingJob,
    handleAnalyzeJob,
    isExtractingJobText,
    extractedJobFileInfo,
    handleExtractJobText,
    errorMessage,
    setErrorMessage,
  } = useScreening();

  const [intakeMode, setIntakeMode] = useState('paste'); // 'paste' | 'upload'
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleClear = () => {
    setRawJobText('');
    setJobTitleHint('');
    setErrorMessage(null);
  };

  const handleFileDrop = async (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      await processUploadedFile(files[0]);
    }
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await processUploadedFile(files[0]);
    }
  };

  const processUploadedFile = async (file) => {
    const validExtensions = ['.pdf', '.docx', '.txt'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValid) {
      setErrorMessage(
        `Unsupported file type '${file.name}'. Please upload a PDF (.pdf), Word (.docx), or plain text (.txt) file.`
      );
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage(`File '${file.name}' exceeds the 10MB size limit.`);
      return;
    }

    try {
      await handleExtractJobText(file);
      // Auto-populate job title hint from filename if empty
      if (!jobTitleHint) {
        const guessedTitle = file.name
          .replace(/\.[^/.]+$/, '')
          .replace(/[_-]/g, ' ')
          .replace(/\b\w/g, (c) => c.toUpperCase());
        setJobTitleHint(guessedTitle);
      }
    } catch {
      // Error handled inside handleExtractJobText
    }
  };

  const getFormatBadge = (format) => {
    if (format === 'pdf') return 'PDF Document';
    if (format === 'docx') return 'Word Document (.docx)';
    if (format === 'txt') return 'Plain Text (.txt)';
    return format?.toUpperCase() || 'Document';
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto motion-safe:animate-fade-in">
      {/* Editorial Header with Vibrant Gradient Accent */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-gradient-to-r from-[#F0F9FF] to-[#ECFEFF] text-[#0369A1] border border-[#BAE6FD] shadow-subtle">
              Stage 01
            </span>
            <span className="text-xs font-semibold text-[#475569]">
              Job Intake & Rubric Initialization
            </span>
          </div>
          <h1 className="font-sans text-2xl sm:text-3xl font-bold text-[#0F172A] tracking-tight">
            Job Description & Rubric Intake
          </h1>
          <p className="text-xs text-[#475569] mt-1 leading-relaxed max-w-2xl">
            Ingest your job description to extract structured, calibrated evaluation criteria and configure your deterministic screening rubric.
          </p>
        </div>

        {rawJobText && (
          <button
            onClick={handleClear}
            className="self-start md:self-auto text-xs px-3 py-1.5 text-[#64748B] hover:text-[#E11D48] rounded-xl border border-[#E2E8F0] hover:border-[#FECDD3] hover:bg-[#FFF1F2] transition-all flex items-center gap-1.5 shadow-subtle active:scale-[0.98]"
            title="Clear current text"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Clear Input</span>
          </button>
        )}
      </div>

      {errorMessage && (
        <Alert
          type="error"
          title="Intake Error"
          message={errorMessage}
          onClose={() => setErrorMessage(null)}
        />
      )}

      {/* Main Intake Form Card with Layered Elevation */}
      <div className="card-modern p-6 sm:p-8 space-y-6 border-[#BAE6FD]/60 shadow-[0_4px_20px_-4px_rgba(7,89,133,0.06)]">
        {/* Intake Mode Segmented Control */}
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4">
          <div className="inline-flex p-1 rounded-xl bg-[#F1F5F9] border border-[#E2E8F0] text-xs font-semibold">
            <button
              onClick={() => setIntakeMode('paste')}
              className={`px-4 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 ${
                intakeMode === 'paste'
                  ? 'bg-white text-[#0369A1] shadow-sm font-bold'
                  : 'text-[#64748B] hover:text-[#0F172A]'
              }`}
            >
              <FileText className="w-4 h-4 text-[#0369A1]" />
              <span>Paste job description</span>
            </button>
            <button
              onClick={() => setIntakeMode('upload')}
              className={`px-4 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 ${
                intakeMode === 'upload'
                  ? 'bg-white text-[#0369A1] shadow-sm font-bold'
                  : 'text-[#64748B] hover:text-[#0F172A]'
              }`}
            >
              <UploadCloud className="w-4 h-4 text-[#06B6D4]" />
              <span>Upload document (PDF, DOCX, TXT)</span>
            </button>
          </div>

          <div className="text-[11px] text-[#64748B] hidden sm:block font-mono bg-[#F8FAFC] px-2.5 py-1 rounded-lg border border-[#E2E8F0]">
            {intakeMode === 'paste' ? 'Plain text input' : 'Max 10MB per document'}
          </div>
        </div>

        {/* Target Job Title Hint Input */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold text-[#0F172A] tracking-wide">
              Target Job Title (Optional Hint)
            </label>
            <span className="text-[11px] text-[#64748B]">
              Helps calibrate domain classification
            </span>
          </div>
          <input
            type="text"
            value={jobTitleHint}
            onChange={(e) => setJobTitleHint(e.target.value)}
            placeholder="e.g. Senior Software Engineer"
            className="w-full text-xs sm:text-sm px-4 py-2.5 border border-[#E2E8F0] rounded-xl bg-white placeholder:text-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1] transition-all text-[#0F172A] shadow-subtle hover:border-[#CBD5E1]"
          />
        </div>

        {/* Mode 1: Paste Text */}
        {intakeMode === 'paste' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-[#0F172A] tracking-wide">
                Job Description Text <span className="text-[#E11D48]">*</span>
              </label>
              <span className="text-[11px] text-[#64748B]">Minimum 20 characters</span>
            </div>

            <div className="relative group">
              <textarea
                rows={11}
                value={rawJobText}
                onChange={(e) => setRawJobText(e.target.value)}
                placeholder="Paste raw Job Description here..."
                className="w-full font-mono text-xs sm:text-sm p-4 sm:p-5 pb-10 border border-[#E2E8F0] rounded-xl bg-[#F8FAFC] placeholder:text-[#94A3B8] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#06B6D4]/30 focus:border-[#0369A1] leading-relaxed resize-y text-[#0F172A] transition-all shadow-inner group-hover:border-[#CBD5E1]"
              />
              <div className="absolute bottom-3 right-3 text-[11px] text-[#475569] font-mono bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-[#E2E8F0] shadow-sm pointer-events-none select-none">
                {rawJobText.length.toLocaleString()} characters
              </div>
            </div>
          </div>
        )}

        {/* Mode 2: Upload File */}
        {intakeMode === 'upload' && (
          <div className="space-y-4">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.docx,.txt"
              className="hidden"
            />

            {/* Dropzone with Glowing Hover States */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`p-8 sm:p-11 rounded-2xl border-2 border-dashed text-center cursor-pointer transition-all duration-200 ${
                isDragOver
                  ? 'border-[#06B6D4] bg-[#ECFEFF]/60 scale-[1.01] shadow-glow-cyan'
                  : 'border-[#CBD5E1] bg-[#F8FAFC] hover:border-[#0369A1] hover:bg-[#F0F9FF]/50 hover:shadow-subtle'
              }`}
            >
              <div className="flex flex-col items-center justify-center space-y-3.5">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#F0F9FF] via-[#ECFEFF] to-[#E0F2FE] border border-[#BAE6FD] flex items-center justify-center text-[#0369A1] shadow-glow-cyan">
                  {isExtractingJobText ? (
                    <Sparkles className="w-7 h-7 animate-spin text-[#0369A1]" />
                  ) : (
                    <UploadCloud className="w-7 h-7 stroke-[1.75]" />
                  )}
                </div>
                <div>
                  <p className="text-xs font-bold text-[#0F172A]">
                    {isExtractingJobText
                      ? 'Extracting document text with AI...'
                      : 'Click to upload or drag & drop job document'}
                  </p>
                  <p className="text-[11px] text-[#64748B] mt-1">
                    Supports PDF (.pdf), Word (.docx), and Plain Text (.txt) up to 10MB
                  </p>
                </div>
              </div>
            </div>

            {/* Extracted File Status Banner */}
            {extractedJobFileInfo && (
              <div className="p-4 rounded-xl bg-[#E8FBF5] border border-[#A3F3DC] flex items-center justify-between text-xs shadow-sm">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-[#00D294]/20 flex items-center justify-center text-[#00D294] flex-shrink-0">
                    <CheckCircle2 className="w-5 h-5 text-[#00D294]" />
                  </div>
                  <div className="min-w-0">
                    <span className="font-bold text-[#0B5B44] truncate block">
                      {extractedJobFileInfo.filename}
                    </span>
                    <span className="text-[11px] text-[#0B5B44]/80">
                      {getFormatBadge(extractedJobFileInfo.format)} • {extractedJobFileInfo.character_count.toLocaleString()} characters extracted
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setIntakeMode('paste')}
                  className="text-xs font-bold text-[#0B5B44] hover:underline flex-shrink-0 ml-2"
                >
                  View / Edit Text
                </button>
              </div>
            )}
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-[#E2E8F0]">
          <div className="flex items-center gap-2 text-xs text-[#475569]">
            <HelpCircle className="w-4 h-4 text-[#06B6D4] flex-shrink-0" />
            <span>AI extracts mandatory competencies, licenses, and configures initial rubric weights.</span>
          </div>

          <button
            onClick={() => handleAnalyzeJob()}
            disabled={isAnalyzingJob || isExtractingJobText || !rawJobText.trim() || rawJobText.trim().length < 20}
            className="btn-primary w-full sm:w-auto"
          >
            {isAnalyzingJob ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin text-[#A5F3FC]" />
                <span>Extracting Criteria with AI...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-[#A5F3FC]" />
                <span>{jobSpec ? 'Re-Analyze Job Description' : 'Analyze Job Description'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
