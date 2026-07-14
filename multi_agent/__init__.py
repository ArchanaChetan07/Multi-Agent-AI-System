"""Lightweight multi-agent system: plan → route → observe → revise."""

from .orchestrator import AgentOrchestrator, RunResult
from .config import is_demo_mode

__all__ = ["AgentOrchestrator", "RunResult", "is_demo_mode"]
