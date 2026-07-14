"""Web search tool with deterministic DEMO_MODE results."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


def _demo_hits(query: str) -> list[SearchHit]:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:8]
    return [
        SearchHit(
            title=f"Demo result for: {query}",
            url=f"https://example.com/demo/{digest}",
            snippet=(
                f"[DEMO] Synthetic search hit for '{query}'. "
                "Replace with DuckDuckGo / live search when API access is configured."
            ),
        ),
        SearchHit(
            title=f"Background context ({digest})",
            url=f"https://example.com/context/{digest}",
            snippet="[DEMO] Secondary deterministic context article for offline tests.",
        ),
    ]


def web_search(query: str, *, demo: bool = True) -> list[SearchHit]:
    query = (query or "").strip()
    if not query:
        return []
    if demo:
        return _demo_hits(query)
    try:
        from duckduckgo_search import DDGS

        hits: list[SearchHit] = []
        with DDGS() as ddgs:
            for row in ddgs.text(query, max_results=5):
                hits.append(
                    SearchHit(
                        title=row.get("title") or "Untitled",
                        url=row.get("href") or row.get("link") or "",
                        snippet=row.get("body") or row.get("snippet") or "",
                    )
                )
        return hits or _demo_hits(query)
    except Exception:
        return _demo_hits(query)
