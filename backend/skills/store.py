"""MongoDB CRUD for skills."""
from uuid import uuid4

from agents.services.agent_store import skills_collection
from services.utils import name_filter, utc_now as _utc_now


class SkillStore:
    def create(
        self,
        *,
        name: str,
        description: str,
        content: str,
        source: str = "custom",
        github_url: str | None = None,
        owner_id: str | None = None,
    ) -> dict:
        coll = skills_collection()
        doc = {
            "_id": str(uuid4()),
            "name": name,
            "description": description,
            "content": content,
            "source": source,
            "github_url": github_url,
            "owner_id": owner_id,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        coll.insert_one(doc)
        return doc

    def get(self, skill_id: str) -> dict | None:
        return skills_collection().find_one({"_id": skill_id})

    def get_many(self, skill_ids: list[str]) -> list[dict]:
        if not skill_ids:
            return []
        return list(skills_collection().find({"_id": {"$in": skill_ids}}))

    def list_all(self, q: str | None = None) -> list[dict]:
        query = name_filter(q, "name", "description")
        return list(skills_collection().find(query).sort("source", 1).sort("name", 1))

    def update(self, skill_id: str, fields: dict) -> dict | None:
        allowed = {"name", "description", "content"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get(skill_id)
        updates["updated_at"] = _utc_now()
        skills_collection().update_one({"_id": skill_id}, {"$set": updates})
        return self.get(skill_id)

    def delete(self, skill_id: str) -> bool:
        return skills_collection().delete_one({"_id": skill_id}).deleted_count > 0

    def get_by_name(self, name: str) -> dict | None:
        return skills_collection().find_one({"name": name})

    def name_exists(self, name: str) -> bool:
        return skills_collection().count_documents({"name": name}) > 0
