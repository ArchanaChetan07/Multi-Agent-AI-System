"""Finance tool with deterministic DEMO_MODE results."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")


@dataclass(frozen=True)
class FinanceSnapshot:
    symbol: str
    price: float
    currency: str
    recommendation: str
    news_headlines: tuple[str, ...]
    source: str


def extract_ticker(text: str, default: str = "NVDA") -> str:
    # Prefer common equity tickers mentioned explicitly
    known = ("NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META")
    upper = text.upper()
    for t in known:
        if t in upper:
            return t
    matches = TICKER_RE.findall(text.upper())
    skip = {"THE", "AND", "FOR", "LATEST", "NEWS", "SHARE", "USE", "AI", "USD"}
    for m in matches:
        if m not in skip:
            return m
    return default


def _demo_snapshot(symbol: str) -> FinanceSnapshot:
    digest = int(hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:6], 16)
    price = 50.0 + (digest % 90000) / 100.0
    recs = ("buy", "hold", "sell", "overweight")
    return FinanceSnapshot(
        symbol=symbol.upper(),
        price=round(price, 2),
        currency="USD",
        recommendation=recs[digest % len(recs)],
        news_headlines=(
            f"[DEMO] {symbol.upper()} announces product update",
            f"[DEMO] Analysts revisit targets for {symbol.upper()}",
        ),
        source="demo",
    )


def finance_lookup(query: str, *, demo: bool = True) -> FinanceSnapshot:
    symbol = extract_ticker(query)
    if demo:
        return _demo_snapshot(symbol)
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = getattr(ticker, "fast_info", None)
        price = None
        if info is not None:
            price = getattr(info, "last_price", None) or info.get("last_price")  # type: ignore[union-attr]
        if price is None:
            hist = ticker.history(period="1d")
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if price is None:
            return _demo_snapshot(symbol)
        return FinanceSnapshot(
            symbol=symbol.upper(),
            price=round(float(price), 2),
            currency="USD",
            recommendation="unavailable",
            news_headlines=(f"Live quote fetched for {symbol.upper()}",),
            source="yfinance",
        )
    except Exception:
        return _demo_snapshot(symbol)
