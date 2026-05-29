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


def find_shimshon_task(lead_name: str) -> str | None:
    """Find a Shimshon task with Project='סיוון' whose title contains lead_name. Returns page_id or None."""
    from difflib import SequenceMatcher
    if not SHIMSHON_TASKS_DB_ID:
        return None
    notion = _get_client()
    try:
        res = notion.databases.query(
            database_id=SHIMSHON_TASKS_DB_ID,
            filter={
                "and": [
                    {"property": "Project", "select": {"equals": SIVAN_PROJECT_TAG}},
                    {"property": "Status", "select": {"does_not_equal": "סגור"}},
                ]
            },
        )
        needle = lead_name.lower().strip()
        best_id = None
        best_score = 0.0
        for page in res.get("results", []):
            title_list = page["properties"].get("Name", {}).get("title", [])
            title = title_list[0].get("plain_text", "") if title_list else ""
            hay = title.lower()
            if needle in hay or hay in needle:
                return page["id"]
            score = SequenceMatcher(None, needle, hay).ratio()
            if score > best_score:
                best_score = score
                best_id = page["id"]
        return best_id if best_score >= 0.5 else None
    except Exception as e:
        logger.error("find_shimshon_task failed: %s", e)
        return None


def cancel_shimshon_task(page_id: str) -> bool:
    """Mark a Shimshon task as Done."""
    notion = _get_client()
    try:
        notion.pages.update(
            page_id=page_id,
            properties={"Status": {"select": {"name": "סגור"}}},
        )
        logger.info("cancel_shimshon_task: %s marked Done", page_id[:8])
        return True
    except Exception as e:
        logger.error("cancel_shimshon_task failed: %s", e)
        return False


def update_shimshon_task_date(page_id: str, new_date: str) -> bool:
    """Update Scheduled Date of a Shimshon task."""
    notion = _get_client()
    try:
        notion.pages.update(
            page_id=page_id,
            properties={"Scheduled Date": {"date": {"start": new_date}}},
        )
        logger.info("update_shimshon_task_date: %s → %s", page_id[:8], new_date)
        return True
    except Exception as e:
        logger.error("update_shimshon_task_date failed: %s", e)
        return False
