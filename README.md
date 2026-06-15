# 80k RAG Assistant

An AI career assistant that answers questions using a RAG pipeline over 80,000 Hours
articles, with inline, verifiable citations that link to the exact text in the source.

- **Frontend:** Next.js (App Router) + React + Tailwind
- **Backend:** FastAPI (`api/index.py`) — a Python serverless function on Vercel
- **Retrieval:** Qdrant vector search + OpenAI embeddings (`text-embedding-3-small`)
- **Generation:** Anthropic Claude (`claude-sonnet-4-6`) with structured, validated citations

## Getting Started

### Prerequisites

- Node.js + npm
- Python 3.12 with the virtualenv set up:
  ```bash
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
  ```
- A `.env` file with: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`

### Run the dev servers

```bash
npm install
npm run dev
```

This starts **both** servers together via `concurrently`:

- `web` — Next.js on http://localhost:3000
- `api` — FastAPI/uvicorn on http://localhost:8000

In development, Next proxies `/api/*` to the local Python backend (see the dev-only
`rewrites()` in `next.config.ts`). In production on Vercel, that proxy is a no-op and the
`vercel.json` rewrite routes `/api/*` to the Python function instead.

> Note: `vercel dev` is not used — it doesn't run the Python function with this
> Next.js 16 + Turbopack setup. The two-process script above is the supported workflow.

Run a single side if needed: `npm run dev:web` or `npm run dev:api`.

## Deploy

Deployed on Vercel. `requirements.txt` defines the Python function's dependencies and
`vercel.json` handles `/api/*` routing.
