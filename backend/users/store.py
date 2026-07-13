"""MongoDB users collection — single source of truth for user records."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pymongo.collection import Collection

from agents.services.agent_store import _client as _get_client
from services.utils import utc_now as _utc_now

PERIOD_SECONDS = {"daily": 86400, "weekly": 604800, "monthly": 2592000}  # 30 days


def _users_col() -> Collection:
    from agents.services.agent_store import _client
    if _client is None:
        raise RuntimeError("MongoDB not configured")
    return _client["sales"]["users"]


class UserStore:
    def create(
        self,
        *,
        email: str,
        name: str,
        password_hash: str,
        role: str = "member",
        credits_limit: float = 10.0,
        credits_period: str = "monthly",
    ) -> dict:
        col = _users_col()
        now = _utc_now()
        doc = {
            "_id": str(uuid4()),
            "email": email.lower().strip(),
            "name": name,
            "password_hash": password_hash,
            "role": role,
            "credits_limit": credits_limit,
            "credits_period": credits_period,
            "credits_period_start": now,
            "credits_used": 0.0,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        col.insert_one(doc)
        return doc

    def get_by_email(self, email: str) -> dict | None:
        return _users_col().find_one({"email": email.lower().strip()})

    def get_by_id(self, user_id: str) -> dict | None:
        return _users_col().find_one({"_id": user_id})

    def list_all(self) -> list[dict]:
        return list(_users_col().find({}, {"password_hash": 0}).sort("created_at", -1))

    def update_credits_config(self, user_id: str, limit: float, period: str) -> bool:
        if period not in PERIOD_SECONDS:
            period = "monthly"
        res = _users_col().update_one(
            {"_id": user_id},
            {"$set": {
                "credits_limit": limit,
                "credits_period": period,
                "credits_used": 0.0,
                "credits_period_start": _utc_now(),
                "updated_at": _utc_now(),
            }},
        )
        return res.modified_count > 0

    def check_and_reset_period(self, user_id: str) -> dict | None:
        """Reset credits_used if the current period has elapsed. Returns updated doc."""
        col = _users_col()
        doc = col.find_one({"_id": user_id})
        if not doc:
            return None
        period = doc.get("credits_period", "monthly")
        period_start = doc.get("credits_period_start")
        if period_start is None:
            period_start = doc.get("created_at", _utc_now())
        secs = PERIOD_SECONDS.get(period, PERIOD_SECONDS["monthly"])
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=timezone.utc)
        now = _utc_now()
        if (now - period_start).total_seconds() >= secs:
            col.update_one(
                {"_id": user_id},
                {"$set": {"credits_used": 0.0, "credits_period_start": now, "updated_at": now}},
            )
            doc["credits_used"] = 0.0
            doc["credits_period_start"] = now
        return doc

    def increment_credits_used(self, user_id: str, amount: float) -> None:
        _users_col().update_one(
            {"_id": user_id},
            {"$inc": {"credits_used": amount}, "$set": {"updated_at": _utc_now()}},
        )

    def deactivate(self, user_id: str) -> bool:
        res = _users_col().update_one(
            {"_id": user_id},
            {"$set": {"is_active": False, "updated_at": _utc_now()}},
        )
        return res.modified_count > 0

    def exists_any(self) -> bool:
        return _users_col().count_documents({}) > 0
