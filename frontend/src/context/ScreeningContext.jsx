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

const ScreeningContext = createContext(null);

export function ScreeningProvider({ children }) {
  // Backend connection & health
  const [backendHealth, setBackendHealth] = useState(null);
  const [healthStatus, setHealthStatus] = useState('checking'); // 'checking' | 'waking_up' | 'ready' | 'unavailable'
  const [isHealthChecking, setIsHealthChecking] = useState(true);
  const [healthError, setHealthError] = useState(null);

  // In-flight health promise & poll cancel refs to prevent duplicate requests
  const healthPromiseRef = React.useRef(null);
  const pollTimerRef = React.useRef(null);
  const cancelWarmupRef = React.useRef(false);

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
  const [completedStages, setCompletedStages] = useState([]);
  const [screeningResult, setScreeningResult] = useState(null);

  // Candidate detail inspection drawer
  const [inspectedCandidateId, setInspectedCandidateId] = useState(null);

  // Global alerts/errors
  const [errorMessage, setErrorMessage] = useState(null);

  /**
   * Performs a single health probe, deduplicating concurrent calls via singleton promise.
   */
  const probeHealth = useCallback(async (options = {}) => {
    if (healthPromiseRef.current) {
      return healthPromiseRef.current;
    }

    const promise = (async () => {
      try {
        const data = await api.getHealth(options);
        return data;
      } finally {
        healthPromiseRef.current = null;
      }
    })();

    healthPromiseRef.current = promise;
    return promise;
  }, []);

  // Active loop identifier to immediately supersede older loops
  const activeLoopIdRef = React.useRef(0);

  /**
   * Bounded warm-up loop tailored for Render Free spin-downs.
   * Max 6 attempts (~30s total with backoff: 0s, 2s, 3s, 4s, 5s, 6s).
   */
  const warmUpBackend = useCallback(async (opts = {}) => {
    const { isManualRetry = false, maxRetries = 5, initialDelayMs = 2000 } = opts;
    
    // Clear any pending poll timer and invalidate existing loop
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    const currentLoopId = ++activeLoopIdRef.current;

    // If backend is already known ready and this is not a manual retry, no need to re-poll
    if (!isManualRetry && backendHealth?.status === 'healthy') {
      setHealthStatus('ready');
      setIsHealthChecking(false);
      return backendHealth;
    }

    setIsHealthChecking(true);
    setHealthError(null);
    if (isManualRetry || healthStatus === 'unavailable') {
      setHealthStatus('checking');
    }

    let delay = initialDelayMs;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      if (activeLoopIdRef.current !== currentLoopId) break;

      try {
        // Attempt single health check with a 6-second timeout
        const data = await probeHealth({ timeoutMs: 6000 });
        if (activeLoopIdRef.current !== currentLoopId) break;

        if (data && data.status === 'healthy') {
          setBackendHealth(data);
          setHealthStatus('ready');
          setHealthError(null);
          setIsHealthChecking(false);
          return data;
        }
      } catch (err) {
        if (activeLoopIdRef.current !== currentLoopId) break;

        // Safe console diagnostic without leaking secrets
        if (typeof console !== 'undefined' && console.warn) {
          console.warn(`[VectorHire] Health probe attempt ${attempt + 1}/${maxRetries + 1} failed:`, err?.message);
        }

        // On failure before last retry, transition to waking_up (Render cold start)
        if (attempt < maxRetries) {
          setHealthStatus('waking_up');
          // Wait with progressive backoff before next attempt
          await new Promise((resolve) => {
            pollTimerRef.current = setTimeout(resolve, delay);
          });
          if (activeLoopIdRef.current !== currentLoopId) break;
          delay = Math.min(delay + 1000, 6000);
        } else {
          // Bounded retries exhausted
          setBackendHealth({ status: 'unreachable' });
          setHealthStatus('unavailable');
          setHealthError(err?.message || 'Unable to connect to the evaluation service.');
        }
      }
    }

    if (activeLoopIdRef.current === currentLoopId) {
      setIsHealthChecking(false);
    }
    return null;
  }, [backendHealth, healthStatus, probeHealth]);

  /**
   * Manual refresh/check method exposed to UI components.
   */
  const checkHealth = useCallback(async () => {
    return warmUpBackend({ isManualRetry: true, maxRetries: 4, initialDelayMs: 2000 });
  }, [warmUpBackend]);

  /**
   * Ensures backend is ready before triggering intensive actions (e.g., Evaluate Resumes).
   */
  const ensureBackendReady = useCallback(async () => {
    if (backendHealth?.status === 'healthy') {
      return true;
    }
    const result = await warmUpBackend({ isManualRetry: false, maxRetries: 4, initialDelayMs: 2500 });
    return result?.status === 'healthy';
  }, [backendHealth, warmUpBackend]);

  // Initial mount: immediately warm backend in the background without blocking render
  useEffect(() => {
    warmUpBackend({ isManualRetry: false, maxRetries: 5, initialDelayMs: 2000 });
    return () => {
      activeLoopIdRef.current++;
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
   * Executes batch resume screening via POST /analyze-resumes-stream with genuine stage handling
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

    // If backend is waking up or not yet confirmed ready, attempt readiness check first
    if (backendHealth?.status !== 'healthy') {
      setEvaluationPhase('Waking up VectorHire evaluation service...');
      setIsScreening(true);
      setActiveStepInternal('evaluation');
      setCurrentStageIndex(0);
      setCompletedStages([]);
      
      const ready = await ensureBackendReady();
      if (!ready) {
        setErrorMessage('The evaluation service is temporarily unavailable. Please try again in a moment.');
        setIsScreening(false);
        setActiveStepInternal('resumes');
        return;
      }
    }

    setIsScreening(true);
    setActiveStepInternal('evaluation');
    setCurrentStageIndex(0);
    setCompletedStages([]);
    setEvaluationPhase('Validating candidate document format, integrity, and resume structure...');
    setErrorMessage(null);

    try {
      const result = await api.analyzeResumesStream({
        files: selectedFiles,
        jobSpec: jobSpec,
        onStageStart: ({ stage_index, message, stage_title }) => {
          setCurrentStageIndex(stage_index);
          if (message) setEvaluationPhase(message);
        },
        onStageComplete: ({ stage_index, message }) => {
          setCompletedStages((prev) => (prev.includes(stage_index) ? prev : [...prev, stage_index]));
          if (stage_index < 4) {
            setCurrentStageIndex(stage_index + 1);
          }
          if (message) setEvaluationPhase(message);
        },
      });

      setCompletedStages([0, 1, 2, 3, 4]);
      setCurrentStageIndex(5); // all stages complete

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
    setCompletedStages([]);
  };

  const value = {
    backendHealth,
    healthStatus,
    healthError,
    isHealthChecking,
    checkHealth,
    warmUpBackend,
    ensureBackendReady,
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
    completedStages,
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
