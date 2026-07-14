"""Offline unit tests for the lightweight multi-agent system."""

from __future__ import annotations

import os

import pytest

# Force demo mode for offline CI regardless of local .env
os.environ["DEMO_MODE"] = "1"

from multi_agent.agents import FinanceAgent, WebSearchAgent
from multi_agent.config import is_demo_mode
from multi_agent.orchestrator import AgentOrchestrator
from multi_agent.tools.finance import extract_ticker, finance_lookup
from multi_agent.tools.web_search import web_search
from multi_agent.tracing import Tracer


class TestConfig:
    def test_demo_mode_forced(self):
        assert is_demo_mode() is True


class TestTools:
    def test_web_search_deterministic(self):
        a = web_search("NVDA news", demo=True)
        b = web_search("NVDA news", demo=True)
        assert len(a) >= 1
        assert a[0].title == b[0].title
        assert a[0].url == b[0].url
        assert "[DEMO]" in a[0].snippet

    def test_web_search_empty_query(self):
        assert web_search("  ", demo=True) == []

    def test_extract_ticker(self):
        assert extract_ticker("latest news for NVDA") == "NVDA"
        assert extract_ticker("price of AAPL stock") == "AAPL"

    def test_finance_lookup_deterministic(self):
        a = finance_lookup("analyst recommendation for NVDA", demo=True)
        b = finance_lookup("analyst recommendation for NVDA", demo=True)
        assert a.symbol == "NVDA"
        assert a.price == b.price
        assert a.source == "demo"
        assert a.news_headlines


class TestAgents:
    def test_web_search_agent_attributes(self):
        agent = WebSearchAgent()
        assert agent.name
        assert agent.role == "web_search"
        out = agent.run("search AI chips", demo=True)
        assert out["role"] == "web_search"
        assert out["hits"]

    def test_finance_agent_attributes(self):
        agent = FinanceAgent()
        assert agent.role == "finance"
        out = agent.run("stock price TSLA", demo=True)
        assert out["symbol"] == "TSLA"
        assert "price" in out


class TestOrchestrator:
    def test_plan_routes_finance_and_search(self):
        orch = AgentOrchestrator(demo=True)
        plan = orch.plan("Summarize analyst recommendation and share the latest news for NVDA")
        roles = [s.agent_role for s in plan]
        assert roles == ["finance", "web_search"]

    def test_plan_defaults_to_search(self):
        orch = AgentOrchestrator(demo=True)
        plan = orch.plan("What is happening with renewable energy?")
        assert plan[0].agent_role == "web_search"

    def test_run_end_to_end_with_trace(self):
        orch = AgentOrchestrator(demo=True)
        result = orch.run("Summarize analyst recommendation and share the latest news for NVDA")
        assert result.demo_mode is True
        assert result.plan
        assert len(result.observations) >= 2
        assert "NVDA" in result.answer
        kinds = [e["kind"] for e in result.trace]
        assert "plan" in kinds
        assert "route" in kinds
        assert "observe" in kinds
        assert "finish" in kinds

    def test_empty_task(self):
        orch = AgentOrchestrator(demo=True)
        result = orch.run("")
        assert result.answer == "Task cannot be empty"

    def test_revision_when_no_observations(self):
        orch = AgentOrchestrator(demo=True)
        # Force revision path by pre-checking needs_revision
        assert orch._needs_revision([]) is True
        revised = orch._revise_plan("NVDA", [], [])
        assert {s.agent_role for s in revised} == {"finance", "web_search"}


class TestTracing:
    def test_tracer_records_events(self):
        t = Tracer()
        t.record("plan", "hello", step=1)
        data = t.to_list()
        assert len(data) == 1
        assert data[0]["kind"] == "plan"
        assert data[0]["data"]["step"] == 1


class TestErrorHandling:
    def test_agent_rejects_blank_via_orchestrator(self):
        orch = AgentOrchestrator(demo=True)
        result = orch.run("   ")
        assert "empty" in result.answer.lower()
