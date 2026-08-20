# ClinAssit Agentic AI

A LangGraph-powered healthcare agent with a FastAPI backend and a polished server-rendered web UI. It accepts a healthcare question, routes it through a small agent workflow, retrieves PubMed-backed context when needed, and returns a structured answer with sources, confidence, and safety guidance.

### Stack

- FastAPI
- LangGraph
- `langchain-openai`
- HTMX
- Mermaid
- Markdown rendering
- PubMed E-utilities + public web fallback

## Features

- Browser-based healthcare question flow
- LangGraph planner + retrieval + answer + safety pipeline
- PubMed-first retrieval with fallback context
- Markdown-formatted patient-friendly answers
- Confidence level, safety notice, and source attribution
- Workflow diagram in the UI
- Lightweight loading state and skeleton response UI

## Project Structure

```text
api/
  index.py
app/
  frontend/
    app.js
    index.html
    styles.css
  templates/
    result.html
  graph.py
  main.py
  prompts.py
  schemas.py
  tools.py
  __init__.py
.env.example
.gitignore
render.yaml
requirements.txt
vercel.json
README.md
```

## Local Setup

### 1. Create a virtual environment

Use Python 3.12 for the smoothest install path.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Add environment variables

Create a local `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Run Locally

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## API Endpoints

- `GET /`
  Serves the web app

- `POST /api/ask`
  Returns JSON response data

- `POST /ui/ask`
  Returns the rendered result HTML partial used by HTMX

## Example API Response

```json
{
  "question": "What are early symptoms of diabetes?",
  "answer": "...",
  "sources": [
    {
      "title": "...",
      "url": "...",
      "source_type": "pubmed",
      "snippet": "..."
    }
  ],
  "confidence": "medium",
  "needs_urgent_care": false,
  "disclaimer": "...",
  "reasoning_summary": "...",
  "retrieval_used": true
}
```

## LangGraph Flow

```text
START
  -> planner
     -> direct answer
     -> pubmed retrieval
         -> fallback web retrieval
  -> answer
  -> safety
  -> formatter
END
```

## Deployment

### Deploy to Vercel

This repo now includes:

- [api/index.py](/c:/Users/KIIT0001/Desktop/healthcare%20agent/api/index.py)
- [vercel.json](/c:/Users/KIIT0001/Desktop/healthcare%20agent/vercel.json)

These route all requests through a Python entrypoint that imports the FastAPI app and includes the frontend/template files in the deployment bundle.

#### Vercel dashboard flow

1. Push the repo to GitHub.
2. Import the repo into Vercel.
3. In Project Settings, add:
   - `OPENAI_API_KEY`
4. Deploy.

#### Vercel CLI flow

```bash
vercel login
vercel
vercel --prod
```

If prompted for environment variables, add `OPENAI_API_KEY` in the Vercel dashboard or with:

```bash
vercel env add OPENAI_API_KEY
```

### Deploy to Render

This repo now includes [render.yaml](/c:/Users/KIIT0001/Desktop/healthcare%20agent/render.yaml).

#### Render dashboard flow

1. Push the repo to GitHub.
2. In Render, create a new Web Service from the repo.
3. Render will detect `render.yaml`.
4. Add:
   - `OPENAI_API_KEY`
5. Deploy.

#### Render service settings

- Runtime: Python
- Build command:

  ```text
  pip install -r requirements.txt
  ```

- Start command:

  ```text
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

## Demo Questions

- `What are early symptoms of diabetes?`
- `How is hypertension usually managed?`
- `Chest pain and shortness of breath, what should I do?`
- `Explain HbA1c in simple words`

## Safety Notes

- This project is informational only.
- It is not a medical diagnostic system.
- It always adds a safety disclaimer.
- Urgent symptom prompts trigger stronger escalation language.

## Troubleshooting

### Python 3.13 install issues

Use Python 3.12 instead:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### `OPENAI_API_KEY is not set`

Add the key to:

- local `.env`
- Vercel project env vars
- Render service env vars

### Mermaid graph does not appear

The graph renderer uses a CDN import, so the client needs network access.

### Retrieval returns weak sources

Some broad queries do not produce strong PubMed matches. The app falls back to a broader public context source rather than failing.
