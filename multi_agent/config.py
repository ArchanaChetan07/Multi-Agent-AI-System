"""Runtime configuration. Never logs secret values."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def has_groq_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def is_demo_mode() -> bool:
    """Demo mode when forced or when Groq key is missing."""
    if _truthy("DEMO_MODE"):
        return True
    if _truthy("FORCE_LIVE"):
        return False
    return not has_groq_key()


def groq_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
