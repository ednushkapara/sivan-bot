"""
notion_leads.py — all Notion read/write for Sivan's CRM.
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Setup ───────────────────────────────────────────────────────────────────

def _clean_id(v: str) -> str:
    return re.sub(r"[^a-f0-9\-]", "", v.lower())

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
DB_LEADS = _clean_id(os.getenv("NOTION_LEADS_DB", ""))
DB_MUSIC_EVENTS = _clean_id(os.getenv("NOTION_MUSIC_EVENTS_DB", ""))

CLOSED_STATUSES = {"סגור — זכינו ✅", "סגור — הפסדנו ❌", "אירוע בוצע 🎵"}


def _get_client():
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN not set")
    from notion_client import Client
    return Client(auth=NOTION_TOKEN)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _rich_text(text: str) -> list:
    return [{"text": {"content": str(text)[:2000]}}] if text else []


def _get_plain_text(prop: dict, key: str = "rich_text") -> str:
    return "".join(item.get("plain_text", "") for item in prop.get(key, []))


def _now_israel() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=3)


def _today_iso() -> str:
    return _now_israel().strftime("%Y-%m-%d")


def _now_stamp() -> str:
    return _now_israel().strftime("%d/%m %H:%M")


def _parse_date(date_str: str) -> str | None:
    """Normalize to YYYY-MM-DD. Accepts: YYYY-MM-DD, DD.MM.YYYY, DD.MM."""
    if not date_str:
        return None
    s = date_str.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"^(\d{1,2})\.(\d{1,2})$", s)
    if m:
        year = _now_israel().year
        return f"{year}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return s


def _extract_lead(page: dict) -> dict:
    """Convert a Notion page to a clean lead dict."""
    props = page.get("properties", {})

    def sel(key):
        s = props.get(key, {}).get("select")
        return s["name"] if s else None

    def multi(key):
        return [o["name"] for o in props.get(key, {}).get("multi_select", [])]

    def date(key):
        d = props.get(key, {}).get("date")
        return d["start"] if d else None

    def num(key):
        return props.get(key, {}).get("number")

    return {
        "id": page["id"],
        "name": _get_plain_text(props.get("Name", {}), "title"),
        "status": sel("Status"),
        "event_type": sel("Event Type"),
        "performance_style": multi("Performance Style"),
        "music_style": multi("Music Style"),
        "event_date": date("Event Date"),
        "contact_date": date("Contact Date"),
        "last_communication": date("Last Communication"),
        "follow_up_date": date("Follow Up Date"),
        "close_date": date("Close Date"),
        "budget": num("Budget"),
        "proposed_price": num("Proposed Price"),
        "final_price": num("Final Price"),
        "contact_name": _get_plain_text(props.get("Contact Name", {})),
        "contact_phone": props.get("Contact Phone", {}).get("phone_number"),
        "contact_email": props.get("Contact Email", {}).get("email"),
        "location": _get_plain_text(props.get("Location", {})),
        "source": sel("Source"),
        "notes": _get_plain_text(props.get("Notes", {})),
    }


# ─── S1: create_lead ─────────────────────────────────────────────────────────

def create_lead(
    name: str,
    event_type: str,
    event_date: str = None,
    performance_style: list = [],
    music_style: list = [],
    budget: float = None,
    contact_name: str = None,
    contact_phone: str = None,
    source: str = None,
    notes: str = None,
) -> str:
    """Create a new lead. Returns page_id."""
    notion = _get_client()
    props = {
        "Name": {"title": [{"text": {"content": name}}]},
        "Status": {"select": {"name": "איסוף פרטים"}},
        "Event Type": {"select": {"name": event_type}},
        "Contact Date": {"date": {"start": _today_iso()}},
    }
    if event_date:
        parsed = _parse_date(event_date)
        if parsed:
            props["Event Date"] = {"date": {"start": parsed}}
    if performance_style:
        props["Performance Style"] = {"multi_select": [{"name": s} for s in performance_style]}
    if music_style:
        props["Music Style"] = {"multi_select": [{"name": s} for s in music_style]}
    if budget is not None:
        props["Budget"] = {"number": float(budget)}
    if contact_name:
        props["Contact Name"] = {"rich_text": _rich_text(contact_name)}
    if contact_phone:
        props["Contact Phone"] = {"phone_number": contact_phone}
    if source:
        props["Source"] = {"select": {"name": source}}
    if notes:
        props["Notes"] = {"rich_text": _rich_text(notes)}

    page = notion.pages.create(
        parent={"database_id": DB_LEADS},
        properties=props,
    )
    page_id = page["id"]
    logger.info("create_lead: created '%s' → %s", name, page_id)
    return page_id


# ─── S2: get_leads / get_lead_by_name / get_task_suggestions ─────────────────

def get_leads(
    status: str = None,
    event_type: str = None,
    from_date: str = None,
    to_date: str = None,
    limit: int = 20,
) -> list:
    """Return leads with optional filters."""
    notion = _get_client()
    filters = []
    if status:
        filters.append({"property": "Status", "select": {"equals": status}})
    if event_type:
        filters.append({"property": "Event Type", "select": {"equals": event_type}})
    if from_date:
        filters.append({"property": "Event Date", "date": {"on_or_after": _parse_date(from_date)}})
    if to_date:
        filters.append({"property": "Event Date", "date": {"on_or_before": _parse_date(to_date)}})

    kwargs = {"database_id": DB_LEADS, "page_size": min(limit, 100)}
    if len(filters) == 1:
        kwargs["filter"] = filters[0]
    elif len(filters) > 1:
        kwargs["filter"] = {"and": filters}

    res = notion.databases.query(**kwargs)
    return [_extract_lead(p) for p in res.get("results", [])[:limit]]


def get_lead_by_name(name: str) -> dict | None:
    """Find a lead by name (exact first, then fuzzy). Returns lead dict or None."""
    notion = _get_client()
    res = notion.databases.query(database_id=DB_LEADS)
    needle = name.lower().strip()
    best = None
    best_score = 0.0
    for page in res.get("results", []):
        title_list = page["properties"].get("Name", {}).get("title", [])
        page_title = title_list[0].get("plain_text", "") if title_list else ""
        hay = page_title.lower().strip()
        if needle == hay or needle in hay or hay in needle:
            return _extract_lead(page)
        score = SequenceMatcher(None, needle, hay).ratio()
        if score > best_score:
            best_score = score
            best = page
    if best and best_score >= 0.85:
        return _extract_lead(best)
    return None


def get_task_suggestions(query: str, top_n: int = 3) -> list:
    """Return up to top_n lead names ranked by similarity. Only open leads."""
    notion = _get_client()
    res = notion.databases.query(database_id=DB_LEADS)
    needle = query.lower().strip()
    scored = []
    for page in res.get("results", []):
        props = page.get("properties", {})
        status = (props.get("Status", {}).get("select") or {}).get("name", "")
        if status in CLOSED_STATUSES:
            continue
        title_list = props.get("Name", {}).get("title", [])
        page_title = title_list[0].get("plain_text", "") if title_list else ""
        if not page_title:
            continue
        hay = page_title.lower().strip()
        if needle in hay or hay in needle:
            score = 0.95
        else:
            score = SequenceMatcher(None, needle, hay).ratio()
        if score >= 0.4:
            scored.append((score, page_title))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [title for _, title in scored[:top_n]]


# ─── S3: update functions ─────────────────────────────────────────────────────

def update_lead_status(page_id: str, new_status: str) -> bool:
    """Update the Status field of a lead."""
    notion = _get_client()
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"select": {"name": new_status}}},
    )
    logger.info("update_lead_status: %s → %s", page_id[:8], new_status)
    return True


def update_lead_fields(
    page_id: str,
    proposed_price: float = None,
    final_price: float = None,
    event_date: str = None,
    follow_up_date: str = None,
    last_communication: str = None,
    location: str = None,
    contact_name: str = None,
    contact_phone: str = None,
    performance_style: list = None,
    music_style: list = None,
    budget: float = None,
    notes: str = None,
) -> bool:
    """Update one or more lead fields. Only non-None values are sent."""
    notion = _get_client()
    props = {}
    if proposed_price is not None:
        props["Proposed Price"] = {"number": float(proposed_price)}
    if final_price is not None:
        props["Final Price"] = {"number": float(final_price)}
    if budget is not None:
        props["Budget"] = {"number": float(budget)}
    if event_date is not None:
        parsed = _parse_date(event_date)
        if parsed:
            props["Event Date"] = {"date": {"start": parsed}}
    if follow_up_date is not None:
        parsed = _parse_date(follow_up_date)
        if parsed:
            props["Follow Up Date"] = {"date": {"start": parsed}}
    if last_communication is not None:
        parsed = _parse_date(last_communication)
        if parsed:
            props["Last Communication"] = {"date": {"start": parsed}}
    if location is not None:
        props["Location"] = {"rich_text": _rich_text(location)}
    if contact_name is not None:
        props["Contact Name"] = {"rich_text": _rich_text(contact_name)}
    if contact_phone is not None:
        props["Contact Phone"] = {"phone_number": contact_phone}
    if performance_style is not None:
        props["Performance Style"] = {"multi_select": [{"name": s} for s in performance_style]}
    if music_style is not None:
        props["Music Style"] = {"multi_select": [{"name": s} for s in music_style]}
    if notes is not None:
        # append note to existing notes
        page = notion.pages.retrieve(page_id=page_id)
        current = _get_plain_text(page["properties"].get("Notes", {}))
        combined = f"{current}\n[{_now_stamp()}] {notes}".strip()
        props["Notes"] = {"rich_text": _rich_text(combined)}
    if not props:
        return True
    notion.pages.update(page_id=page_id, properties=props)
    logger.info("update_lead_fields: %s fields=%s", page_id[:8], list(props.keys()))
    return True


def add_lead_note(page_id: str, note: str) -> bool:
    """Append a timestamped note to a lead's Notes field."""
    notion = _get_client()
    page = notion.pages.retrieve(page_id=page_id)
    current = _get_plain_text(page["properties"].get("Notes", {}))
    combined = f"{current}\n[{_now_stamp()}] {note}".strip()
    notion.pages.update(
        page_id=page_id,
        properties={"Notes": {"rich_text": _rich_text(combined)}},
    )
    logger.info("add_lead_note: %s", page_id[:8])
    return True


# ─── S9: pipeline + followups ─────────────────────────────────────────────────

def get_pipeline_summary() -> dict:
    """Return lead counts grouped by Status + total proposed/final values."""
    notion = _get_client()
    res = notion.databases.query(database_id=DB_LEADS)
    summary: dict = {}
    total_proposed = 0.0
    total_final = 0.0
    for page in res.get("results", []):
        props = page.get("properties", {})
        status = (props.get("Status", {}).get("select") or {}).get("name", "לא ידוע")
        summary[status] = summary.get(status, 0) + 1
        total_proposed += props.get("Proposed Price", {}).get("number") or 0
        total_final += props.get("Final Price", {}).get("number") or 0
    summary["_total_proposed"] = total_proposed
    summary["_total_final"] = total_final
    return summary


def get_lead_context_for_message(lead_name: str) -> dict:
    """Return lead context for draft_customer_message. Claude does the actual drafting."""
    lead = get_lead_by_name(lead_name)
    if not lead:
        return {"found": False, "lead_name": lead_name}
    return {
        "found": True,
        "name": lead["name"],
        "event_type": lead["event_type"],
        "event_date": lead["event_date"],
        "status": lead["status"],
        "proposed_price": lead["proposed_price"],
        "location": lead["location"],
        "last_communication": lead["last_communication"],
        "follow_up_date": lead["follow_up_date"],
        "notes": lead["notes"],
    }


def get_due_followups(days_ahead: int = 3) -> list:
    """Return open leads whose Follow Up Date is within the next N days (incl. overdue)."""
    notion = _get_client()
    cutoff = (_now_israel() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    res = notion.databases.query(
        database_id=DB_LEADS,
        filter={
            "and": [
                {"property": "Follow Up Date", "date": {"on_or_before": cutoff}},
                {"property": "Follow Up Date", "date": {"is_not_empty": True}},
                {"property": "Status", "select": {"does_not_equal": "סגור — זכינו ✅"}},
                {"property": "Status", "select": {"does_not_equal": "סגור — הפסדנו ❌"}},
                {"property": "Status", "select": {"does_not_equal": "אירוע בוצע 🎵"}},
            ]
        },
    )
    return [_extract_lead(p) for p in res.get("results", [])]
