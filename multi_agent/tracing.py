"""Structured tracing for plan / tool / revise steps."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceEvent:
    kind: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Tracer:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def record(self, kind: str, message: str, **data: Any) -> TraceEvent:
        event = TraceEvent(kind=kind, message=message, data=data)
        self.events.append(event)
        return event

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.events]
