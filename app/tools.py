from __future__ import annotations

from typing import List
from urllib.parse import quote_plus

import httpx

from app.schemas import SourceItem


PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"


def _clean_snippet(value: str | None, limit: int = 280) -> str | None:
    if not value:
        return None
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def search_pubmed(query: str, max_results: int = 4) -> List[SourceItem]:
    
    params = {
        "db": "pubmed",
        "term": f"{query} AND (review[Publication Type] OR guideline[Publication Type] OR systematic[sb])",
        "retmode": "json",
        "retmax": max_results,
        "sort": "relevance",
    }
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            search_response = client.get(PUBMED_SEARCH_URL, params=params)
            search_response.raise_for_status()
            id_list = search_response.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            summary_response = client.get(
                PUBMED_SUMMARY_URL,
                params={
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "json",
                },
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json().get("result", {})
    except (httpx.HTTPError, ValueError):
        return []

    sources: List[SourceItem] = []
    for pubmed_id in id_list:
        item = summary_data.get(pubmed_id, {})
        title = item.get("title")
        if not title:
            continue
        authors = item.get("authors", [])
        author_text = ", ".join(author.get("name", "") for author in authors[:3] if author.get("name"))
        pubdate = item.get("pubdate", "Unknown date")
        snippet = f"{pubdate}. {author_text}".strip()
        sources.append(
            SourceItem(
                title=title.rstrip("."),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                source_type="pubmed",
                snippet=_clean_snippet(snippet),
            )
        )
    return sources


def search_web_fallback(query: str) -> List[SourceItem]:
    slug = quote_plus(query)
    
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            search_response = client.get(
                WIKI_SEARCH_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                },
            )
            search_response.raise_for_status()
            search_results = search_response.json().get("query", {}).get("search", [])
            title = search_results[0]["title"] if search_results else query

            response = client.get(f"{WIKI_SUMMARY_URL}{quote_plus(title)}")
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return [
            SourceItem(
                title=f"General background search for: {query}",
                url=f"https://medlineplus.gov/search/?query={slug}",
                source_type="web",
                snippet=_clean_snippet(
                    "A broad public-health fallback source was provided because richer web summary retrieval was unavailable."
                ),
            )
        ]

    title = data.get("title") or query.title()
    summary = data.get("extract") or "General background information was retrieved from a public web source."
    canonical = (
        data.get("content_urls", {})
        .get("desktop", {})
        .get("page")
        or f"https://en.wikipedia.org/wiki/{slug}"
    )
    return [
        SourceItem(
            title=title,
            url=canonical,
            source_type="web",
            snippet=_clean_snippet(summary),
        )
    ]


def render_context(sources: List[SourceItem]) -> str:
    if not sources:
        return "No external context was retrieved."
    chunks = []
    for index, source in enumerate(sources, start=1):
        snippet = source.snippet or "No summary available."
        chunks.append(f"[{index}] {source.title}\nType: {source.source_type}\nURL: {source.url}\nSnippet: {snippet}")
    return "\n\n".join(chunks)
