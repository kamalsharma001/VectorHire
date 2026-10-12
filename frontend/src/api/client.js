/**
 * VectorHire API Client.
 * Connects directly to the FastAPI REST backend endpoints.
 * Centralizes endpoint URLs, payload formatting, error unwrapping, and network resilience.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

class ApiError extends Error {
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
   * Verifies backend readiness, active Groq LLM model, embedding model, and operational limits.
   */
  async getHealth() {
    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });
      return await handleResponse(response);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Unable to connect to VectorHire backend API. Is the server running on port 8000?', 0);
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
