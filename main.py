#!/usr/bin/env python3
"""CLI entrypoint for the multi-agent orchestrator."""

from __future__ import annotations

import argparse
import json
import sys

from multi_agent.orchestrator import AgentOrchestrator, optional_groq_complete


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multi-agent web search + finance runner")
    parser.add_argument(
        "task",
        nargs="?",
        default="Summarize analyst recommendation and share the latest news for NVDA",
        help="Natural-language task for the orchestrator",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Prefer live tools (still falls back to demo on failure)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured RunResult as JSON",
    )
    parser.add_argument(
        "--groq-polish",
        action="store_true",
        help="If GROQ_API_KEY is set, optionally polish the answer with Groq",
    )
    args = parser.parse_args(argv)

    orch = AgentOrchestrator(demo=False if args.live else None)
    result = orch.run(args.task)

    if args.groq_polish and not result.demo_mode:
        polished = optional_groq_complete(result.answer)
        if polished:
            result.answer = polished

    if args.json:
        print(
            json.dumps(
                {
                    "task": result.task,
                    "demo_mode": result.demo_mode,
                    "plan": result.plan,
                    "observations": result.observations,
                    "revisions": result.revisions,
                    "answer": result.answer,
                    "trace": result.trace,
                },
                indent=2,
            )
        )
    else:
        print(result.answer)
        print("\n--- trace ---")
        for event in result.trace:
            print(f"[{event['kind']}] {event['message']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
