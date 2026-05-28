"""
Per-interaction logging — one JSON line per user message.

Writes to logs/YYYY-MM-DD.jsonl (one file per day).
Also emits a one-line human-readable summary via stdlib logger,
which Railway captures into its Logs UI (the disk file is ephemeral there).

The single most important debugging tool: captures the full pipeline
from user input -> tool calls -> tool results -> final response.

Usage:
    from interaction_log import log_interaction
    log_interaction(
        user_id=12345,
        user_input="..",
        history_size=20,
        tool_calls=[{"name": "add_lead", "input": {...}}],
        tool_results=[{"name": "add_lead", "result": {...}}],
        final_response="..",
        duration_ms=1842,
        iterations=2,
        error=None,
    )

Reading logs later:
    Locally:  tail -f logs/2026-05-22.jsonl
              grep '"error"' logs/2026-05-22.jsonl
    Railway:  Use the Logs tab. Search for "INTERACTION".
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_DIR = Path(__file__).parent / "logs"
_logger = logging.getLogger(__name__)


def _truncate(s: str, max_len: int) -> str:
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"...[+{len(s)-max_len} chars]"


def log_interaction(
    *,
    user_id: int = 0,
    user_input: str = "",
    history_size: int = 0,
    tool_calls: list | None = None,
    tool_results: list | None = None,
    final_response: str = "",
    duration_ms: int = 0,
    iterations: int = 0,
    error: str | None = None,
) -> None:
    """Append one JSON line per interaction; emit summary line to stdout.
    NEVER raises — logging failures must not break the bot.
    """
    try:
        _LOG_DIR.mkdir(exist_ok=True)
        now = datetime.now(timezone.utc)
        log_path = _LOG_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"

        record: dict[str, Any] = {
            "ts": now.isoformat(),
            "user_id": user_id,
            "user_input": _truncate(user_input, 500),
            "history_size": history_size,
            "iterations": iterations,
            "duration_ms": duration_ms,
            "tool_calls": tool_calls or [],
            "tool_results": tool_results or [],
            "final_response": _truncate(final_response, 1000),
        }
        if error:
            record["error"] = _truncate(str(error), 500)

        # 1. Full JSON to disk
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 2. Human-readable summary to stdout (Railway captures this)
        names = ",".join(tc.get("name", "?") for tc in (tool_calls or [])) or "-"
        err = f" ERROR={error[:80]}" if error else ""
        _logger.info(
            "INTERACTION user=%s iter=%d dur=%dms tools=%s in=%r out=%r%s",
            user_id, iterations, duration_ms, names,
            _truncate(user_input, 80), _truncate(final_response, 100), err,
        )
    except Exception as e:
        _logger.warning("interaction_log write failed: %s", e)
