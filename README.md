# VectorHire — Evidence-Driven Resume Intelligence

Turn batches of resumes into explainable, evidence-backed candidate comparisons.

VectorHire is an AI-assisted recruitment screening tool that evaluates multiple resumes against a single job description. It combines semantic and lexical matching, structured requirements, evidence verification, and deterministic scoring to help recruiters understand how candidates compare and what supports each assessment.

- **Live Demo:** `[Add live demo URL after deployment]`

> **Important:** VectorHire is a recruiter decision-support tool, not an autonomous hiring system. Final hiring decisions remain with humans.

---

## The Problem

Resume screening can be inconsistent when it relies on keyword matching alone or unverified AI-generated judgments. Relevant experience may be expressed using different terminology, while a keyword appearing in a resume does not necessarily demonstrate competency.

VectorHire addresses this challenge by connecting candidate assessments to resume evidence and applying a structured, consistent evaluation process.

---

## Key Features

- **Dynamic job requirements:** Extract and structure requirements from a job description into a job-specific rubric.
- **Batch resume screening:** Evaluate up to 10 resumes in one screening session.
- **Hybrid matching:** Combine semantic similarity, lexical matching, and controlled terminology normalization.
- **Evidence provenance:** Validate extracted evidence against source text and character offsets.
- **Contextual verification:** Assess whether evidence genuinely supports a requirement, accounting for negation and disclaimers.
- **Deterministic scoring:** Calculate candidate scores using normalized requirement weights rather than asking an LLM to invent the final score.
- **Hard-gate handling:** Keep specified eligibility requirements distinguishable from overall match scores and flag cases requiring human review.
- **Uncertainty awareness:** Distinguish supported, uncertain, missing, and contradictory or unverifiable evidence.
- **Interview preparation:** Generate targeted interview questions based on requirements and evidence gaps.
- **Provider resilience:** Use Google Gemini as the configured primary LLM, with Groq as the cross-provider fallback.


## How It Works

```
Job Description
      │
      ▼
Requirement Extraction and Dynamic Rubric
      │
      ▼
Resume Upload and Document Validation
      │
      ▼
Semantic and Lexical Evidence Retrieval
      │
      ▼
Source Provenance and Contextual Verification
      │
      ▼
Deterministic Scoring and Eligibility Checks
      │
      ▼
Candidate Comparison and Interview Questions
```

### LLM interpretation, deterministic scoring

LLMs help interpret job descriptions, structure requirements, evaluate contextual evidence, and generate interview questions. Evidence provenance checks validate extracted source text. The deterministic scoring engine calculates final scores using the active rubric, while hard-gate results remain separately identifiable.

This separation reduces dependence on unconstrained LLM-generated scores, but it does not eliminate model errors or guarantee that every assessment is correct.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, JavaScript, Vite, Tailwind CSS |
| **Backend** | Python, FastAPI, Pydantic v2, Uvicorn |
| **Primary LLM** | Google Gemini (`gemini-2.5-flash`) |
| **Fallback LLM** | Groq Cloud, with configured model fallbacks (`openai/gpt-oss-20b`, `qwen/qwen3.8-27b`) |
| **Embeddings** | FastEmbed, `BAAI/bge-small-en-v1.5` |
| **Matching and scoring** | Semantic and lexical matching, deterministic rubric scoring |
| **Document processing** | PDF text extraction, DOCX and TXT support |
| **Testing tools** | Pytest and Vitest |

---

## Project Structure

```text
VectorHire/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── orchestration/
│   │   ├── providers/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vercel.json
│   └── .env.example
├── screenshots/
├── render.yaml
├── LICENSE
└── README.md
```

---

## Getting Started

### Prerequisites

- Python version supported by the backend dependencies (Python 3.10+ recommended).
- Node.js and npm.
- API keys for the LLM providers you intend to use for live evaluation.

### 1. Set up the backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` file using `backend/.env.example` as the reference. Configure your provider keys and required settings. Never commit real credentials.

Start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend runs at `http://localhost:8000`. API documentation is available at `http://localhost:8000/docs` if enabled by the application configuration.

### 2. Set up the frontend

Open a separate terminal from the repository root:

```bash
cd frontend
npm install
```

Create a local `.env` file using `frontend/.env.example` and configure the backend URL:

```env
VITE_API_BASE_URL=http://localhost:8000
```

*(For local development with the Vite proxy, `VITE_API_BASE_URL` can also be left empty).*

Start the frontend:

```bash
npm run dev
```

Open the local URL printed by Vite (typically `http://localhost:5173`).

---

## Deployment

VectorHire is configured for separate backend and frontend hosting.

### Backend — Render

The root `render.yaml` defines the backend service configuration.

- **Root directory:** `backend`
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check:** `/health`

Configure the required provider keys, model settings, and CORS origins in the Render service environment.

### Frontend — Vercel

Deploy the `frontend/` directory as a Vite application.

- **Root directory:** `frontend`
- **Build command:** `npm run build`
- **Output directory:** `dist`
- **API URL:** Set `VITE_API_BASE_URL` to the deployed backend URL.

The existing `frontend/vercel.json` provides SPA routing support. Configure the backend CORS allowlist to include the deployed frontend origin.

> **Deployment status:** The repository contains deployment configuration, but the live demo URL must be added only after a public deployment has been completed and verified.

---

## Privacy and Responsible Use

- Screening sessions use in-memory application state rather than a persistent candidate repository.
- Uploaded files may pass through temporary processing or framework-managed upload buffers. In-memory sessions alone do not guarantee that no temporary files are created.
- PDF processing requires an extractable text layer. Scanned image-only PDFs may not be readable without OCR.
- Current operational limits are up to 10 resumes per batch and 10 MB per file, subject to active configuration.
- Missing evidence is not proof that a candidate lacks a skill.
- Candidate scores, evidence, and eligibility flags should be reviewed by a human. VectorHire should not be the sole basis for employment decisions.

---

## Limitations

- Evaluation quality depends on resume quality, job-description clarity, model behavior, and the available evidence.
- Provider availability, rate limits, quotas, and latency can affect processing.
- Passing automated tests does not prove live provider availability or guarantee real-world hiring accuracy.
- OCR, persistent candidate management, and external ATS integrations should not be assumed unless separately implemented.

---

## Author

**Kamal Sharma**  
CSE AIML  
Chandigarh University  
GitHub: [kamalsharma001](https://github.com/kamalsharma001)
