import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from capsules.models import CapsuleRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _capsules_col():
    from agents.services.agent_store import capsules_collection
    return capsules_collection()


def _doc_to_record(doc: dict) -> CapsuleRecord:
    return CapsuleRecord(
        capsule_id=doc["_id"],
        agent_id=doc["agent_id"],
        session_id=doc.get("session_id"),
        user_id=doc.get("user_id"),
        format_type=doc["format_type"],
        name=doc["name"],
        description=doc["description"],
        data=doc.get("data"),
        metadata=doc.get("metadata") or {},
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class CapsuleStore:
    def save(
        self,
        *,
        agent_id: str,
        session_id: str | None,
        user_id: str | None,
        format_type: str,
        name: str,
        description: str,
        data: Any,
        metadata: dict | None = None,
        capsule_id: str | None = None,
    ) -> CapsuleRecord:
        coll = _capsules_col()
        cid = capsule_id or str(uuid4())
        now = _utc_now()
        meta = metadata or {}

        existing = coll.find_one({"_id": cid})
        if existing:
            coll.update_one(
                {"_id": cid},
                {"$set": {
                    "format_type": format_type,
                    "name": name,
                    "description": description,
                    "data": data,
                    "metadata": meta,
                    "updated_at": now,
                }},
            )
            doc = coll.find_one({"_id": cid})
        else:
            doc = {
                "_id": cid,
                "agent_id": agent_id,
                "session_id": session_id,
                "user_id": user_id,
                "format_type": format_type,
                "name": name,
                "description": description,
                "data": data,
                "metadata": meta,
                "created_at": now,
                "updated_at": now,
            }
            coll.insert_one(doc)

        return _doc_to_record(doc)

    def get(self, capsule_id: str) -> CapsuleRecord | None:
        doc = _capsules_col().find_one({"_id": capsule_id})
        return _doc_to_record(doc) if doc else None

    def list_for_session(self, session_id: str) -> list[CapsuleRecord]:
        docs = _capsules_col().find({"session_id": session_id}).sort("created_at", 1)
        return [_doc_to_record(d) for d in docs]

    def list_for_agent(self, agent_id: str, user_id: str | None = None) -> list[CapsuleRecord]:
        query: dict = {"agent_id": agent_id}
        if user_id:
            query["user_id"] = user_id
        docs = _capsules_col().find(query).sort("created_at", -1).limit(100)
        return [_doc_to_record(d) for d in docs]

    def delete(self, capsule_id: str, user_id: str | None = None) -> bool:
        query: dict[str, Any] = {"_id": capsule_id}
        if user_id:
            query["user_id"] = user_id
        res = _capsules_col().delete_one(query)
        return res.deleted_count > 0

    def update_metadata(self, capsule_id: str, metadata: dict) -> None:
        _capsules_col().update_one(
            {"_id": capsule_id},
            {"$set": {"metadata": metadata, "updated_at": _utc_now()}},
        )
