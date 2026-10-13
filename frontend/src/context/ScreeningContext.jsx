import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

export const STAGES = [
  { id: 'job', step: 1, label: 'Job Description', shortLabel: 'Job' },
  { id: 'requirements', step: 2, label: 'Requirements & Rubric', shortLabel: 'Rubric' },
  { id: 'resumes', step: 3, label: 'Resume Upload', shortLabel: 'Resumes' },
  { id: 'evaluation', step: 4, label: 'Candidate Evaluation', shortLabel: 'Evaluation' },
  { id: 'results', step: 5, label: 'Results & Evidence', shortLabel: 'Results' },
];

export const PIPELINE_STAGES = [
  {
    step: '01',
    title: 'Preparing Candidate Documents',
    description: 'Document classification gate, PDF integrity checks, and text-layer validation to filter non-resumes.',
  },
  {
    step: '02',
    title: 'Extracting Resume Content',
    description: 'Decomposing document text into sections, credential records, project history, and candidate identifiers.',
  },
  {
    step: '03',
    title: 'Matching Requirements & Retrieving Evidence',
    description: 'Boundary-aware canonical lexical matching and dense semantic retrieval against rubric criteria.',
  },
  {
    step: '04',
    title: 'Verifying Supporting Evidence',
    description: 'Verifying verbatim source offsets, contextual execution capability, and strict anti-hallucination checks.',
  },
  {
    step: '05',
    title: 'Calculating Scores & Preparing Results',
    description: 'Applying deterministic category weights, γ uncertainty discounts, hard gates, and candidate ranking.',
  },
];

export const ScreeningContext = createContext(null);

export function ScreeningProvider({ children }) {
  // Backend connection & health
  const [backendHealth, setBackendHealth] = useState(null);
  const [isHealthChecking, setIsHealthChecking] = useState(true);

  // Workflow stages: 'job' | 'requirements' | 'resumes' | 'evaluation' | 'results'
  // (with backwards-compatible aliases 'intake' -> 'job', 'upload' -> 'resumes')
  const [activeStep, setActiveStepInternal] = useState('job');

  const normalizeStep = (step) => {
    if (step === 'intake') return 'job';
    if (step === 'upload') return 'resumes';
    return step;
  };

  const setActiveStep = (step) => {
    setActiveStepInternal(normalizeStep(step));
  };

  // Job description intake state
  const [rawJobText, setRawJobText] = useState('');
  const [jobTitleHint, setJobTitleHint] = useState('');
  const [jobSpec, setJobSpec] = useState(null);
  const [analysisSummary, setAnalysisSummary] = useState('');
  const [isAnalyzingJob, setIsAnalyzingJob] = useState(false);
  const [isExtractingJobText, setIsExtractingJobText] = useState(false);
  const [extractedJobFileInfo, setExtractedJobFileInfo] = useState(null);

  // Resume upload & batch state
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isScreening, setIsScreening] = useState(false);
  const [evaluationPhase, setEvaluationPhase] = useState('idle');
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0.0);
  const [screeningResult, setScreeningResult] = useState(null);

  // Candidate detail inspection drawer
  const [inspectedCandidateId, setInspectedCandidateId] = useState(null);

  // Global alerts/errors
  const [errorMessage, setErrorMessage] = useState(null);

  // Health check on initial load
  const checkHealth = useCallback(async () => {
    setIsHealthChecking(true);
    try {
      const data = await api.getHealth();
      setBackendHealth(data);
    } catch {
      setBackendHealth({ status: 'unreachable' });
    } finally {
      setIsHealthChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  /**
   * Extracts text from uploaded JD file (.pdf, .docx, .txt)
   */
  const handleExtractJobText = async (file) => {
    if (!file) return;
    setIsExtractingJobText(true);
    setErrorMessage(null);

    try {
      const res = await api.extractJobText(file);
      setRawJobText(res.text);
      setExtractedJobFileInfo({
        filename: res.filename,
        format: res.format,
        character_count: res.character_count,
      });
      return res;
    } catch (err) {
      setErrorMessage(err.message || `Failed to extract text from '${file.name}'.`);
      throw err;
    } finally {
      setIsExtractingJobText(false);
    }
  };

  /**
   * Submits raw job description to POST /analyze-job
   */
  const handleAnalyzeJob = async (customText, customHint) => {
    const textToSubmit = customText || rawJobText;
    const hintToSubmit = customHint !== undefined ? customHint : jobTitleHint;

    if (!textToSubmit || textToSubmit.trim().length < 20) {
      setErrorMessage('Please provide a job description with at least 20 characters.');
      return;
    }

    setIsAnalyzingJob(true);
    setErrorMessage(null);

    try {
      const res = await api.analyzeJob({
        jobDescriptionText: textToSubmit,
        jobTitleHint: hintToSubmit || null,
      });

      setJobSpec(res.job_spec);
      setAnalysisSummary(res.analysis_summary || '');
      setRawJobText(textToSubmit);
      if (hintToSubmit) setJobTitleHint(hintToSubmit);
      // Automatically advance to Stage 2: Requirements & Rubric
      setActiveStepInternal('requirements');
    } catch (err) {
      setErrorMessage(err.message || 'Job description analysis failed.');
    } finally {
      setIsAnalyzingJob(false);
    }
  };

  /**
   * Updates rubric weights, uncertainty discount, or requirement criteria
   */
  const updateJobSpec = (updater) => {
    setJobSpec((prev) => {
      if (typeof updater === 'function') {
        return updater(prev);
      }
      return { ...prev, ...updater };
    });
  };

  /**
   * Executes batch resume screening via POST /analyze-resumes with honest 5-stage progression and live timer
   */
  const handleStartScreening = async () => {
    if (isScreening) return;
    if (!selectedFiles || selectedFiles.length === 0) {
      setErrorMessage('Please add at least one PDF resume to begin screening.');
      return;
    }
    if (!jobSpec) {
      setErrorMessage('Job specification is missing. Please analyze a job description first.');
      return;
    }

    setIsScreening(true);
    setActiveStepInternal('evaluation');
    setCurrentStageIndex(0);
    setElapsedSeconds(0.0);
    setEvaluationPhase('Evaluating candidate evidence');
    setErrorMessage(null);

    try {
      const result = await api.analyzeResumes({
        files: selectedFiles,
        jobSpec: jobSpec,
      });

      if (!result || result.total_successful === 0 || !result.ranked_candidates || result.ranked_candidates.length === 0) {
        const failureMsg =
          result?.validation_errors && result.validation_errors.length > 0
            ? `All ${result.total_submitted || 'submitted'} resumes failed evaluation: ${result.validation_errors.map((e) => `${e.filename}: ${e.error_message}`).join('; ')}`
            : 'All uploaded candidate resumes failed evaluation. Please check your documents.';
        setErrorMessage(failureMsg);
        setActiveStepInternal('resumes');
        return;
      }

      setScreeningResult(result);
      setActiveStepInternal('results');
      if (result.ranked_candidates && result.ranked_candidates.length > 0) {
        setInspectedCandidateId(result.ranked_candidates[0].candidate_id);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Screening execution failed.');
      setActiveStepInternal('resumes');
    } finally {
      setIsScreening(false);
      setEvaluationPhase('idle');
    }
  };

  /**
   * Navigation checks
   */
  const canNavigateTo = (stepId) => {
    const id = normalizeStep(stepId);
    if (id === 'job') return true;
    if (id === 'requirements') return !!jobSpec;
    if (id === 'resumes') return !!jobSpec;
    if (id === 'evaluation') return isScreening;
    if (id === 'results') return !!screeningResult;
    return false;
  };

  /**
   * Completely resets the ephemeral session (zero retention)
   */
  const resetSession = () => {
    setActiveStepInternal('job');
    setRawJobText('');
    setJobTitleHint('');
    setJobSpec(null);
    setAnalysisSummary('');
    setSelectedFiles([]);
    setScreeningResult(null);
    setInspectedCandidateId(null);
    setErrorMessage(null);
    setExtractedJobFileInfo(null);
    setIsScreening(false);
    setEvaluationPhase('idle');
    setCurrentStageIndex(0);
    setElapsedSeconds(0.0);
  };

  const value = {
    backendHealth,
    isHealthChecking,
    checkHealth,
    activeStep,
    setActiveStep,
    rawJobText,
    setRawJobText,
    jobTitleHint,
    setJobTitleHint,
    jobSpec,
    analysisSummary,
    isAnalyzingJob,
    handleAnalyzeJob,
    isExtractingJobText,
    extractedJobFileInfo,
    handleExtractJobText,
    updateJobSpec,
    selectedFiles,
    setSelectedFiles,
    isScreening,
    evaluationPhase,
    currentStageIndex,
    elapsedSeconds,
    pipelineStages: PIPELINE_STAGES,
    handleStartScreening,
    screeningResult,
    inspectedCandidateId,
    setInspectedCandidateId,
    errorMessage,
    setErrorMessage,
    canNavigateTo,
    resetSession,
  };

  return (
    <ScreeningContext.Provider value={value}>
      {children}
    </ScreeningContext.Provider>
  );
}

export function useScreening() {
  const context = useContext(ScreeningContext);
  if (!context) {
    throw new Error('useScreening must be used within a ScreeningProvider');
  }
  return context;
}
