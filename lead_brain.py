import base64
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta

from anthropic import Anthropic
from dotenv import load_dotenv

from interaction_log import log_interaction

load_dotenv()

logger = logging.getLogger(__name__)

_api_key = os.getenv("ANTHROPIC_API_KEY")
if not _api_key:
    logger.error("ANTHROPIC_API_KEY is not set — Claude calls will fail")

client = Anthropic(api_key=_api_key)
MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 10

# ─── Context loader ───────────────────────────────────────────────────────────

_CONTEXT_DIR = os.path.join(os.path.dirname(__file__), "context")


def _load_context_file(filename: str) -> str:
    path = os.path.join(_CONTEXT_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
        return content if content else ""
    except FileNotFoundError:
        return ""


SIVAN_PROMPT = """\
שם: סיוון
תפקיד: CRM Manager של עדן — לידים, פייפליין, אירועי מוזיקה, ניסוח הודעות.
שפה: תמיד עברית, לשון נקבה.
טון: עסקית-ידידותית, קצרה, ממוקדת.

━━━ מה שסיוון עושה ━━━
- מוסיפה ומעדכנת לידים בפייפליין
- קוראת צילומי מסך ומחלצת מידע
- מנסחת הודעות ללקוחות שעדן מעתיק ושולח
- שולחת פולואפים לשמשון כמשימות
- רושמת אירועי מוזיקה עם פרטי תשלום

━━━ מה שסיוון לא עושה ━━━
- לא שולחת הודעות ללקוחות בעצמה
- לא מנהלת יומן ישירות (זה דרך שמשון)
- לא יוצרת ליד בלי שם + סוג אירוע לפחות
- לא מניחה status — תמיד שואלת אם לא ברור

━━━ קריאת צילומי מסך ━━━
כשעדן שולח תמונה של שיחה:
1. חלצי את כל הפרטים: שם שולח, תאריך אירוע, מיקום, סוג אירוע, תקציב — כל מה שמוזכר
2. אם יש timestamp על ההודעה בתמונה (למשל "MAY 6 AT 15:43") — זה ה-Last Communication
3. הוסיפי ליד עם כל הפרטים — כולל location בפרמטר location של add_lead. אל תכתוב location לNotes
4. חובה להשתמש בשמות העבריים המדויקים לשדה source: עמית/חבר, אתר, פייסבוק, אינסטגרם, גוגל, אחר
5. אחרי add_lead — קראי גם ל-update_lead_fields עם last_communication=תאריך ההודעה
6. הצגי תמיד את כל הנתונים שמצאת בפירוט לפני שעושה כל פעולה. אל תשאלי "האם המיקום נכון?" — פשוט הצגי הכל. עדן יתקן מה שלא נכון.
7. אחרי יצירת הליד — רשמי בפירוש מה הוספת לאיזה שדה, ומה לא נמצא בתמונה
8. הציעי טיוטת תגובה שעדן יכול להעתיק ולשלוח

━━━ אמביגואיות ━━━
- "דיברתי עם רון" → "על מה? ליד חדש? הערה? עדכון status?"
- תמיד שואלת שאלה אחת בלבד בכל פעם

━━━ שליחת משימות לשמשון ━━━
לאחר שקראת ל-send_followup_to_shimshon — אל תקראי לכלי שוב באותה שיחה.
סיימת. אשרי בקצרה שהמשימה נשלחה וחכי להודעה הבאה.

━━━ פולואפים ━━━
- בכל הצעת מחיר → "מתי לשלוח פולואפ?"
- בכל עדכון status → מעדכנת last_communication לאוטומטי

━━━ fuzzy match ━━━
- שם לא נמצא בדיוק → מציגה 2-3 הצעות קרובות, שואלת לאישור
- לעולם לא עורכת ליד שגוי

━━━ אחרי סגירת עסקה ━━━
- תמיד שואלת אם לנסח הודעת אישור ללקוח
- תמיד שואלת על שעת האירוע (לשמשון)

━━━ תאריך היום ━━━
{today}

━━━ ימי השבוע הקרוב ━━━
{week_dates}

━━━ מידע על עדן ━━━
{about_eden}

━━━ דומיין מוזיקה ━━━
{music_business}
"""


_HEBREW_DAYS = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


def _week_dates_string(now: datetime) -> str:
    """Return a string mapping Hebrew day names to YYYY-MM-DD for the current week."""
    # weekday(): Mon=0 … Sun=6
    lines = []
    for offset in range(7):
        day = now + timedelta(days=offset)
        hebrew = _HEBREW_DAYS[day.weekday()]  # Mon→שני … Sun→ראשון
        lines.append(f"יום {hebrew} = {day.strftime('%Y-%m-%d')}")
    return "\n".join(lines)


def _build_system_prompt() -> str:
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    today = now.strftime("%A %d/%m/%Y %H:%M") + " (שעון ישראל)"
    about_eden = _load_context_file("about-eden.md") or "—"
    music_business = _load_context_file("music-business.md") or "—"
    week_dates = _week_dates_string(now)
    return SIVAN_PROMPT.format(
        today=today,
        about_eden=about_eden,
        music_business=music_business,
        week_dates=week_dates,
    )


# ─── Agent loop ───────────────────────────────────────────────────────────────

def get_response_with_tools(message: str, history: list, user_id: int = 0) -> str:
    from tools_definition import TOOL_DEFINITIONS
    from tools_executor import execute_tool

    start_ts = time.monotonic()
    all_tool_calls: list = []
    all_tool_results: list = []
    iterations = 0
    history_size = len(history)

    def _emit_log(final_response: str, error: str | None = None) -> None:
        log_interaction(
            user_id=user_id,
            user_input=message,
            history_size=history_size,
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            final_response=final_response,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
            iterations=iterations,
            error=error,
        )

    system = _build_system_prompt()
    messages = list(history[-20:]) + [{"role": "user", "content": message}]

    for _ in range(MAX_ITERATIONS):
        iterations += 1
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except Exception as e:
            logger.error("get_response_with_tools API call failed: %s", e)
            final = "סליחה, לא הצלחתי לעבד. נסי שוב."
            _emit_log(final, error=f"API call failed: {type(e).__name__}: {e}")
            return final

        if resp.stop_reason == "end_turn":
            text_blocks = [b.text for b in resp.content if hasattr(b, "text")]
            final = "\n".join(text_blocks).strip() or "בוצע."
            _emit_log(final)
            return final

        if resp.stop_reason == "tool_use":
            tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
            api_tool_results = []
            for tc in tool_use_blocks:
                logger.info("Tool call: %s %s", tc.name, tc.input)
                all_tool_calls.append({"name": tc.name, "input": dict(tc.input)})
                result = execute_tool(tc.name, tc.input)
                logger.info("Tool result: %s", result)
                all_tool_results.append({"name": tc.name, "result": result})
                api_tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": api_tool_results})
            continue

        logger.warning("Unexpected stop_reason: %s", resp.stop_reason)
        final = "סליחה, לא הצלחתי להשלים את הפעולה."
        _emit_log(final, error=f"unexpected stop_reason: {resp.stop_reason}")
        return final

    final = "סליחה, לא הצלחתי להשלים את הפעולה."
    _emit_log(final, error=f"max iterations ({MAX_ITERATIONS}) exhausted")
    return final


def get_response_with_image(
    image_bytes: bytes,
    caption: str,
    history: list,
    user_id: int = 0,
) -> str:
    from tools_definition import TOOL_DEFINITIONS
    from tools_executor import execute_tool

    start_ts = time.monotonic()
    all_tool_calls: list = []
    all_tool_results: list = []
    iterations = 0
    history_size = len(history)
    user_input_desc = f"[תמונה] {caption}".strip()

    def _emit_log(final_response: str, error: str | None = None) -> None:
        log_interaction(
            user_id=user_id,
            user_input=user_input_desc,
            history_size=history_size,
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            final_response=final_response,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
            iterations=iterations,
            error=error,
        )

    system = _build_system_prompt()

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    image_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_b64,
            },
        },
        {
            "type": "text",
            "text": caption if caption else "קרא את צילום המסך, חלץ מידע ונסח תגובה מתאימה.",
        },
    ]

    messages = list(history[-20:]) + [{"role": "user", "content": image_content}]

    for _ in range(MAX_ITERATIONS):
        iterations += 1
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except Exception as e:
            logger.error("get_response_with_image API call failed: %s", e)
            final = "סליחה, לא הצלחתי לקרוא את התמונה. נסי שוב."
            _emit_log(final, error=f"API call failed: {type(e).__name__}: {e}")
            return final

        if resp.stop_reason == "end_turn":
            text_blocks = [b.text for b in resp.content if hasattr(b, "text")]
            final = "\n".join(text_blocks).strip() or "בוצע."
            _emit_log(final)
            return final

        if resp.stop_reason == "tool_use":
            tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
            api_tool_results = []
            for tc in tool_use_blocks:
                logger.info("Tool call (image): %s %s", tc.name, tc.input)
                all_tool_calls.append({"name": tc.name, "input": dict(tc.input)})
                result = execute_tool(tc.name, tc.input)
                logger.info("Tool result: %s", result)
                all_tool_results.append({"name": tc.name, "result": result})
                api_tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": api_tool_results})
            continue

        logger.warning("Unexpected stop_reason (image): %s", resp.stop_reason)
        final = "סליחה, לא הצלחתי להשלים את הפעולה."
        _emit_log(final, error=f"unexpected stop_reason: {resp.stop_reason}")
        return final

    final = "סליחה, לא הצלחתי להשלים את הפעולה."
    _emit_log(final, error=f"max iterations ({MAX_ITERATIONS}) exhausted")
    return final
