# VectorHire Backend API

FastAPI REST service providing intelligent resume screening, rubric generation, dual-stage evidence verification, and deterministic candidate scoring.

## Quick Start

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Unix:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Running Tests

```bash
python -m pytest -v
```

## Directory Structure

```
backend/
├── app/
│   ├── agents/          # Job analyzer, verifier, question generator
│   ├── api/             # REST endpoint handlers & router
│   ├── core/            # Configuration, settings & exceptions
│   ├── orchestration/   # Deterministic scoring engine & state
│   ├── providers/       # BaseLLMProvider, Gemini, Groq, FastEmbed
│   ├── schemas/         # Pydantic v2 data contracts
│   ├── services/        # Evaluation pipeline, document processing, normalizer
├── tests/               # 130 unit, integration, & benchmark tests
├── requirements.txt     # Backend dependencies
└── .env.example         # Environment template
```
