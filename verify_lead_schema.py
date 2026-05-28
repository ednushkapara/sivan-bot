"""
verify_lead_schema.py — Sivan Notion schema validator.

Run locally:   python verify_lead_schema.py
Run before every deploy and after any Notion DB changes.

Checks every property and select/multi_select option in:
  - סיוון Leads DB
  - סיוון Music Events DB

Reports:
  ✓ OK      — property/option exists with correct type
  ⚠ warn    — optional thing missing or non-fatal
  ✗ MISSING — required; bot WILL fail without it

At the end prints SUMMARY and ACTIONS list.
NEVER writes to Notion. Read-only. Safe to run any time.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ─── Style helpers ───────────────────────────────────────────────────────────

OK = "\033[32m✓\033[0m"
WARN = "\033[33m⚠\033[0m"
ERR = "\033[31m✗\033[0m"
DIM = "\033[2m"
RESET = "\033[0m"

_counts = {"ok": 0, "warn": 0, "err": 0}
_actions: list[str] = []


def _ok(msg: str, indent: int = 2):
    _counts["ok"] += 1
    print(f"{' ' * indent}{OK} {msg}")


def _warn(msg: str, action: str = "", indent: int = 2):
    _counts["warn"] += 1
    print(f"{' ' * indent}{WARN} {msg}")
    if action:
        _actions.append(f"[warn] {action}")


def _err(msg: str, action: str = "", indent: int = 2):
    _counts["err"] += 1
    print(f"{' ' * indent}{ERR} {msg}")
    if action:
        _actions.append(f"[ERR ] {action}")


def _section(title: str):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ─── Expected schemas ─────────────────────────────────────────────────────────

_EVENT_TYPE_OPTIONS = [
    "חתונה", "בר מצווה", "בת מצווה", "אירוע חברה", "מסיבה", "אחר",
]

_PERFORMANCE_STYLE_OPTIONS = [
    "קבלת פנים", "ליווי חופה", "מנות עיקריות", "אפטר ריקודים", "טברנה",
]

_MUSIC_STYLE_OPTIONS = [
    "מזרחית", "יוונית", "רגוע", "מאינסטרים ישראלי", "מאינסטרים לועזי",
]

EXPECTED: dict[str, dict] = {
    "LEADS": {
        "env": "NOTION_LEADS_DB",
        "required": True,
        "title_prop": "Name",
        "props": {
            "Status": {
                "type": "select",
                "options": [
                    "איסוף פרטים", "קביעת שיחת טלפון", "הצעת מחיר נשלחה",
                    "במשא ומתן", "סגור — זכינו ✅", "סגור — הפסדנו ❌", "אירוע בוצע 🎵",
                ],
            },
            "Event Type":          {"type": "select",       "options": _EVENT_TYPE_OPTIONS},
            "Performance Style":   {"type": "multi_select", "options": _PERFORMANCE_STYLE_OPTIONS},
            "Music Style":         {"type": "multi_select", "options": _MUSIC_STYLE_OPTIONS},
            "Event Date":          {"type": "date"},
            "Contact Date":        {"type": "date"},
            "Last Communication":  {"type": "date"},
            "Follow Up Date":      {"type": "date"},
            "Close Date":          {"type": "date"},
            "Budget":              {"type": "number"},
            "Proposed Price":      {"type": "number"},
            "Final Price":         {"type": "number"},
            "Contact Name":        {"type": "rich_text"},
            "Contact Phone":       {"type": "phone_number"},
            "Contact Email":       {"type": "email"},
            "Location":            {"type": "rich_text"},
            "Source": {
                "type": "select",
                "options": ["עמית/חבר", "אתר", "פייסבוק", "אינסטגרם", "גוגל", "אחר"],
            },
            "Notes":               {"type": "rich_text"},
        },
    },
    "MUSIC_EVENTS": {
        "env": "NOTION_MUSIC_EVENTS_DB",
        "required": True,
        "title_prop": "Name",
        "props": {
            "Date":                  {"type": "date"},
            "Event Type":            {"type": "select",       "options": _EVENT_TYPE_OPTIONS},
            "Performance Style":     {"type": "multi_select", "options": _PERFORMANCE_STYLE_OPTIONS},
            "Music Style":           {"type": "multi_select", "options": _MUSIC_STYLE_OPTIONS},
            "Location":              {"type": "rich_text"},
            "Client":                {"type": "rich_text"},
            "Revenue":               {"type": "number"},
            "Deposit Paid":          {"type": "select", "options": ["כן", "לא", "חלקי"]},
            "Contract Signed":       {"type": "select", "options": ["כן", "לא"]},
            "Final Payment Received":{"type": "select", "options": ["כן", "לא", "חלקי"]},
            "Notes":                 {"type": "rich_text"},
            "Lead":                  {"type": "relation"},
        },
    },
}


# ─── Env check ───────────────────────────────────────────────────────────────

def check_env() -> str | None:
    _section("Environment variables")
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        _err("NOTION_TOKEN not set in .env", "Add NOTION_TOKEN=... to .env")
        return None
    _ok(f"NOTION_TOKEN set ({len(token)} chars)")

    for key, spec in EXPECTED.items():
        env = spec["env"]
        val = os.getenv(env, "").strip()
        if val:
            _ok(f"{env} set ({val[:8]}...)")
        elif spec["required"]:
            _err(f"{env} not set", f"Add {env}=<db_id> to .env — run notion_setup.py first")
        else:
            _warn(f"{env} not set (optional)")

    return token


# ─── DB schema check ─────────────────────────────────────────────────────────

def _clean_id(v: str) -> str:
    import re
    return re.sub(r"[^a-f0-9\-]", "", v.lower())


def _get_option_names(prop: dict, prop_type: str) -> set[str]:
    """Extract option names from a select or multi_select property."""
    return {o["name"] for o in prop.get(prop_type, {}).get("options", [])}


def check_db(client, key: str, spec: dict):
    db_id_raw = os.getenv(spec["env"], "").strip()
    if not db_id_raw:
        return

    db_id = _clean_id(db_id_raw)
    _section(f"DB {key} ({db_id[:8]}...)  env={spec['env']}")

    try:
        db = client.databases.retrieve(database_id=db_id)
    except Exception as e:
        _err(f"Cannot retrieve DB: {e}", f"Check {spec['env']} value + integration access")
        return

    title_text = ""
    for part in db.get("title", []):
        title_text += part.get("plain_text", "")
    _ok(f'Connected to DB "{title_text}"')

    actual_props = db.get("properties", {})

    # Title property
    expected_title = spec.get("title_prop")
    if expected_title:
        tp = actual_props.get(expected_title)
        if tp and tp.get("type") == "title":
            _ok(f'Title property "{expected_title}"')
        else:
            _err(
                f'Title property "{expected_title}" missing or wrong type',
                f'In DB "{title_text}" → rename title column to "{expected_title}"',
            )

    # Regular properties
    for prop_name, expected in spec.get("props", {}).items():
        p = actual_props.get(prop_name)
        if not p:
            _err(
                f'Property "{prop_name}" missing',
                f'In DB "{title_text}" → add {expected["type"]} property "{prop_name}"',
            )
            continue

        actual_type = p.get("type")
        if actual_type != expected["type"]:
            _err(
                f'Property "{prop_name}" wrong type: {actual_type} (expected {expected["type"]})',
                f'In DB "{title_text}" → change "{prop_name}" type to {expected["type"]}',
            )
            continue

        _ok(f'Property "{prop_name}" ({actual_type})')

        # Option checks for select / multi_select
        if expected["type"] in ("select", "multi_select") and "options" in expected:
            actual_opts = _get_option_names(p, actual_type)
            for opt in expected["options"]:
                if opt in actual_opts:
                    _ok(f'option "{opt}"', indent=4)
                else:
                    _err(
                        f'option "{opt}" missing',
                        f'In DB "{title_text}" → add {actual_type} option "{opt}" to "{prop_name}"',
                        indent=4,
                    )


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    print("verify_lead_schema.py — Sivan Notion schema validator")
    print(f"{DIM}Read-only. Never writes to Notion.{RESET}")

    token = check_env()
    if not token:
        print()
        print("Cannot proceed without NOTION_TOKEN. Exiting.")
        return 1

    try:
        from notion_client import Client
    except ImportError:
        print()
        print(f"{ERR} notion-client not installed. Run: pip install notion-client")
        return 1

    client = Client(auth=token)

    for key, spec in EXPECTED.items():
        check_db(client, key, spec)

    _section("SUMMARY")
    print(f"  {OK} {_counts['ok']:>3} OK")
    print(f"  {WARN} {_counts['warn']:>3} warnings")
    print(f"  {ERR} {_counts['err']:>3} errors")

    if _actions:
        print()
        print("ACTIONS NEEDED (in order):")
        for i, a in enumerate(_actions, 1):
            print(f"  {i}. {a}")

    print()
    if _counts["err"] == 0:
        print(f"{OK} Schema is healthy. Safe to run Sivan.")
        return 0
    else:
        print(f"{ERR} Schema has {_counts['err']} errors. Fix them above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
