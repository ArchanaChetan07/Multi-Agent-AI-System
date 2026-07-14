"""Tests for batch-eval metric helpers (completion rate, routing accuracy)."""

from __future__ import annotations

import os

os.environ["DEMO_MODE"] = "1"

from multi_agent.batch_metrics import (
    benchmark_tasks,
    compute_batch_metrics,
    is_completed_run,
    routing_roles_match,
)
from multi_agent.orchestrator import AgentOrchestrator
from scripts.batch_eval import run_batch


class TestRoutingAccuracyHelpers:
    def test_finance_only_correct(self):
        assert routing_roles_match(["finance"], "finance") is True
        assert routing_roles_match(["finance", "web_search"], "finance") is False

    def test_web_only_correct(self):
        assert routing_roles_match(["web_search"], "web_search") is True
        assert routing_roles_match(["finance"], "web_search") is False

    def test_both_requires_ordered_pair(self):
        assert routing_roles_match(["finance", "web_search"], "both") is True
        assert routing_roles_match(["web_search", "finance"], "both") is False


class TestCompletionHelpers:
    def test_finish_marks_complete(self):
        assert (
            is_completed_run(
                answer="Task: hello\nMode: DEMO",
                trace_kinds=["start", "plan", "route", "observe", "finish"],
                should_complete=True,
            )
            is True
        )

    def test_empty_rejection_not_complete(self):
        assert (
            is_completed_run(
                answer="Task cannot be empty",
                trace_kinds=["start", "error"],
                should_complete=True,
            )
            is False
        )

    def test_expected_failure_never_complete(self):
        assert (
            is_completed_run(
                answer="anything",
                trace_kinds=["finish"],
                should_complete=False,
            )
            is False
        )


class TestComputeBatchMetrics:
    def test_completion_and_routing_rates(self):
        rows = [
            {
                "task_id": "a",
                "completed": True,
                "routing_correct": True,
                "routing_scored": True,
                "revised": False,
                "revision_count": 0,
                "latency_s": 0.01,
                "expected_kind": "finance",
                "plan_roles": ["finance"],
            },
            {
                "task_id": "b",
                "completed": True,
                "routing_correct": False,
                "routing_scored": True,
                "revised": True,
                "revision_count": 1,
                "latency_s": 0.02,
                "expected_kind": "web_search",
                "plan_roles": ["finance"],
                "failure_note": "misroute",
            },
            {
                "task_id": "c",
                "completed": False,
                "routing_correct": False,
                "routing_scored": False,
                "revised": False,
                "revision_count": 0,
                "latency_s": 0.001,
                "expected_kind": "web_search",
                "plan_roles": [],
                "failure_note": "empty",
            },
        ]
        m = compute_batch_metrics(rows)
        assert m["n_tasks"] == 3
        assert m["completion_rate"] == 66.7  # 2/3
        assert m["n_routing_scored"] == 2
        assert m["routing_accuracy"] == 50.0  # 1/2
        assert m["revision_rate"] == 33.3  # 1/3
        assert m["avg_revisions_per_run"] == round(1 / 3, 3)
        assert len(m["misroutes"]) == 1
        assert len(m["incomplete"]) == 1
        assert m["failure_patterns"]


class TestBatchEvalIntegration:
    def test_benchmark_covers_both_paths(self):
        tasks = benchmark_tasks()
        kinds = {t.expected_kind for t in tasks}
        assert "finance" in kinds and "web_search" in kinds and "both" in kinds
        assert any(not t.should_complete for t in tasks)
        assert len(tasks) >= 20

    def test_run_batch_demo_produces_metrics(self):
        metrics = run_batch(demo=True)
        assert metrics["mode"] == "DEMO_MODE"
        assert metrics["n_tasks"] >= 20
        assert 0.0 <= metrics["completion_rate"] <= 100.0
        assert 0.0 <= metrics["routing_accuracy"] <= 100.0
        assert "failure_patterns" in metrics
        # Smoke: adversarial cases should produce at least one misroute in this batch
        assert metrics["routing_accuracy"] < 100.0

    def test_orchestrator_demo_loop_full_cycle(self):
        orch = AgentOrchestrator(demo=True)
        result = orch.run(
            "Summarize analyst recommendation and share the latest news for NVDA"
        )
        kinds = [e["kind"] for e in result.trace]
        assert kinds[0] == "start"
        assert "plan" in kinds and "route" in kinds and "observe" in kinds
        assert "finish" in kinds
        assert result.demo_mode is True
