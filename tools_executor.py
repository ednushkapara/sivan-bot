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
                    location=params.get("location"),
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

            case "log_conversation_entry":
                from notion_leads import log_conversation_entry
                lead_name = params["lead_name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                entry_id = log_conversation_entry(
                    lead_id=lead["id"],
                    direction=params["direction"],
                    platform=params["platform"],
                    content=params["content"],
                    message_sent=params.get("message_sent"),
                    current_stage=lead.get("status"),
                )
                return {
                    "success": True,
                    "entry_id": entry_id,
                    "message": f"שיחה נרשמה עבור {lead['name']}",
                }

            case "update_followup":
                from shimshon_bridge import find_shimshon_task, cancel_shimshon_task, update_shimshon_task_date
                from notion_leads import clear_follow_up_date
                lead_name = params["lead_name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                task_id = find_shimshon_task(lead_name)
                action = params["action"]
                if action == "cancel":
                    if task_id:
                        cancel_shimshon_task(task_id)
                    clear_follow_up_date(lead["id"])
                    return {
                        "success": True,
                        "message": f"פולואפ ל-{lead['name']} בוטל. Follow Up Date נמחק.",
                    }
                elif action == "update_date":
                    new_date = params.get("new_date")
                    if not new_date:
                        return {"error": "new_date נדרש עבור action='update_date'"}
                    if task_id:
                        update_shimshon_task_date(task_id, new_date)
                    update_lead_fields(lead["id"], follow_up_date=new_date)
                    return {
                        "success": True,
                        "message": f"פולואפ ל-{lead['name']} עודכן ל-{new_date}.",
                    }
                return {"error": f"action לא מוכר: {action}"}

            case "send_followup_to_shimshon":
                from shimshon_bridge import send_task_to_shimshon
                from notion_leads import _today_iso
                lead_name = params["lead_name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                task_id = send_task_to_shimshon(
                    description=params["task_description"],
                    scheduled_date=params.get("scheduled_date"),
                    due_date=params.get("due_date"),
                    notes=params.get("task_notes"),
                )
                if params.get("scheduled_date"):
                    update_lead_fields(
                        lead["id"],
                        follow_up_date=params["scheduled_date"],
                        last_communication=_today_iso(),
                    )
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"משימה נשלחה לשמשון עבור {lead['name']}",
                }

            case "close_lead_won":
                from shimshon_bridge import send_task_to_shimshon
                from notion_leads import _today_iso
                lead_name = params["lead_name"]
                lead = get_lead_by_name(lead_name)
                if not lead:
                    suggestions = get_task_suggestions(lead_name)
                    return _not_found_response(lead_name, suggestions)
                update_lead_status(lead["id"], "סגור — זכינו ✅")
                update_lead_fields(
                    lead["id"],
                    final_price=params.get("final_price"),
                    location=params.get("location"),
                    last_communication=_today_iso(),
                )
                event_date = params["event_date"]
                event_time = params["event_time"]
                location = params.get("location", "")
                task_desc = f"תוסיף ליומן: {lead['name']} | {event_date} {event_time} | {location}".strip(" |")
                send_task_to_shimshon(task_desc, scheduled_date=_today_iso())
                return {
                    "success": True,
                    "message": f"עסקה נסגרה ✅ | {lead['name']} | {event_date} {event_time}",
                }

            case "draft_customer_message":
                from notion_leads import get_lead_context_for_message
                context = get_lead_context_for_message(params["lead_name"])
                if not context.get("found"):
                    from notion_leads import get_task_suggestions
                    suggestions = get_task_suggestions(params["lead_name"])
                    return _not_found_response(params["lead_name"], suggestions)
                return {
                    "lead_context": context,
                    "message_type": params["message_type"],
                    "extra_context": params.get("context", ""),
                }

            case _:
                logger.warning("execute_tool: unknown tool '%s'", name)
                return {"error": f"כלי לא מוכר: '{name}'"}

    except Exception as e:
        logger.error("execute_tool '%s' failed: %s", name, e)
        return {"error": str(e)}
