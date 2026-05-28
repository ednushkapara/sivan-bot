"""
shimshon_bridge.py — writes follow-up tasks to Shimshon's Tasks DB.

STUB — Phase 2 implementation. All functions return mock success.
Real implementation in P2.1.
"""

import logging
import os

logger = logging.getLogger(__name__)

SHIMSHON_TASKS_DB_ID = os.getenv("SHIMSHON_TASKS_DB_ID", "")
SIVAN_PROJECT_TAG = "סיוון"


def send_task_to_shimshon(
    description: str,
    scheduled_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    """
    Write a new task to Shimshon's Notion Tasks DB with Project="סיוון".
    Shimshon picks it up and displays it in /brief like any other task.

    STUB — returns mock success until Phase 2.
    """
    logger.info(
        "[STUB] send_task_to_shimshon: description=%r scheduled=%s due=%s",
        description, scheduled_date, due_date,
    )
    return {
        "task_id": "stub-not-implemented",
        "status": "stub — Phase 2 implementation pending",
    }
