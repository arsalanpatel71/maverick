# Added this because utc_now and name_filter are used across multiple stores (agents, users, RAG).
# Will add more shared helpers here as patterns emerge across services.
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def name_filter(q: str | None, *fields: str) -> dict:
    # Used in list queries to do case-insensitive regex search across name/description fields.
    if not q or not q.strip():
        return {}
    regex = {"$regex": q.strip(), "$options": "i"}
    return {"$or": [{field: regex} for field in fields]}
