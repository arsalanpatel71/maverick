import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from auth.dependencies import get_current_user, get_share_store, get_user_store
from shares.store import ShareStore
from users.store import UserStore

router = APIRouter(prefix="/shares", tags=["shares"])


class ShareRequest(BaseModel):
    email: str
    access: str

    @field_validator("access")
    @classmethod
    def validate_access(cls, v: str) -> str:
        if v not in ("read", "write"):
            raise ValueError("access must be 'read' or 'write'")
        return v


@router.post("/{resource_type}/{resource_id}", status_code=status.HTTP_201_CREATED)
async def share_resource(
    resource_type: str,
    resource_id: str,
    body: ShareRequest,
    me: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
    share_store: ShareStore = Depends(get_share_store),
):
    if resource_type not in ("agent", "rag"):
        raise HTTPException(status_code=400, detail="resource_type must be 'agent' or 'rag'")

    target = await asyncio.to_thread(user_store.get_by_email, body.email)
    if not target:
        raise HTTPException(status_code=404, detail=f"No user with email {body.email}")
    if target["_id"] == me["id"]:
        raise HTTPException(status_code=400, detail="Cannot share with yourself")

    existing = await asyncio.to_thread(
        share_store.get_user_access, resource_type, resource_id, target["_id"]
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Already shared with {body.email} ({existing} access)",
        )

    share = await asyncio.to_thread(
        share_store.create,
        resource_type=resource_type,
        resource_id=resource_id,
        owner_id=me["id"],
        shared_with_id=target["_id"],
        shared_with_email=body.email,
        access=body.access,
    )
    return {"id": share["_id"], "email": body.email, "access": body.access}


@router.get("/{resource_type}/{resource_id}")
async def list_shares(
    resource_type: str,
    resource_id: str,
    _: dict = Depends(get_current_user),
    share_store: ShareStore = Depends(get_share_store),
):
    shares = await asyncio.to_thread(share_store.list_for_resource, resource_type, resource_id)
    return [
        {"id": s["_id"], "email": s["shared_with_email"], "access": s["access"]}
        for s in shares
    ]


@router.delete("/{resource_type}/{resource_id}/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    resource_type: str,
    resource_id: str,
    share_id: str,
    _: dict = Depends(get_current_user),
    share_store: ShareStore = Depends(get_share_store),
):
    ok = await asyncio.to_thread(share_store.delete, share_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Share not found")
