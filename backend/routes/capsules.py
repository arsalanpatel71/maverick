import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import get_current_user
from capsules.store import CapsuleStore
from capsules.models import CapsuleRecord
from settings import get_settings

router = APIRouter(prefix="/capsules", tags=["capsules"])


class CapsuleOut(BaseModel):
    capsule_id: str
    agent_id: str
    session_id: str | None
    user_id: str | None
    format_type: str
    name: str
    description: str
    data: Any
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


def _to_out(r: CapsuleRecord) -> CapsuleOut:
    return CapsuleOut(
        capsule_id=r.capsule_id,
        agent_id=r.agent_id,
        session_id=r.session_id,
        user_id=r.user_id,
        format_type=r.format_type,
        name=r.name,
        description=r.description,
        data=r.data,
        metadata=r.metadata,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


@router.get("/")
async def list_capsules(
    session_id: str | None = None,
    agent_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    store = CapsuleStore()
    if session_id:
        records = await asyncio.to_thread(store.list_for_session, session_id)
    elif agent_id:
        records = await asyncio.to_thread(store.list_for_agent, agent_id, user["id"])
    else:
        records = await asyncio.to_thread(store.list_for_agent, "", user["id"])
    return [_to_out(r) for r in records]


@router.get("/{capsule_id}")
async def get_capsule(capsule_id: str, user: dict = Depends(get_current_user)):
    record = await asyncio.to_thread(CapsuleStore().get, capsule_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Capsule not found")
    if record.user_id and record.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return _to_out(record)


@router.delete("/{capsule_id}", status_code=204)
async def delete_capsule(capsule_id: str, user: dict = Depends(get_current_user)):
    deleted = await asyncio.to_thread(CapsuleStore().delete, capsule_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Capsule not found")


@router.post("/{capsule_id}/refresh-url")
async def refresh_capsule_url(capsule_id: str, user: dict = Depends(get_current_user)):
    settings = get_settings()
    record = await asyncio.to_thread(CapsuleStore().get, capsule_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Capsule not found")
    if record.user_id and record.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    s3_key = record.metadata.get("s3_key")
    if not s3_key:
        raise HTTPException(status_code=400, detail="This capsule has no associated file")

    from capsules.s3 import generate_presigned_url_async
    new_url = await generate_presigned_url_async(s3_key, settings)

    updated_meta = {**record.metadata, "file_url": new_url}
    await asyncio.to_thread(CapsuleStore().update_metadata, capsule_id, updated_meta)

    return {"file_url": new_url}
