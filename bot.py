import asyncio
import io
import logging
import os
from collections import defaultdict

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from lead_brain import get_response_with_tools, get_response_with_image

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Per-user conversation history: user_id → list of {role, content}
_history: dict[int, list] = defaultdict(list)
MAX_HISTORY_TURNS = 10  # keep last 10 user+assistant pairs = 20 messages


def _add_to_history(user_id: int, role: str, content: str):
    _history[user_id].append({"role": role, "content": content})
    max_msgs = MAX_HISTORY_TURNS * 2
    if len(_history[user_id]) > max_msgs:
        _history[user_id] = _history[user_id][-max_msgs:]


# ──────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "עדן"
    await update.message.reply_text(
        f"שלום {name}! אני סיוון — מנהלת הלידים שלך.\n\n"
        "אני מנהלת את הפייפליין שלך, מעדכנת לידים ב-Notion, קוראת צילומי מסך\n"
        "ומנסחת הודעות ללקוחות.\n\n"
        "מה קורה?"
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _history[user_id] = []
    await update.message.reply_text("היסטוריית השיחה נוקתה.")


# ──────────────────────────────────────────────
# Message handlers
# ──────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    await update.message.chat.send_action(ChatAction.TYPING)

    history = _history[user_id]
    response_text = get_response_with_tools(text, history, user_id=user_id)

    _add_to_history(user_id, "user", text)
    _add_to_history(user_id, "assistant", response_text)

    pm = ParseMode.MARKDOWN if any(c in response_text for c in ("*", "_", "`", "[")) else None
    try:
        await update.message.reply_text(response_text, parse_mode=pm)
    except Exception:
        await update.message.reply_text(response_text, parse_mode=None)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caption = update.message.caption or ""

    await update.message.chat.send_action(ChatAction.TYPING)

    # Download highest-res photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    history = _history[user_id]
    response_text = get_response_with_image(
        image_bytes=image_bytes,
        caption=caption,
        history=history,
        user_id=user_id,
    )

    _add_to_history(user_id, "user", f"[תמונה] {caption}".strip())
    _add_to_history(user_id, "assistant", response_text)

    pm = ParseMode.MARKDOWN if any(c in response_text for c in ("*", "_", "`", "[")) else None
    try:
        await update.message.reply_text(response_text, parse_mode=pm)
    except Exception:
        await update.message.reply_text(response_text, parse_mode=None)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

async def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not set in .env")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("סיוון מתחילה לרוץ 🚀")
        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
