from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.graph import render_answer_markdown, run_agent
from app.schemas import AskRequest, AskResponse


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = BASE_DIR / "templates"


app = FastAPI(
    title="Healthcare Agent",
    version="1.0.0",
    description="LangGraph-powered healthcare information agent with a web frontend.",
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", include_in_schema=False)
async def read_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/ask", response_model=AskResponse)
async def ask_healthcare_agent(payload: AskRequest) -> AskResponse:
    
    try:
        return run_agent(payload.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The healthcare agent could not complete the request.",
        ) from exc


@app.post("/ui/ask", response_class=HTMLResponse, include_in_schema=False)
async def ask_healthcare_agent_partial(request: Request, question: str = Form(...)) -> HTMLResponse:
    try:
        result = run_agent(question)
        result_payload = result.model_dump()
        result_payload["answer_html"] = render_answer_markdown(result.answer)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={"result": result_payload},
        )
    except RuntimeError as exc:
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={"error_message": str(exc), "question": question},
            status_code=500,
        )
    except Exception:
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "error_message": "The healthcare agent could not complete the request.",
                "question": question,
            },
            status_code=500,
        )
