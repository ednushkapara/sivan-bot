# סיוון Bot

CRM AI agent for Eden — lead pipeline, follow-ups, music events, message drafting. Communicates via Telegram.
Named "סיוון" (female), responds in feminine Hebrew.
Peer agent to Shimshon. Runs 24/7 on Railway.

## Tech Stack
- Python (Railway) — thin infrastructure only
- Claude Sonnet 4.6 — tool_use agent loop + vision (for screenshots)
- Notion — all data (Leads, Music Events) in same workspace as Shimshon
- python-telegram-bot v21.6

## Key Files
- bot.py — Telegram handlers (text + photos)
- lead_brain.py — Claude agent loop + SIVAN_PROMPT
- notion_leads.py — all Notion read/write
- tools_definition.py — 14 tool schemas
- tools_executor.py — tool dispatch
- shimshon_bridge.py — writes follow-up tasks to Shimshon's Tasks DB
- verify_lead_schema.py — ALWAYS run before any Notion schema changes

## Rules (from Shimshon lessons)
1. Run verify_lead_schema.py before any Notion code changes.
2. DONE = BUILT + TESTED against real Notion. Not just "built."
3. Python is deterministic, Claude is creative.
4. max_tokens=4096, MAX_ITERATIONS=10 always.
5. Never commit .env, token.pickle, credentials.json.
6. Sivan responds in feminine Hebrew always.

## Shimshon Integration
- shimshon_bridge.py writes tasks with Project="סיוון" to Shimshon's Tasks DB.
- Shimshon reads them normally in /brief.
- No other communication between bots.
- Calendar events: Sivan sends task to Shimshon — "תוסיף ליומן: [event]"

## Vision Capability
- handle_photo() in bot.py handles screenshots
- get_response_with_image() in lead_brain.py passes base64 image to Claude
- Same tool_use loop, different content format

## Full Spec
Full spec: @PRD.md
Current progress: @progress.txt
