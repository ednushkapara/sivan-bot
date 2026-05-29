"""
notion_setup.py — one-time script that builds the full Sivan Notion structure.

Run ONCE after Eden completes the manual Notion access steps (P0.2a).
Never run again unless you need to rebuild from scratch.

What it creates:
  1. "סיוון Leads" database under NOTION_PARENT_PAGE_ID
  2. "סיוון Music Events" database under NOTION_PARENT_PAGE_ID
  3. Adds "סיוון" as option to Project select in Shimshon Tasks DB

Requires in .env:
  NOTION_TOKEN
  NOTION_PARENT_PAGE_ID   (set manually after Eden's access step)
  SHIMSHON_TASKS_DB_ID    (copy from Shimshon's .env)
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _clean_id(raw: str) -> str:
    import re
    return re.sub(r"[^a-f0-9\-]", "", raw.lower().strip())


def _find_existing_db(client, parent_page_id: str, title: str) -> str | None:
    """Return the DB ID if a child database with this title already exists, else None."""
    try:
        cursor = None
        while True:
            kwargs = {"block_id": parent_page_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = client.blocks.children.list(**kwargs)
            for block in resp.get("results", []):
                if block.get("type") == "child_database":
                    db_title = block.get("child_database", {}).get("title", "")
                    if db_title == title:
                        return block["id"]
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
    except Exception as e:
        print(f"  ⚠️  Could not check for existing DB '{title}': {e}")
    return None


# ─── DB definitions ───────────────────────────────────────────────────────────

EVENT_TYPE_OPTIONS = [
    {"name": "חתונה"},
    {"name": "בר מצווה"},
    {"name": "בת מצווה"},
    {"name": "אירוע חברה"},
    {"name": "מסיבה"},
    {"name": "אחר"},
]

PERFORMANCE_STYLE_OPTIONS = [
    {"name": "קבלת פנים"},
    {"name": "ליווי חופה"},
    {"name": "מנות עיקריות"},
    {"name": "אפטר ריקודים"},
    {"name": "טברנה"},
]

MUSIC_STYLE_OPTIONS = [
    {"name": "מזרחית"},
    {"name": "יוונית"},
    {"name": "רגוע"},
    {"name": "מאינסטרים ישראלי"},
    {"name": "מאינסטרים לועזי"},
]

LEADS_DB_PROPERTIES = {
    "Name": {"title": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "איסוף פרטים"},
                {"name": "קביעת שיחת טלפון"},
                {"name": "הצעת מחיר נשלחה"},
                {"name": "במשא ומתן"},
                {"name": "סגור — זכינו ✅"},
                {"name": "סגור — הפסדנו ❌"},
                {"name": "אירוע בוצע 🎵"},
            ]
        }
    },
    "Event Type": {"select": {"options": EVENT_TYPE_OPTIONS}},
    "Performance Style": {"multi_select": {"options": PERFORMANCE_STYLE_OPTIONS}},
    "Music Style": {"multi_select": {"options": MUSIC_STYLE_OPTIONS}},
    "Event Date": {"date": {}},
    "Contact Date": {"date": {}},
    "Last Communication": {"date": {}},
    "Follow Up Date": {"date": {}},
    "Close Date": {"date": {}},
    "Budget": {"number": {"format": "number"}},
    "Proposed Price": {"number": {"format": "number"}},
    "Final Price": {"number": {"format": "number"}},
    "Contact Name": {"rich_text": {}},
    "Contact Phone": {"phone_number": {}},
    "Contact Email": {"email": {}},
    "Location": {"rich_text": {}},
    "Source": {
        "select": {
            "options": [
                {"name": "עמית/חבר"},
                {"name": "אתר"},
                {"name": "פייסבוק"},
                {"name": "אינסטגרם"},
                {"name": "גוגל"},
                {"name": "אחר"},
            ]
        }
    },
    "Notes": {"rich_text": {}},
}

MUSIC_EVENTS_DB_PROPERTIES = {
    "Name": {"title": {}},
    "Date": {"date": {}},
    "Event Type": {"select": {"options": EVENT_TYPE_OPTIONS}},
    "Performance Style": {"multi_select": {"options": PERFORMANCE_STYLE_OPTIONS}},
    "Music Style": {"multi_select": {"options": MUSIC_STYLE_OPTIONS}},
    "Location": {"rich_text": {}},
    "Client": {"rich_text": {}},
    "Revenue": {"number": {"format": "number"}},
    "Deposit Paid": {
        "select": {
            "options": [
                {"name": "כן"},
                {"name": "לא"},
                {"name": "חלקי"},
            ]
        }
    },
    "Contract Signed": {
        "select": {
            "options": [
                {"name": "כן"},
                {"name": "לא"},
            ]
        }
    },
    "Final Payment Received": {
        "select": {
            "options": [
                {"name": "כן"},
                {"name": "לא"},
                {"name": "חלקי"},
            ]
        }
    },
    "Notes": {"rich_text": {}},
}

LEAD_STATUS_OPTIONS = [
    {"name": "איסוף פרטים"},
    {"name": "קביעת שיחת טלפון"},
    {"name": "הצעת מחיר נשלחה"},
    {"name": "במשא ומתן"},
    {"name": "סגור — זכינו ✅"},
    {"name": "סגור — הפסדנו ❌"},
    {"name": "אירוע בוצע 🎵"},
]

CONVERSATION_LOG_DB_PROPERTIES = {
    "Name": {"title": {}},
    "Date": {"date": {}},
    "Direction": {
        "select": {
            "options": [
                {"name": "נכנס"},
                {"name": "יוצא"},
                {"name": "שיחת טלפון"},
            ]
        }
    },
    "Platform": {
        "select": {
            "options": [
                {"name": "WhatsApp"},
                {"name": "אינסטגרם"},
                {"name": "טלפון"},
                {"name": "אחר"},
            ]
        }
    },
    "Content": {"rich_text": {}},
    "Message Sent": {"rich_text": {}},
    "Stage": {"select": {"options": LEAD_STATUS_OPTIONS}},
}


# ─── Build functions ──────────────────────────────────────────────────────────

def create_leads_db(client, parent_page_id: str) -> str | None:
    title = "סיוון Leads"
    existing = _find_existing_db(client, parent_page_id, title)
    if existing:
        print(f"⚠️  DB already exists: {title} — skipping")
        print(f"   ID: {existing}")
        print(f"   → Add to .env as NOTION_LEADS_DB")
        return existing

    try:
        db = client.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=LEADS_DB_PROPERTIES,
        )
        db_id = db["id"]
        print(f"✅ Created: {title}")
        print(f"   ID: {db_id}")
        print(f"   → Add to .env as NOTION_LEADS_DB")
        return db_id
    except Exception as e:
        print(f"❌ Failed to create {title}: {e}")
        return None


def create_music_events_db(client, parent_page_id: str, leads_db_id: str | None) -> str | None:
    title = "סיוון Music Events"
    existing = _find_existing_db(client, parent_page_id, title)
    if existing:
        print(f"⚠️  DB already exists: {title} — skipping")
        print(f"   ID: {existing}")
        print(f"   → Add to .env as NOTION_MUSIC_EVENTS_DB")
        return existing

    props = dict(MUSIC_EVENTS_DB_PROPERTIES)

    # Add Lead relation only if Leads DB was created/found
    if leads_db_id:
        props["Lead"] = {
            "relation": {
                "database_id": leads_db_id,
                "single_property": {},
            }
        }
    else:
        print("  ⚠️  Leads DB ID not available — skipping Lead relation property")

    try:
        db = client.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=props,
        )
        db_id = db["id"]
        print(f"✅ Created: {title}")
        print(f"   ID: {db_id}")
        print(f"   → Add to .env as NOTION_MUSIC_EVENTS_DB")
        return db_id
    except Exception as e:
        print(f"❌ Failed to create {title}: {e}")
        return None


def add_sivan_to_shimshon_tasks(client, shimshon_tasks_db_id: str) -> bool:
    if not shimshon_tasks_db_id:
        print("⚠️  SHIMSHON_TASKS_DB_ID not set — skipping Shimshon integration step")
        return False

    try:
        db = client.databases.retrieve(database_id=shimshon_tasks_db_id)
    except Exception as e:
        print(f"❌ Cannot retrieve Shimshon Tasks DB: {e}")
        return False

    project_prop = db.get("properties", {}).get("Project")
    if not project_prop or project_prop.get("type") != "select":
        print("❌ Shimshon Tasks DB has no 'Project' select property — cannot add 'סיוון'")
        return False

    current_options = project_prop.get("select", {}).get("options", [])
    existing_names = {o["name"] for o in current_options}

    if "סיוון" in existing_names:
        print("⚠️  'סיוון' already exists in Shimshon Tasks DB Project options — skipping")
        return True

    new_options = current_options + [{"name": "סיוון"}]
    try:
        client.databases.update(
            database_id=shimshon_tasks_db_id,
            properties={
                "Project": {
                    "select": {"options": new_options}
                }
            },
        )
        print("✅ Added 'סיוון' to Shimshon Tasks DB Project options")
        return True
    except Exception as e:
        print(f"❌ Failed to update Shimshon Tasks DB: {e}")
        return False


def create_conversation_log_db(client, parent_page_id: str, leads_db_id: str | None) -> str | None:
    title = "סיוון Conversation Log"
    existing = _find_existing_db(client, parent_page_id, title)
    if existing:
        print(f"⚠️  DB already exists: {title} — skipping")
        print(f"   ID: {existing}")
        print(f"   → Add to .env as NOTION_CONVERSATION_LOG_DB")
        return existing

    props = dict(CONVERSATION_LOG_DB_PROPERTIES)
    if leads_db_id:
        props["Lead"] = {
            "relation": {
                "database_id": leads_db_id,
                "single_property": {},
            }
        }
    else:
        print("  ⚠️  Leads DB ID not available — skipping Lead relation property")

    try:
        db = client.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=props,
        )
        db_id = db["id"]
        print(f"✅ Created: {title}")
        print(f"   ID: {db_id}")
        print(f"   → Add to .env as NOTION_CONVERSATION_LOG_DB")
        return db_id
    except Exception as e:
        print(f"❌ Failed to create {title}: {e}")
        return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("notion_setup.py — סיוון Notion DB builder")
    print("Run once. Never again (unless rebuilding from scratch).")
    print()

    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        print("❌ NOTION_TOKEN not set in .env — cannot proceed")
        return 1

    parent_page_id_raw = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()
    if not parent_page_id_raw:
        print("❌ NOTION_PARENT_PAGE_ID not set in .env")
        print()
        print("Steps to fix:")
        print("  1. In Notion → Settings → Connections → find the integration")
        print("     (same integration used by Shimshon)")
        print("  2. Open the parent page where 'סיוון' will live")
        print("  3. Click ••• on that page → Add connections → select the integration")
        print("  4. Copy that page's ID → paste as NOTION_PARENT_PAGE_ID in .env")
        return 1

    shimshon_tasks_db_id_raw = os.getenv("SHIMSHON_TASKS_DB_ID", "").strip()
    shimshon_tasks_db_id = _clean_id(shimshon_tasks_db_id_raw) if shimshon_tasks_db_id_raw else ""
    parent_page_id = _clean_id(parent_page_id_raw)

    try:
        from notion_client import Client
    except ImportError:
        print("❌ notion-client not installed. Run: pip install notion-client")
        return 1

    client = Client(auth=token)

    print("=" * 50)
    print("Step 1: Create סיוון Leads DB")
    print("=" * 50)
    leads_db_id = create_leads_db(client, parent_page_id)

    print()
    print("=" * 50)
    print("Step 2: Create סיוון Music Events DB")
    print("=" * 50)
    music_events_db_id = create_music_events_db(client, parent_page_id, leads_db_id)

    print()
    print("=" * 50)
    print("Step 3: Create סיוון Conversation Log DB")
    print("=" * 50)
    conv_log_db_id = create_conversation_log_db(client, parent_page_id, leads_db_id)

    print()
    print("=" * 50)
    print("Step 4: Add 'סיוון' to Shimshon Tasks DB")
    print("=" * 50)
    add_sivan_to_shimshon_tasks(client, shimshon_tasks_db_id)

    print()
    print("=" * 50)
    print("DONE. Next steps:")
    print("=" * 50)
    if leads_db_id:
        print(f"  Add to .env:  NOTION_LEADS_DB={leads_db_id}")
    if music_events_db_id:
        print(f"  Add to .env:  NOTION_MUSIC_EVENTS_DB={music_events_db_id}")
    if conv_log_db_id:
        print(f"  Add to .env:  NOTION_CONVERSATION_LOG_DB={conv_log_db_id}")
    print()
    print("  Then run:     python verify_lead_schema.py")
    print("  Should show:  X OK, 0 errors")

    errors = sum(1 for v in [leads_db_id, music_events_db_id, conv_log_db_id] if v is None)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
