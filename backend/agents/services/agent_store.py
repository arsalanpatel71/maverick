from datetime import datetime, timezone
from uuid import uuid4

from services.utils import utc_now as _utc_now

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection

from agents.schemas import AgentProvider, AgentResponse, ConversationMessage, ManagedAgent, RAGConfig, ResponseSchema
from services.utils import name_filter

_client: MongoClient | None = None
_agents: Collection | None = None
_rags: Collection | None = None
_rag_chunks: Collection | None = None
_sessions: Collection | None = None
_traces: Collection | None = None
_shares: Collection | None = None
_skills: Collection | None = None
_capsules: Collection | None = None


def configure_agent_store(mongo_uri: str, database: str) -> None:
    """Call once at startup. Raises if URI is missing or the server is unreachable."""
    global _client, _agents, _rags, _rag_chunks, _sessions, _traces, _shares, _skills, _capsules
    if not mongo_uri.strip():
        raise ValueError("MONGO_URI is not set or empty")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    _client = client
    db = client[database]
    _agents = db["agents"]
    _rags = db["rags"]
    _rag_chunks = db["rag_chunks"]
    _sessions = db["sessions"]
    _sessions.create_index("session_id", unique=True, background=True)
    _traces = db["traces"]
    _traces.create_index([("agent_id", 1), ("created_at", -1)], background=True)
    _shares = db["shares"]
    _shares.create_index([("resource_type", 1), ("resource_id", 1)], background=True)
    _shares.create_index([("shared_with_id", 1)], background=True)
    _skills = db["skills"]
    _skills.create_index("name", unique=True, background=True)
    _capsules = db["capsules"]
    _capsules.create_index([("session_id", 1), ("created_at", 1)], background=True)
    _capsules.create_index([("agent_id", 1), ("user_id", 1), ("created_at", -1)], background=True)


def close_agent_store() -> None:
    global _client, _agents, _rags, _rag_chunks, _sessions, _traces, _shares, _skills, _capsules
    if _client is not None:
        _client.close()
    _client = None
    _agents = None
    _rags = None
    _rag_chunks = None
    _sessions = None
    _traces = None
    _shares = None
    _skills = None
    _capsules = None


def _collection() -> Collection:
    if _agents is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _agents


def rags_collection() -> Collection:
    if _rags is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _rags


def rag_chunks_collection() -> Collection:
    if _rag_chunks is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _rag_chunks


def sessions_collection() -> Collection:
    if _sessions is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _sessions


def traces_collection() -> Collection:
    if _traces is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _traces


def shares_collection() -> Collection:
    if _shares is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _shares


def skills_collection() -> Collection:
    if _skills is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _skills


def capsules_collection() -> Collection:
    if _capsules is None:
        raise RuntimeError("MongoDB is not configured; call configure_agent_store at startup")
    return _capsules


def _doc_to_response(doc: dict) -> AgentResponse:
    created = doc["created_at"]
    updated = doc["updated_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    if isinstance(updated, str):
        updated = datetime.fromisoformat(updated)
    rag_raw = doc.get("rag_config")
    managed_raw = doc.get("managed_agents") or []
    schema_raw = doc.get("response_schema")
    return AgentResponse(
        id=doc["_id"],
        role=doc["role"],
        goal=doc["goal"],
        instructions=doc["instructions"],
        model=doc["model"],
        provider=AgentProvider(doc["provider"]),
        memory_enabled=bool(doc.get("memory_enabled", False)),
        memory_max_messages=doc.get("memory_max_messages"),
        rag_config=RAGConfig(**rag_raw) if rag_raw else None,
        managed_agents=[ManagedAgent(**m) for m in managed_raw],
        response_schema=ResponseSchema(**schema_raw) if schema_raw else None,
        skill_ids=doc.get("skill_ids") or [],
        created_at=created,
        updated_at=updated,
        name=doc.get("name") or doc.get("role", ""),
    )


class AgentStore:
    def create(
        self,
        *,
        name: str,
        role: str,
        goal: str,
        instructions: str,
        model: str,
        provider: AgentProvider,
        memory_enabled: bool = False,
        memory_max_messages: int | None = None,
        rag_config: RAGConfig | None = None,
        managed_agents: list[ManagedAgent] | None = None,
        response_schema: ResponseSchema | None = None,
        skill_ids: list[str] | None = None,
        owner_id: str | None = None,
    ) -> AgentResponse:
        coll = _collection()
        agent_id = str(uuid4())
        now = _utc_now()
        doc = {
            "_id": agent_id,
            "name": name,
            "role": role,
            "goal": goal,
            "instructions": instructions,
            "model": model,
            "provider": provider.value,
            "memory_enabled": memory_enabled,
            "memory_max_messages": memory_max_messages,
            "rag_config": rag_config.model_dump() if rag_config else None,
            "managed_agents": [m.model_dump() for m in managed_agents] if managed_agents else [],
            "response_schema": response_schema.model_dump() if response_schema else None,
            "skill_ids": skill_ids or [],
            "created_at": now,
            "updated_at": now,
            "owner_id": owner_id,
        }
        coll.insert_one(doc)
        return _doc_to_response(doc)

    def get(self, agent_id: str) -> AgentResponse | None:
        coll = _collection()
        doc = coll.find_one({"_id": agent_id})
        return _doc_to_response(doc) if doc else None

    def get_owner_id(self, agent_id: str) -> tuple[bool, str | None]:
        """Return (found, owner_id). found=False when the agent does not exist."""
        doc = _collection().find_one({"_id": agent_id}, {"owner_id": 1})
        if not doc:
            return False, None
        return True, doc.get("owner_id")

    def list_for_user(self, user_id: str, q: str | None = None) -> list[AgentResponse]:
        """Return agents owned by user, shared with user, or legacy (no owner_id)."""
        coll = _collection()
        shared_ids = [
            s["resource_id"]
            for s in shares_collection().find(
                {"resource_type": "agent", "shared_with_id": user_id}, {"resource_id": 1}
            )
        ]
        access_filter: dict = {"$or": [
            {"owner_id": user_id},
            {"owner_id": None},
            {"_id": {"$in": shared_ids}},
        ]}
        nf = name_filter(q, "name", "role")
        query = {"$and": [access_filter, nf]} if nf else access_filter
        cursor = coll.find(query).sort("updated_at", -1)
        return [_doc_to_response(doc) for doc in cursor]

    def update(self, agent_id: str, fields: dict) -> AgentResponse | None:
        allowed = (
            "name",
            "role",
            "goal",
            "instructions",
            "model",
            "provider",
            "memory_enabled",
            "memory_max_messages",
            "rag_config",
            "managed_agents",
            "response_schema",
            "skill_ids",
        )
        updates = {k: v for k, v in fields.items() if k in allowed}
        updates = {k: v for k, v in updates.items() if v is not None or k in ("memory_max_messages", "rag_config", "response_schema")}
        if not updates:
            return self.get(agent_id)
        updates["updated_at"] = _utc_now()
        coll = _collection()
        result = coll.find_one_and_update(
            {"_id": agent_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            return None
        return _doc_to_response(result)

    def delete(self, agent_id: str) -> bool:
        coll = _collection()
        res = coll.delete_one({"_id": agent_id})
        return res.deleted_count > 0

    def clone(self, agent_id: str, owner_id: str | None = None) -> AgentResponse | None:
        coll = _collection()
        doc = coll.find_one({"_id": agent_id})
        if not doc:
            return None
        now = _utc_now()
        new_doc = {k: v for k, v in doc.items()}
        new_doc["_id"] = str(uuid4())
        new_doc["name"] = f"{doc.get('name') or doc.get('role', 'Agent')} (copy)"
        new_doc["owner_id"] = owner_id
        new_doc["created_at"] = now
        new_doc["updated_at"] = now
        coll.insert_one(new_doc)
        return _doc_to_response(new_doc)


class SessionMemory:
    def get_history(
        self, session_id: str, max_messages: int = 20
    ) -> list[ConversationMessage]:
        coll = sessions_collection()
        doc = coll.find_one(
            {"session_id": session_id},
            {"messages": {"$slice": -max_messages}},
        )
        if not doc:
            return []
        return [
            ConversationMessage(role=m["role"], content=m["content"])
            for m in doc.get("messages", [])
        ]

    def add_turn(
        self,
        session_id: str,
        user_content: str,
        assistant_content: str,
    ) -> None:
        coll = sessions_collection()
        now = _utc_now()
        coll.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": {"$each": [
                    {"role": "user",      "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ]}},
                "$set":         {"updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def clear(self, session_id: str) -> None:
        coll = sessions_collection()
        coll.delete_one({"session_id": session_id})


class TraceStore:
    def create(self, *, agent_id: str, session_id: str | None, query: str) -> str:
        """Create a new trace document and return its trace_id."""
        coll = traces_collection()
        trace_id = str(uuid4())
        coll.insert_one({
            "_id": trace_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "query": query,
            "events": [],
            "response": None,
            "usage": None,
            "created_at": _utc_now(),
            "completed_at": None,
        })
        return trace_id

    def append_event(self, trace_id: str, event_type: str, data: dict) -> None:
        """Push one trace event onto the events array."""
        coll = traces_collection()
        coll.update_one(
            {"_id": trace_id},
            {"$push": {"events": {"type": event_type, "data": data, "ts": _utc_now()}}},
        )

    def complete(
        self,
        trace_id: str,
        response: str,
        usage: dict | None,
        *,
        user_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        cost_usd: float = 0.0,
    ) -> None:
        """Mark trace as complete with the final LLM response."""
        coll = traces_collection()
        fields: dict = {"response": response, "usage": usage, "completed_at": _utc_now(), "cost_usd": cost_usd}
        if user_id:
            fields["user_id"] = user_id
        if model:
            fields["model"] = model
        if provider:
            fields["provider"] = provider
        coll.update_one({"_id": trace_id}, {"$set": fields})

    def list_for_agent(self, agent_id: str, limit: int = 50) -> list[dict]:
        """Return recent traces for an agent (newest first), without the events array."""
        coll = traces_collection()
        docs = coll.find(
            {"agent_id": agent_id},
            {"events": 0},
        ).sort("created_at", -1).limit(limit)
        return list(docs)

    def get(self, trace_id: str) -> dict | None:
        """Return a single trace with all events."""
        coll = traces_collection()
        return coll.find_one({"_id": trace_id})
