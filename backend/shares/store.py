from uuid import uuid4

from agents.services.agent_store import shares_collection
from services.utils import utc_now as _utc_now


class ShareStore:
    def create(
        self,
        *,
        resource_type: str,
        resource_id: str,
        owner_id: str,
        shared_with_id: str,
        shared_with_email: str,
        access: str,
    ) -> dict:
        doc = {
            "_id": str(uuid4()),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "owner_id": owner_id,
            "shared_with_id": shared_with_id,
            "shared_with_email": shared_with_email,
            "access": access,
            "created_at": _utc_now(),
        }
        shares_collection().insert_one(doc)
        return doc

    def list_for_resource(self, resource_type: str, resource_id: str) -> list[dict]:
        return list(shares_collection().find(
            {"resource_type": resource_type, "resource_id": resource_id}
        ))

    def get_user_access(self, resource_type: str, resource_id: str, user_id: str) -> str | None:
        doc = shares_collection().find_one({
            "resource_type": resource_type,
            "resource_id": resource_id,
            "shared_with_id": user_id,
        })
        return doc["access"] if doc else None

    def delete(self, share_id: str) -> bool:
        return shares_collection().delete_one({"_id": share_id}).deleted_count > 0
