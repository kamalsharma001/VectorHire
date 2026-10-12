# VectorHire Frontend SPA

Vite + React single-page application providing a modern, 5-stage recruiter screening workflow with interactive evidence provenance inspection.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

The application runs locally on `http://localhost:5173`.

## Production Build & Tests

```bash
# Run unit & workflow test suite (22 tests in Vitest)
npm test -- --run

# Compile production bundle
npm run build
```

## Directory Structure

```
frontend/
├── src/
│   ├── api/             # Centralized API client & HTTP error unwrapping
│   ├── components/      # Modular UI components (common, layout, intake, screening, evidence)
│   ├── constants/       # Taxonomy & status enums
│   ├── context/         # ScreeningSessionContext state management
│   └── test/            # Vitest unit & integration test files
├── public/              # Static public assets
├── package.json
├── vercel.json          # Vercel SPA rewrite rules
└── .env.example         # Environment template
```
