"""
shimshon_bridge.py — writes follow-up tasks to Shimshon's Tasks DB.
Phase 2: real implementation.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SHIMSHON_TASKS_DB_ID = os.getenv("SHIMSHON_TASKS_DB_ID", "")
SIVAN_PROJECT_TAG = "סיוון"


def _get_client():
    from notion_client import Client
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        raise RuntimeError("NOTION_TOKEN not set")
    return Client(auth=token)


def send_task_to_shimshon(
    description: str,
    scheduled_date: str = None,
    due_date: str = None,
    notes: str = None,
) -> str:
    """
    Write a new task to Shimshon's Tasks DB with Project="סיוון".
    Returns the page_id of the created task.
    """
    if not SHIMSHON_TASKS_DB_ID:
        raise RuntimeError("SHIMSHON_TASKS_DB_ID not set in .env")

    notion = _get_client()
    properties = {
        "Name": {"title": [{"text": {"content": description}}]},
        "Project": {"select": {"name": SIVAN_PROJECT_TAG}},
        "Status": {"select": {"name": "פתוח"}},
    }
    if scheduled_date:
        properties["Scheduled Date"] = {"date": {"start": scheduled_date}}
    if due_date:
        properties["Due Date"] = {"date": {"start": due_date}}
    if notes:
        properties["Notes"] = {"rich_text": [{"text": {"content": notes[:2000]}}]}

    response = notion.pages.create(
        parent={"database_id": SHIMSHON_TASKS_DB_ID},
        properties=properties,
    )
    task_id = response["id"]
    logger.info("send_task_to_shimshon: created task '%s' → %s", description[:60], task_id)
    return task_id
