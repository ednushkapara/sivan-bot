"""
notion_leads.py — all Notion read/write for Sivan's CRM.

STUB — Phase 1 implementation. All functions raise NotImplementedError.
Real implementation starts in P1.1.
"""

import logging

logger = logging.getLogger(__name__)


def create_lead(params: dict) -> str:
    """Create a new lead in Notion Leads DB. Returns page_id."""
    raise NotImplementedError("P1.1 — not yet implemented")


def get_leads(filters: dict) -> list:
    """Get leads with optional filters (status, event_type, from_date, to_date, limit)."""
    raise NotImplementedError("P1.1 — not yet implemented")


def get_lead_by_name(name: str) -> dict | None:
    """Exact-match lookup by lead name. Returns page dict or None."""
    raise NotImplementedError("P1.1 — not yet implemented")


def get_task_suggestions(query: str, top_n: int = 3) -> list:
    """Fuzzy-match lead names. Returns list of {name, page_id} suggestions."""
    raise NotImplementedError("P1.1 — not yet implemented")


def update_lead_status(page_id: str, status: str, note: str | None = None) -> dict:
    """Update a lead's Status select. Optionally append a timestamped note."""
    raise NotImplementedError("P1.1 — not yet implemented")


def update_lead_fields(page_id: str, **kwargs) -> dict:
    """Update arbitrary lead fields. kwargs match Leads DB property names."""
    raise NotImplementedError("P1.1 — not yet implemented")


def add_lead_note(page_id: str, note: str) -> dict:
    """Append a timestamped note to a lead's Notes field."""
    raise NotImplementedError("P1.1 — not yet implemented")


def get_pipeline_summary() -> dict:
    """Return lead counts and total value grouped by Status."""
    raise NotImplementedError("P1.1 — not yet implemented")


def get_due_followups(days_ahead: int = 3) -> list:
    """Return leads whose Follow Up Date is within the next N days."""
    raise NotImplementedError("P1.1 — not yet implemented")
