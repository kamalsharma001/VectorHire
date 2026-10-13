/**
 * VectorHire API Client.
 * Connects directly to the FastAPI REST backend endpoints.
 * Centralizes endpoint URLs, payload formatting, error unwrapping, and network resilience.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(message, status = null, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

/**
 * Parses JSON response safely, extracting FastAPI HTTPException detail if available.
 */
async function handleResponse(response) {
  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;

    if (data) {
      if (typeof data.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        // FastAPI / Pydantic validation error array
        errorMsg = data.detail
          .map((d) => (d.msg ? `${d.loc ? d.loc.slice(-1)[0] + ': ' : ''}${d.msg}` : JSON.stringify(d)))
          .join('; ');
      } else if (data.message) {
        errorMsg = data.message;
      } else if (data.error) {
        errorMsg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
      }
    }

    throw new ApiError(errorMsg, response.status, data);
  }

  return data;
}

export const api = {
  /**
   * GET /health
   * Verifies backend readiness, active LLM model, embedding model, and operational limits.
   */
  async getHealth(options = {}) {
    const { timeoutMs = 8000, signal } = options;
    const controller = new AbortController();
    const effectiveSignal = signal || controller.signal;
    let timerId = null;

    if (timeoutMs && !signal) {
      timerId = setTimeout(() => controller.abort(), timeoutMs);
    }

    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: effectiveSignal,
      });
      return await handleResponse(response);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      const isAbort = err?.name === 'AbortError' || effectiveSignal.aborted;
      const friendlyMsg = isAbort
        ? 'Backend health check timed out while waiting for a response.'
        : 'Unable to connect to the VectorHire backend evaluation service.';
      throw new ApiError(friendlyMsg, 0, { originalError: err?.message, isAbort });
    } finally {
      if (timerId) clearTimeout(timerId);
    }
  },

  /**
   * POST /analyze-job
   * Analyzes unstructured Job Description text into a validated JobSpecification and initial rubric.
   */
  async analyzeJob({ jobDescriptionText, jobTitleHint = null }) {
    if (!jobDescriptionText || jobDescriptionText.trim().length < 20) {
      throw new ApiError('Job description text must contain at least 20 characters.', 422);
    }

    try {
      const response = await fetch(`${API_BASE}/analyze-job`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          job_description_text: jobDescriptionText.trim(),
          job_title_hint: jobTitleHint ? jobTitleHint.trim() : null,
        }),
      });
      return await handleResponse(response);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || 'Failed to analyze job description.', 0);
    }
  },

  /**
   * POST /extract-job-text
   * Extracts text from an uploaded Job Description file (.pdf, .docx, or .txt).
   */
  async extractJobText(file) {
    if (!file) {
      throw new ApiError('Please select a file to extract job text from.', 400);
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/extract-job-text`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
        },
        body: formData,
      });
      return await handleResponse(response);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || 'Failed to extract text from job description file.', 0);
    }
  },

  /**
   * POST /analyze-resumes
   * Multipart batch upload of PDF resumes evaluated against a frozen JobSpecification.
   */
  async analyzeResumes({ files, jobSpec }) {
    if (!files || files.length === 0) {
      throw new ApiError('At least one PDF resume must be uploaded.', 400);
    }
    if (!jobSpec) {
      throw new ApiError('Job specification is required for candidate evaluation.', 422);
    }

    const formData = new FormData();
    for (const file of files) {
      formData.append('resumes', file);
    }
    formData.append('job_spec', JSON.stringify(jobSpec));

    try {
      const response = await fetch(`${API_BASE}/analyze-resumes`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          // Do not set Content-Type header so the browser sets boundary automatically
        },
        body: formData,
      });
      return await handleResponse(response);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || 'Batch screening evaluation failed.', 0);
    }
  },

  /**
   * POST /analyze-resumes-stream
   * Multipart batch upload with genuine real-time Server-Sent Events (SSE) stage progression.
   */
  async analyzeResumesStream({ files, jobSpec, onStageStart, onStageComplete }) {
    if (!files || files.length === 0) {
      throw new ApiError('At least one PDF resume must be uploaded.', 400);
    }
    if (!jobSpec) {
      throw new ApiError('Job specification is required for candidate evaluation.', 422);
    }

    const formData = new FormData();
    for (const file of files) {
      formData.append('resumes', file);
    }
    formData.append('job_spec', JSON.stringify(jobSpec));

    let response;
    try {
      response = await fetch(`${API_BASE}/analyze-resumes-stream`, {
        method: 'POST',
        headers: {
          Accept: 'text/event-stream',
        },
        body: formData,
      });
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || 'Unable to connect to evaluation stream.', 0);
    }

    if (!response.ok) {
      return await handleResponse(response);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let finalResult = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // Normalize CRLF to LF
        buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

        // SSE messages are delimited by a double newline
        let boundaryIndex;
        while ((boundaryIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawMessage = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + 2);

          if (!rawMessage.trim()) continue;

          let eventType = 'message';
          const dataLines = [];

          for (const line of rawMessage.split('\n')) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              // Strip optional single leading space per SSE specification
              let d = line.slice(5);
              if (d.startsWith(' ')) d = d.slice(1);
              dataLines.push(d);
            }
          }

          if (dataLines.length === 0) continue;
          const dataStr = dataLines.join('\n');

          let parsedData;
          try {
            parsedData = JSON.parse(dataStr);
          } catch {
            parsedData = dataStr;
          }

          if (eventType === 'stage_start') {
            if (onStageStart) onStageStart(parsedData);
          } else if (eventType === 'stage_complete') {
            if (onStageComplete) onStageComplete(parsedData);
          } else if (eventType === 'complete') {
            finalResult = parsedData;
          } else if (eventType === 'error') {
            const errMsg =
              typeof parsedData === 'object' && parsedData?.error
                ? parsedData.error
                : String(parsedData);
            throw new ApiError(errMsg, 422, parsedData);
          }
        }
      }

      // Check any remaining buffer upon stream completion
      if (buffer.trim()) {
        const rawMessage = buffer.trim();
        let eventType = 'message';
        const dataLines = [];
        for (const line of rawMessage.split('\n')) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            let d = line.slice(5);
            if (d.startsWith(' ')) d = d.slice(1);
            dataLines.push(d);
          }
        }
        if (dataLines.length > 0) {
          const dataStr = dataLines.join('\n');
          let parsedData;
          try {
            parsedData = JSON.parse(dataStr);
          } catch {
            parsedData = dataStr;
          }
          if (eventType === 'stage_start') {
            if (onStageStart) onStageStart(parsedData);
          } else if (eventType === 'stage_complete') {
            if (onStageComplete) onStageComplete(parsedData);
          } else if (eventType === 'complete') {
            finalResult = parsedData;
          } else if (eventType === 'error') {
            const errMsg =
              typeof parsedData === 'object' && parsedData?.error
                ? parsedData.error
                : String(parsedData);
            throw new ApiError(errMsg, 422, parsedData);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    if (!finalResult) {
      throw new ApiError('Evaluation stream finished without returning results.', 500);
    }

    return finalResult;
  },

  /**
   * POST /generate-questions
   * Generates tailored interview questions based strictly on verified evidence and identified gaps.
   */
  async generateQuestions({ candidateId, candidateName, jobSpec, scorecard, maxQuestions = 5 }) {
    try {
      const response = await fetch(`${API_BASE}/generate-questions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          candidate_id: candidateId,
          candidate_name: candidateName,
          job_spec: jobSpec,
          scorecard: scorecard,
          max_questions: maxQuestions,
        }),
      });
      return await handleResponse(response);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || 'Failed to generate interview questions.', 0);
    }
  },
};
