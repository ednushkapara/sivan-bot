"""
tools_executor.py — dispatch table for Sivan's 14 tools.

STUB — empty for Phase 0. Phase 1 (P1.3) fills in the dispatch logic.
"""

import logging

logger = logging.getLogger(__name__)


def execute_tool(name: str, params: dict) -> dict:
    """Dispatch a tool call by name. Returns result dict for Claude."""
    logger.warning("execute_tool called with unknown/stub tool: %s", name)
    return {"error": f"Tool '{name}' not yet implemented (Phase 1)"}
