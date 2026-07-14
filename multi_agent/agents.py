"""Explicit agent roles for web search and finance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from multi_agent.tools.finance import FinanceSnapshot, finance_lookup
from multi_agent.tools.web_search import SearchHit, web_search


class AgentRole(Protocol):
    name: str
    role: str

    def run(self, task: str, *, demo: bool) -> dict[str, Any]: ...


@dataclass
class WebSearchAgent:
    name: str = "Web Search Agent"
    role: str = "web_search"

    def run(self, task: str, *, demo: bool) -> dict[str, Any]:
        hits = web_search(task, demo=demo)
        return {
            "agent": self.name,
            "role": self.role,
            "query": task,
            "hits": [
                {"title": h.title, "url": h.url, "snippet": h.snippet}
                for h in hits
            ],
            "summary": _summarize_hits(hits),
        }


@dataclass
class FinanceAgent:
    name: str = "Finance AI Agent"
    role: str = "finance"

    def run(self, task: str, *, demo: bool) -> dict[str, Any]:
        snap: FinanceSnapshot = finance_lookup(task, demo=demo)
        return {
            "agent": self.name,
            "role": self.role,
            "query": task,
            "symbol": snap.symbol,
            "price": snap.price,
            "currency": snap.currency,
            "recommendation": snap.recommendation,
            "news_headlines": list(snap.news_headlines),
            "source": snap.source,
            "summary": (
                f"{snap.symbol} @ {snap.price} {snap.currency}; "
                f"recommendation={snap.recommendation}; source={snap.source}"
            ),
        }


def _summarize_hits(hits: list[SearchHit]) -> str:
    if not hits:
        return "No search results."
    lines = [f"- {h.title}: {h.snippet}" for h in hits]
    return "\n".join(lines)
