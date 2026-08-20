from __future__ import annotations

from typing import List, Literal, TypedDict
from pydantic import BaseModel, Field


ConfidenceLevel = Literal["low", "medium", "high"]
RouteName = Literal["search_pubmed", "direct_answer"]
SourceType = Literal["pubmed", "web"]


class SourceItem(BaseModel):
    title: str
    url: str
    source_type: SourceType
    snippet: str | None = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceItem]
    confidence: ConfidenceLevel
    needs_urgent_care: bool
    disclaimer: str
    reasoning_summary: str
    retrieval_used: bool


class AgentState(TypedDict, total=False):
    question: str
    route: RouteName
    retrieved_context: str
    sources: List[SourceItem]
    answer: str
    confidence: ConfidenceLevel
    needs_urgent_care: bool
    disclaimer: str
    reasoning_summary: str
    retrieval_used: bool
