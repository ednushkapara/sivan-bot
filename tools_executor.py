"""
tools_executor.py — dispatch table for Sivan's CRM tools.
Phase 1: 8 core lead management tools.
"""

import logging

logger = logging.getLogger(__name__)


def _not_found_response(name: str, suggestions: list) -> dict:
    if suggestions:
        opts = " | ".join(suggestions)
        return {
            "found": False,
            "suggestions": suggestions,
            "message": f"לא מצאתי ליד בשם '{name}'. אולי התכוונת ל: {opts}?",
        }
    return {
        "found": False,
        "suggestions": [],
        "message": f"לא מצאתי ליד בשם '{name}'. בדקי את השם ונסי שוב.",
    }


def execute_tool(name: str, params: dict) -> dict:
    """Dispatch a tool call by name. Returns result dict for Claude."""
    from notion_leads import (
        create_lead,
        get_leads,
        get_lead_by_name,
        get_task_suggestions,
        update_lead_status,
        update_lead_fields,
        add_lead_note,
        get_pipeline_summary,
        get_due_followups,
    )

    try:
        match name:

            case "add_lead":
                page_id = create_lead(
                    name=params["name"],
                    event_type=params["event_type"],
                    event_date=params.get("event_date"),
                    performance_style=params.get("performance_style", []),
                    music_style=params.get("music_style", []),
                    budget=params.get("budget"),
                    contact_name=params.get("contact_name"),
                    contact_phone=params.get("contact_phone"),
                    source=params.get("source"),
                    notes=params.get("notes"),
                )
                return {
                    "success": True,
                    "lead_id": page_id,
                    "message": f"ליד נוצר: {params['name']}",
                }

            case "get_leads":
                leads = get_leads(
                    status=params.get("status"),
                    event_type=params.get("event_type"),
                    from_date=params.get("from_date"),
                    to_date=params.get("to_date"),
                    limit=params.get("limit", 20),
                )
                return {"leads": leads, "count": len(leads)}

            case "get_lead":
                lead_name = params["name"]
                lead = get_lead_by_name(lead_name)
                if lead:
                    return {"found": True, "lead": lead}
                suggestions = get_task_suggestions(lead_name)
                return _not_found_response(lead_name, suggestions)

            case "update_lead_status":
                lead_name = params["name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                update_lead_status(lead["id"], params["new_status"])
                return {
                    "success": True,
                    "message": f"עודכן: {lead['name']} → {params['new_status']}",
                }

            case "update_lead_fields":
                lead_name = params["name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                update_lead_fields(
                    page_id=lead["id"],
                    proposed_price=params.get("proposed_price"),
                    final_price=params.get("final_price"),
                    budget=params.get("budget"),
                    event_date=params.get("event_date"),
                    follow_up_date=params.get("follow_up_date"),
                    last_communication=params.get("last_communication"),
                    location=params.get("location"),
                    contact_name=params.get("contact_name"),
                    contact_phone=params.get("contact_phone"),
                    performance_style=params.get("performance_style"),
                    music_style=params.get("music_style"),
                    notes=params.get("notes"),
                )
                return {
                    "success": True,
                    "message": f"עודכן: {lead['name']}",
                }

            case "add_lead_note":
                lead_name = params["name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                add_lead_note(lead["id"], params["note"])
                return {
                    "success": True,
                    "message": f"הערה נוספה ל-{lead['name']}",
                }

            case "get_pipeline_summary":
                summary = get_pipeline_summary()
                return {"summary": summary}

            case "get_due_followups":
                leads = get_due_followups(days_ahead=params.get("days_ahead", 3))
                return {"leads": leads, "count": len(leads)}

            case _:
                logger.warning("execute_tool: unknown tool '%s'", name)
                return {"error": f"כלי לא מוכר: '{name}'"}

    except Exception as e:
        logger.error("execute_tool '%s' failed: %s", name, e)
        return {"error": str(e)}
