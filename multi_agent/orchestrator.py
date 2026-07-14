"""Orchestrator: decompose task → route agents → observe → optionally revise."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from multi_agent.agents import FinanceAgent, WebSearchAgent
from multi_agent.config import is_demo_mode
from multi_agent.tracing import Tracer


@dataclass
class PlannedStep:
    agent_role: str
    objective: str


@dataclass
class RunResult:
    task: str
    demo_mode: bool
    plan: list[dict[str, str]]
    observations: list[dict[str, Any]]
    revisions: list[str]
    answer: str
    trace: list[dict[str, Any]] = field(default_factory=list)


class AgentOrchestrator:
    """In-repo multi-agent collaborator (no phi required for tests)."""

    def __init__(self, *, demo: bool | None = None) -> None:
        self.demo = is_demo_mode() if demo is None else demo
        self.web = WebSearchAgent()
        self.finance = FinanceAgent()
        self._agents = {
            self.web.role: self.web,
            self.finance.role: self.finance,
        }

    def plan(self, task: str) -> list[PlannedStep]:
        lower = task.lower()
        steps: list[PlannedStep] = []
        wants_finance = any(
            k in lower
            for k in (
                "stock",
                "analyst",
                "recommendation",
                "price",
                "finance",
                "fundament",
                "ticker",
                "nvda",
                "aapl",
                "msft",
            )
        )
        wants_news = any(k in lower for k in ("news", "latest", "search", "web", "summarize"))

        if wants_finance:
            steps.append(
                PlannedStep(
                    agent_role="finance",
                    objective=f"Lookup finance metrics for: {task}",
                )
            )
        if wants_news or not steps:
            steps.append(
                PlannedStep(
                    agent_role="web_search",
                    objective=f"Search for context: {task}",
                )
            )
        # Prefer finance then search for market questions that ask for both
        if wants_finance and wants_news:
            roles = [s.agent_role for s in steps]
            if roles != ["finance", "web_search"]:
                steps = [
                    PlannedStep(agent_role="finance", objective=f"Lookup finance metrics for: {task}"),
                    PlannedStep(agent_role="web_search", objective=f"Search for context: {task}"),
                ]
        return steps

    def _needs_revision(self, observations: list[dict[str, Any]]) -> bool:
        if not observations:
            return True
        for obs in observations:
            if obs.get("role") == "finance" and not obs.get("symbol"):
                return True
            if obs.get("role") == "web_search" and not obs.get("hits"):
                return True
        return False

    def _revise_plan(
        self, task: str, plan: list[PlannedStep], observations: list[dict[str, Any]]
    ) -> list[PlannedStep]:
        roles_run = {o.get("role") for o in observations}
        revised: list[PlannedStep] = []
        if "finance" not in roles_run:
            revised.append(
                PlannedStep(agent_role="finance", objective=f"Fallback finance lookup: {task}")
            )
        if "web_search" not in roles_run:
            revised.append(
                PlannedStep(agent_role="web_search", objective=f"Fallback web search: {task}")
            )
        if not revised:
            # Re-run web search with a narrower objective
            revised.append(
                PlannedStep(
                    agent_role="web_search",
                    objective=f"Revise search with narrower query: {task}",
                )
            )
        return revised

    def _synthesize(self, task: str, observations: list[dict[str, Any]]) -> str:
        parts = [f"Task: {task}", f"Mode: {'DEMO' if self.demo else 'LIVE'}"]
        for obs in observations:
            parts.append(f"\n[{obs.get('agent')}] {obs.get('summary', '')}")
            if obs.get("role") == "finance":
                parts.append(
                    f"Symbol={obs.get('symbol')} Price={obs.get('price')} "
                    f"{obs.get('currency')} Rec={obs.get('recommendation')}"
                )
                headlines = obs.get("news_headlines") or []
                if headlines:
                    parts.append("Headlines:")
                    parts.extend(f"  - {h}" for h in headlines)
            if obs.get("role") == "web_search":
                sources = obs.get("hits") or []
                if sources:
                    parts.append("Sources:")
                    for h in sources:
                        parts.append(f"  - {h.get('title')} ({h.get('url')})")
        return "\n".join(parts)

    def run(self, task: str) -> RunResult:
        tracer = Tracer()
        task = (task or "").strip()
        tracer.record("start", "Received task", task=task, demo=self.demo)

        if not task:
            tracer.record("error", "Empty task")
            return RunResult(
                task=task,
                demo_mode=self.demo,
                plan=[],
                observations=[],
                revisions=[],
                answer="Task cannot be empty",
                trace=tracer.to_list(),
            )

        plan = self.plan(task)
        tracer.record(
            "plan",
            "Decomposed task",
            steps=[{"agent_role": s.agent_role, "objective": s.objective} for s in plan],
        )

        observations: list[dict[str, Any]] = []
        revisions: list[str] = []

        def execute(steps: list[PlannedStep]) -> None:
            for step in steps:
                agent = self._agents.get(step.agent_role)
                if agent is None:
                    tracer.record("route_error", "Unknown agent role", role=step.agent_role)
                    continue
                tracer.record(
                    "route",
                    f"Routing to {agent.name}",
                    role=step.agent_role,
                    objective=step.objective,
                )
                result = agent.run(step.objective, demo=self.demo)
                observations.append(result)
                tracer.record(
                    "observe",
                    f"Observed {agent.name}",
                    role=step.agent_role,
                    summary=result.get("summary", "")[:200],
                )

        execute(plan)

        if self._needs_revision(observations):
            revised = self._revise_plan(task, plan, observations)
            note = f"Revising plan → {[s.agent_role for s in revised]}"
            revisions.append(note)
            tracer.record("revise", note)
            execute(revised)

        answer = self._synthesize(task, observations)
        tracer.record("finish", "Synthesized answer", observation_count=len(observations))

        return RunResult(
            task=task,
            demo_mode=self.demo,
            plan=[{"agent_role": s.agent_role, "objective": s.objective} for s in plan],
            observations=observations,
            revisions=revisions,
            answer=answer,
            trace=tracer.to_list(),
        )


def optional_groq_complete(prompt: str) -> str | None:
    """Thin optional path for real Groq when a key is present."""
    from multi_agent.config import has_groq_key, groq_model

    if not has_groq_key():
        return None
    try:
        from groq import Groq

        client = Groq()
        resp = client.chat.completions.create(
            model=groq_model(),
            messages=[
                {
                    "role": "system",
                    "content": "You summarize multi-agent finance/web findings concisely.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None
