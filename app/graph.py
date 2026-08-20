from __future__ import annotations

import json
import os
from typing import Any, Dict
from html import escape

import markdown
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from dotenv import load_dotenv

from app.prompts import ANSWER_SYSTEM_PROMPT, DISCLAIMER_TEXT, PLANNER_SYSTEM_PROMPT
from app.schemas import AgentState, AskResponse, SourceItem
from app.tools import render_context, search_pubmed, search_web_fallback


load_dotenv()


URGENT_KEYWORDS = {
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "stroke",
    "fainting",
    "seizure",
    "suicidal",
    "unconscious",
    "severe bleeding",
}


def _get_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def _default_route(question: str) -> tuple[str, str]:
    lowered = question.lower()
    direct_keywords = ("what is", "explain", "define", "meaning of", "what does")
    if any(lowered.startswith(keyword) for keyword in direct_keywords) and len(lowered.split()) < 12:
        return "direct_answer", "Short educational question, so a high-level answer is enough."
    return "search_pubmed", "The question benefits from evidence-backed retrieval."


def planner_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"]
    fallback_route, fallback_reason = _default_route(question)
    try:
        parser = JsonOutputParser()
        llm = _get_llm()
        message = llm.invoke(
            [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=f"Question: {question}"),
            ]
        )
        parsed = parser.parse(message.content)
        route = parsed.get("route", fallback_route)
        if route not in {"search_pubmed", "direct_answer"}:
            route = fallback_route
        reasoning_summary = parsed.get("reasoning_summary", fallback_reason)
    except Exception:
        route = fallback_route
        reasoning_summary = fallback_reason

    return {
        "route": route,
        "reasoning_summary": reasoning_summary,
        "retrieval_used": route == "search_pubmed",
        "sources": [],
        "retrieved_context": "",
    }


def pubmed_search_node(state: AgentState) -> Dict[str, Any]:
    sources = search_pubmed(state["question"])
    return {
        "sources": sources,
        "retrieved_context": render_context(sources),
    }


def web_fallback_node(state: AgentState) -> Dict[str, Any]:
    sources = search_web_fallback(state["question"])
    return {
        "sources": state.get("sources", []) + sources,
        "retrieved_context": render_context(state.get("sources", []) + sources),
        "retrieval_used": True,
        "reasoning_summary": "PubMed results were limited, so the agent added a general web source for background context.",
    }


def answer_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"]
    context = state.get("retrieved_context", "")
    route = state.get("route", "direct_answer")

    fallback_answer = (
        "Here is a general explanation based on the available information.\n\n"
        "## What this usually means\n"
        "- This response is educational and should not replace care from a licensed clinician.\n"
        "- The available context may be limited, so specific diagnosis or treatment choices should be confirmed professionally.\n\n"
        "## Common next steps\n"
        "- Review symptoms, timing, and any current medicines with a healthcare professional.\n"
        "- Use the listed sources as background, not as a personal treatment plan.\n"
    )
    fallback_confidence = "low" if route == "direct_answer" and not context else "medium"

    try:
        llm = _get_llm()
        message = llm.invoke(
            [
                SystemMessage(content=ANSWER_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Question: {question}\n\n"
                        f"Route: {route}\n\n"
                        f"Context:\n{context or 'No external context retrieved.'}"
                    )
                ),
            ]
        )
        parsed = _parse_json_content(message.content)
        answer = parsed.get("answer", fallback_answer)
        confidence = parsed.get("confidence", fallback_confidence)
        if confidence not in {"low", "medium", "high"}:
            confidence = fallback_confidence
    except Exception:
        answer = fallback_answer
        confidence = fallback_confidence

    return {
        "answer": answer,
        "confidence": confidence,
    }

def safety_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"].lower()
    urgent = any(keyword in question for keyword in URGENT_KEYWORDS)
    answer = state["answer"]
    if urgent:
        answer = (
            "Your question mentions symptoms that can be serious. "
            "If this is happening now, seek urgent medical care or emergency help immediately.\n\n"
            + answer
        )
    return {
        "answer": answer,
        "needs_urgent_care": urgent,
        "disclaimer": DISCLAIMER_TEXT,
    }


def formatter_node(state: AgentState) -> Dict[str, Any]:
    response = AskResponse(
        question=state["question"],
        answer=state["answer"],
        sources=[source if isinstance(source, SourceItem) else SourceItem.model_validate(source) for source in state.get("sources", [])],
        confidence=state.get("confidence", "low"),
        needs_urgent_care=state.get("needs_urgent_care", False),
        disclaimer=state.get("disclaimer", DISCLAIMER_TEXT),
        reasoning_summary=state.get("reasoning_summary", "Completed the healthcare response workflow."),
        retrieval_used=state.get("retrieval_used", False),
    )
    return response.model_dump()


def render_answer_markdown(answer: str) -> str:
    safe_markdown = escape(answer)
    return markdown.markdown(
        safe_markdown,
        extensions=["extra", "nl2br", "sane_lists"],
    )


def _planner_route(state: AgentState) -> str:
    return state.get("route", "direct_answer")


def _post_pubmed_route(state: AgentState) -> str:
    return "web_fallback" if not state.get("sources") else "answer"


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("pubmed_search", pubmed_search_node)
    builder.add_node("web_fallback", web_fallback_node)
    builder.add_node("answer_step", answer_node)
    builder.add_node("safety_step", safety_node)
    builder.add_node("formatter_step", formatter_node)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        _planner_route,
        {
            "search_pubmed": "pubmed_search",
            "direct_answer": "answer_step",
        },
    )
    builder.add_conditional_edges(
        "pubmed_search",
        _post_pubmed_route,
        {
            "answer": "answer_step",
            "web_fallback": "web_fallback",
        },
    )
    builder.add_edge("web_fallback", "answer_step")
    builder.add_edge("answer_step", "safety_step")
    builder.add_edge("safety_step", "formatter_step")
    builder.add_edge("formatter_step", END)
    return builder.compile()


graph = build_graph()


def run_agent(question: str) -> AskResponse:
    result = graph.invoke({"question": question})
    return AskResponse.model_validate(result)
