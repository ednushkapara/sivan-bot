"""
tools_definition.py — Anthropic tool schemas for Sivan's CRM tools.
Phase 1: 8 core lead management tools.
"""

TOOL_DEFINITIONS = [

    # ─── LEADS ───────────────────────────────────────────────────────────────

    {
        "name": "add_lead",
        "description": (
            "הוסיפי ליד חדש לפייפליין. "
            "השתמשי כשעדן מזכיר פנייה חדשה מלקוח פוטנציאלי. "
            "שם + סוג אירוע הם חובה. שאר השדות אופציונליים. "
            "סטטוס ברירת מחדל: 'איסוף פרטים'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "שם הלקוח או האירוע"
                },
                "event_type": {
                    "type": "string",
                    "description": "אחד מ: חתונה, בר מצווה, בת מצווה, אירוע חברה, מסיבה, אחר"
                },
                "event_date": {
                    "type": "string",
                    "description": "תאריך האירוע — פורמט YYYY-MM-DD"
                },
                "performance_style": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "סגנונות הופעה — מתוך: קבלת פנים, ליווי חופה, מנות עיקריות, אפטר ריקודים, טברנה"
                },
                "music_style": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "סגנון מוזיקה — מתוך: מזרחית, יוונית, רגוע, מאינסטרים ישראלי, מאינסטרים לועזי"
                },
                "budget": {
                    "type": "number",
                    "description": "תקציב הלקוח בשקלים"
                },
                "contact_name": {
                    "type": "string",
                    "description": "שם איש הקשר (אם שונה מהלקוח)"
                },
                "contact_phone": {
                    "type": "string",
                    "description": "מספר טלפון"
                },
                "source": {
                    "type": "string",
                    "description": "מקור הליד — אחד מ: עמית/חבר, אתר, פייסבוק, אינסטגרם, גוגל, אחר"
                },
                "notes": {
                    "type": "string",
                    "description": "הערות ראשוניות"
                }
            },
            "required": ["name", "event_type"]
        }
    },

    {
        "name": "get_leads",
        "description": (
            "קבלי רשימת לידים מהפייפליין. "
            "השתמשי כשעדן שואל מה יש לו בפייפליין, מה הלידים הפתוחים, "
            "או רוצה לראות לידים לפי סטטוס/סוג אירוע."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "סנני לפי סטטוס ספציפי — אחד מ: איסוף פרטים, קביעת שיחת טלפון, הצעת מחיר נשלחה, במשא ומתן, סגור — זכינו ✅, סגור — הפסדנו ❌, אירוע בוצע 🎵"
                },
                "event_type": {
                    "type": "string",
                    "description": "סנני לפי סוג אירוע"
                },
                "from_date": {
                    "type": "string",
                    "description": "מתאריך אירוע (YYYY-MM-DD)"
                },
                "to_date": {
                    "type": "string",
                    "description": "עד תאריך אירוע (YYYY-MM-DD)"
                },
                "limit": {
                    "type": "integer",
                    "description": "מקסימום תוצאות (ברירת מחדל: 20)"
                }
            },
            "required": []
        }
    },

    {
        "name": "get_lead",
        "description": (
            "חפשי ליד לפי שם. "
            "השתמשי לפני כל עדכון — כדי לאמת שמצאת את הליד הנכון. "
            "אם לא נמצא בדיוק, מחזירה הצעות קרובות."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "שם הלקוח לחיפוש"
                }
            },
            "required": ["name"]
        }
    },

    {
        "name": "update_lead_status",
        "description": (
            "עדכני את הסטטוס של ליד בפייפליין. "
            "השתמשי כשעדן אומר שהתקדם עם לקוח — 'שלחתי הצעת מחיר', 'סגרנו', וכו'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "שם הלקוח"
                },
                "new_status": {
                    "type": "string",
                    "description": "הסטטוס החדש — אחד מ: איסוף פרטים, קביעת שיחת טלפון, הצעת מחיר נשלחה, במשא ומתן, סגור — זכינו ✅, סגור — הפסדנו ❌, אירוע בוצע 🎵"
                }
            },
            "required": ["name", "new_status"]
        }
    },

    {
        "name": "update_lead_fields",
        "description": (
            "עדכני שדות ספציפיים של ליד — מחיר, תאריך, מיקום, פרטי קשר וכו'. "
            "שלחי רק את השדות שצריך לעדכן."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "שם הלקוח"
                },
                "proposed_price": {
                    "type": "number",
                    "description": "הצעת מחיר בשקלים"
                },
                "final_price": {
                    "type": "number",
                    "description": "מחיר סופי מוסכם בשקלים"
                },
                "budget": {
                    "type": "number",
                    "description": "תקציב הלקוח בשקלים"
                },
                "event_date": {
                    "type": "string",
                    "description": "תאריך האירוע (YYYY-MM-DD)"
                },
                "follow_up_date": {
                    "type": "string",
                    "description": "מתי לחזור ללקוח (YYYY-MM-DD)"
                },
                "last_communication": {
                    "type": "string",
                    "description": "תאריך ההתכתבות האחרונה (YYYY-MM-DD)"
                },
                "location": {
                    "type": "string",
                    "description": "מיקום האירוע"
                },
                "contact_name": {
                    "type": "string",
                    "description": "שם איש הקשר"
                },
                "contact_phone": {
                    "type": "string",
                    "description": "מספר טלפון"
                },
                "performance_style": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "סגנונות הופעה (מחליף את הקיים)"
                },
                "music_style": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "סגנון מוזיקה (מחליף את הקיים)"
                },
                "notes": {
                    "type": "string",
                    "description": "הערה להוספה לרשומת הלקוח (מתווספת לקיים)"
                }
            },
            "required": ["name"]
        }
    },

    {
        "name": "add_lead_note",
        "description": (
            "הוסיפי הערה לליד. ההערה מתווספת עם חותמת זמן לשדה Notes. "
            "השתמשי כשעדן מספר מה קרה בשיחה, מה הלקוח אמר, וכו'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "שם הלקוח"
                },
                "note": {
                    "type": "string",
                    "description": "תוכן ההערה"
                }
            },
            "required": ["name", "note"]
        }
    },

    {
        "name": "get_pipeline_summary",
        "description": (
            "הצגי סיכום פייפליין — כמה לידים בכל שלב ומה הסכום הכולל. "
            "השתמשי כשעדן שואל 'מה יש לי בפייפליין' או 'תראי סיכום'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "get_due_followups",
        "description": (
            "הצגי לידים שצריך לעשות להם פולואפ בימים הקרובים. "
            "כוללת לידים שה-Follow Up Date שלהם עבר (overdue). "
            "השתמשי כשעדן שואל 'מה דחוף', 'מי ממתין', וכו'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "כמה ימים קדימה לבדוק (ברירת מחדל: 3)"
                }
            },
            "required": []
        }
    },

    {
        "name": "send_followup_to_shimshon",
        "description": (
            "שלחי משימת פולואפ לשמשון. "
            "השתמשי כשעדן מבקש לזכור לחזור ללקוח או לשלוח הודעה בתאריך מסוים. "
            "המשימה תופיע אצל שמשון תחת Project='סיוון'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_name": {
                    "type": "string",
                    "description": "שם הלקוח"
                },
                "task_description": {
                    "type": "string",
                    "description": "שם קצר של המשימה — לדוגמה: 'פולואפ ליוסי לוי' (לא לכלול כאן תוכן הודעה)"
                },
                "task_notes": {
                    "type": "string",
                    "description": "תוכן מפורט — הודעה לשלוח, פרטים נוספים. יכנס לשדה Notes של המשימה."
                },
                "scheduled_date": {
                    "type": "string",
                    "description": "מתי לבצע (YYYY-MM-DD)"
                },
                "due_date": {
                    "type": "string",
                    "description": "דד-ליין (YYYY-MM-DD) — רק אם עדן ציין דד-ליין"
                }
            },
            "required": ["lead_name", "task_description"]
        }
    },

    {
        "name": "close_lead_won",
        "description": (
            "סגרי עסקה — עדכני סטטוס ל'סגור — זכינו' ושלחי משימה לשמשון להוסיף ליומן. "
            "השתמשי כשעדן אומר 'סגרנו', 'אושר', 'חתמנו'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_name": {
                    "type": "string",
                    "description": "שם הלקוח"
                },
                "event_date": {
                    "type": "string",
                    "description": "תאריך האירוע (YYYY-MM-DD)"
                },
                "event_time": {
                    "type": "string",
                    "description": "שעת האירוע (HH:MM)"
                },
                "final_price": {
                    "type": "number",
                    "description": "מחיר סופי מוסכם בשקלים"
                },
                "location": {
                    "type": "string",
                    "description": "מיקום האירוע"
                }
            },
            "required": ["lead_name", "event_date", "event_time"]
        }
    },

    {
        "name": "draft_customer_message",
        "description": (
            "נסחי הודעה ללקוח — פולואפ, הצעת מחיר, אישור, או הודעה כללית. "
            "הכלי מביא את פרטי הליד, ואת ניסוח ההודעה עושה Claude. "
            "השתמשי כשעדן מבקש 'תנסחי הודעה ל...' או 'תנסחי פולואפ ל...'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_name": {
                    "type": "string",
                    "description": "שם הלקוח"
                },
                "message_type": {
                    "type": "string",
                    "description": "סוג ההודעה: פולואפ | הצעת מחיר | אישור | כללי"
                },
                "context": {
                    "type": "string",
                    "description": "הנחיה ספציפית מעדן — קצרה יותר, רשמית יותר, וכו'"
                }
            },
            "required": ["lead_name", "message_type"]
        }
    },

]
