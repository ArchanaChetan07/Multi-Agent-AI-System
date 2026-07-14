"""Labeled task batch and pure metric helpers for orchestrator offline eval.

Known-correct routing labels are attached to each sample so routing accuracy
is measurable (not post-hoc). Adversarial cases intentionally mention finance
keywords in non-finance questions to surface misrouting honestly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Sequence

ExpectedKind = Literal["finance", "web_search", "both"]


@dataclass(frozen=True)
class LabeledTask:
    task_id: str
    text: str
    expected_kind: ExpectedKind
    """Primary intended path used for routing-accuracy scoring."""

    should_complete: bool = True
    """False for empty/invalid inputs expected to fail gracefully."""


def benchmark_tasks() -> list[LabeledTask]:
    """Fixed batch spanning finance, web-search, dual-path, and adversarial cases."""
    tasks: list[LabeledTask] = []

    finance_prompts = [
        "What is the stock price of AAPL?",
        "Lookup NVDA finance fundamentals",
        "Give me the ticker price for TSLA",
        "Analyst recommendation for MSFT only",
        "Share AAPL stock fundamentals only",
        "Finance overview for AMZN ticker",
        "Current stock price quote for META",
        "What is GOOGL stock price right now?",
        "NVDA analyst recommendation summary",
        "TSLA finance metrics only",
        "MSFT stock fundamentals check",
        "AAPL ticker price snapshot",
    ]
    for i, text in enumerate(finance_prompts):
        tasks.append(
            LabeledTask(task_id=f"fin-{i:02d}", text=text, expected_kind="finance")
        )

    web_prompts = [
        "What is happening with renewable energy policy?",
        "Search for context on electric vehicle adoption trends",
        "Summarize web discussion about climate tech startups",
        "Latest news about chip fabrication capacity",
        "Web search: progress in solid-state batteries",
        "Find background on grid-scale storage deployments",
        "What are researchers saying about fusion energy?",
        "Search the web for open-source LLM tooling updates",
        "Summarize recent articles on edge computing",
        "News roundup: autonomous delivery robots",
        "Web context for urban heat-island mitigation",
        "Search for overviews of federated learning",
    ]
    for i, text in enumerate(web_prompts):
        tasks.append(
            LabeledTask(task_id=f"web-{i:02d}", text=text, expected_kind="web_search")
        )

    both_prompts = [
        "Summarize analyst recommendation and share the latest news for NVDA",
        "AAPL stock price plus latest news search",
        "Finance fundamentals and web news for MSFT",
        "Lookup ticker recommendation and search latest headlines for TSLA",
    ]
    for i, text in enumerate(both_prompts):
        tasks.append(
            LabeledTask(task_id=f"both-{i:02d}", text=text, expected_kind="both")
        )

    # Adversarial: finance keyword present, but intent is general web/knowledge.
    # Expected primary path is web_search; keyword planner often misroutes to finance.
    adversarial = [
        (
            "adv-00",
            "What is the historical price of art auctions in London?",
            "web_search",
        ),
        (
            "adv-01",
            "MSFT Excel tips for beginners learning spreadsheets",
            "web_search",
        ),
        (
            "adv-02",
            "Best restaurant recommendation near downtown for weekend brunch",
            "web_search",
        ),
    ]
    for task_id, text, kind in adversarial:
        tasks.append(
            LabeledTask(
                task_id=task_id,
                text=text,
                expected_kind=kind,  # type: ignore[arg-type]
            )
        )

    # Graceful-failure case: empty task should not count as a completed answer.
    tasks.append(
        LabeledTask(
            task_id="fail-empty",
            text="   ",
            expected_kind="web_search",
            should_complete=False,
        )
    )

    return tasks


def routing_roles_match(plan_roles: Sequence[str], expected_kind: ExpectedKind) -> bool:
    """Score whether planned agent roles match the labeled intent."""
    roles = list(plan_roles)
    if expected_kind == "finance":
        return "finance" in roles and "web_search" not in roles
    if expected_kind == "web_search":
        return "web_search" in roles and "finance" not in roles
    if expected_kind == "both":
        return roles == ["finance", "web_search"]
    return False


def is_completed_run(
    *,
    answer: str,
    trace_kinds: Iterable[str],
    should_complete: bool,
) -> bool:
    """A completed run reaches a valid final answer without erroring out."""
    kinds = set(trace_kinds)
    answer_l = (answer or "").strip().lower()
    if not should_complete:
        # Expected failure: empty/invalid — count as non-completion of a successful task.
        return False
    if not answer_l:
        return False
    if "cannot be empty" in answer_l:
        return False
    if "error" in kinds and "finish" not in kinds:
        return False
    return "finish" in kinds


def compute_batch_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate completion / routing / revision / latency from per-task rows.

    Each row keys:
      completed: bool
      routing_correct: bool
      routing_scored: bool (default True) — False excludes empty/invalid from routing %
      revised: bool
      revision_count: int
      latency_s: float
      expected_kind: str
      task_id: str
      plan_roles: list[str]
      failure_note: str | None
    """
    n = len(rows)
    if n == 0:
        return {
            "n_tasks": 0,
            "completion_rate": 0.0,
            "routing_accuracy": 0.0,
            "revision_rate": 0.0,
            "avg_revisions_per_run": 0.0,
            "avg_latency_s": 0.0,
            "failure_patterns": [],
        }

    completed = sum(1 for r in rows if r.get("completed"))
    scored = [r for r in rows if r.get("routing_scored", True)]
    routed_ok = sum(1 for r in scored if r.get("routing_correct"))
    n_routed = len(scored) or 1
    revised = sum(1 for r in rows if r.get("revised"))
    rev_counts = [int(r.get("revision_count") or 0) for r in rows]
    latencies = [float(r.get("latency_s") or 0.0) for r in rows]

    misroutes = [
        {
            "task_id": r.get("task_id"),
            "expected_kind": r.get("expected_kind"),
            "plan_roles": r.get("plan_roles"),
            "note": r.get("failure_note") or "routing mismatch",
        }
        for r in scored
        if not r.get("routing_correct")
    ]
    incomplete = [
        {
            "task_id": r.get("task_id"),
            "note": r.get("failure_note") or "did not complete",
        }
        for r in rows
        if not r.get("completed")
    ]

    return {
        "n_tasks": n,
        "n_routing_scored": len(scored),
        "completed": completed,
        "completion_rate": round(100.0 * completed / n, 1),
        "routing_correct": routed_ok,
        "routing_accuracy": round(100.0 * routed_ok / n_routed, 1),
        "revised_runs": revised,
        "revision_rate": round(100.0 * revised / n, 1),
        "avg_revisions_per_run": round(sum(rev_counts) / n, 3),
        "avg_latency_s": round(sum(latencies) / n, 4),
        "misroutes": misroutes,
        "incomplete": incomplete,
        "failure_patterns": _summarize_failure_patterns(misroutes, incomplete),
    }


def _summarize_failure_patterns(
    misroutes: list[dict[str, Any]], incomplete: list[dict[str, Any]]
) -> list[str]:
    patterns: list[str] = []
    if misroutes:
        patterns.append(
            "Keyword planner misroutes when non-finance questions contain "
            "finance trigger tokens (price, recommendation, ticker substrings like MSFT)."
        )
    if incomplete:
        patterns.append(
            "Empty/whitespace tasks return a rejection answer and do not finish successfully."
        )
    return patterns
