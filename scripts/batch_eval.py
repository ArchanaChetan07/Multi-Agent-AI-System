#!/usr/bin/env python3
"""Batch-eval the plan→route→observe→revise orchestrator (DEMO_MODE by default).

Measures task completion rate, routing accuracy (against labeled intents),
revision rate, and end-to-end latency. Writes artifacts/batch_metrics.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Default offline — CI and local demo must not require API keys.
os.environ.setdefault("DEMO_MODE", "1")

from multi_agent.batch_metrics import (  # noqa: E402
    benchmark_tasks,
    compute_batch_metrics,
    is_completed_run,
    routing_roles_match,
)
from multi_agent.orchestrator import AgentOrchestrator  # noqa: E402


def run_batch(*, demo: bool = True) -> dict:
    orch = AgentOrchestrator(demo=demo)
    tasks = benchmark_tasks()
    rows: list[dict] = []
    live_fallback_detected = False

    for task in tasks:
        t0 = time.perf_counter()
        result = orch.run(task.text)
        latency_s = time.perf_counter() - t0
        execution_sources: list[str] = []
        task_fallback_detected = False
        for observation in result.observations:
            if observation.get("role") == "finance":
                source = str(observation.get("source") or "unknown")
                execution_sources.append(source)
                task_fallback_detected |= not demo and source == "demo"
            elif observation.get("role") == "web_search":
                hits = observation.get("hits") or []
                source = "duckduckgo" if hits else "no-results"
                if any(
                    "example.com" in str(hit.get("url") or "")
                    or "[DEMO]" in str(hit.get("snippet") or "")
                    for hit in hits
                ):
                    source = "demo"
                    task_fallback_detected = not demo
                execution_sources.append(source)
        live_fallback_detected |= task_fallback_detected

        plan_roles = [s["agent_role"] for s in result.plan]
        kinds = [e["kind"] for e in result.trace]
        routing_scored = task.should_complete
        routing_ok = (
            routing_roles_match(plan_roles, task.expected_kind) if routing_scored else False
        )

        if not task.should_complete:
            failure_note = "empty/whitespace task rejected"
        elif not routing_ok:
            failure_note = (
                f"expected_kind={task.expected_kind} but plan_roles={plan_roles}"
            )
        else:
            failure_note = None

        completed = is_completed_run(
            answer=result.answer,
            trace_kinds=kinds,
            should_complete=task.should_complete,
        )
        if not task.should_complete:
            completed = False

        rev_count = len(result.revisions)
        rows.append(
            {
                "task_id": task.task_id,
                "expected_kind": task.expected_kind,
                "should_complete": task.should_complete,
                "plan_roles": plan_roles,
                "completed": completed,
                "routing_scored": routing_scored,
                "routing_correct": routing_ok,
                "revised": rev_count > 0,
                "revision_count": rev_count,
                "latency_s": round(latency_s, 6),
                "execution_sources": execution_sources,
                "demo_fallback_detected": task_fallback_detected,
                "failure_note": failure_note,
                "trace_kinds": kinds,
            }
        )

    metrics = compute_batch_metrics(rows)
    metrics["mode"] = (
        "DEMO_MODE"
        if demo
        else ("LIVE_WITH_DEMO_FALLBACK" if live_fallback_detected else "LIVE")
    )
    metrics["live_fallback_detected"] = live_fallback_detected if not demo else False
    metrics["per_task"] = rows
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multi-agent batch outcome metrics")
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Request live tools; artifacts are labeled LIVE_WITH_DEMO_FALLBACK "
            "if any deterministic fallback is detected"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts" / "batch_metrics.json",
        help="Output JSON path",
    )
    args = parser.parse_args(argv)

    demo = not args.live
    if demo:
        os.environ["DEMO_MODE"] = "1"

    metrics = run_batch(demo=demo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Compact public summary without huge per_task dump duplication for README consumers
    public = {k: v for k, v in metrics.items() if k != "per_task"}
    public["per_task_count"] = len(metrics.get("per_task") or [])
    # Keep misroutes + incomplete for honest failure reporting
    args.out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps(public, indent=2))
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
