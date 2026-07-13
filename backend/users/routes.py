"""Admin user management routes — super_admin only."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import get_user_store, require_super_admin
from auth.service import hash_password
from users.store import UserStore

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _safe(doc: dict) -> dict:
    doc.pop("password_hash", None)
    doc["id"] = doc.pop("_id", doc.get("id"))
    return doc


class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str
    credits_limit: float = 10.0
    credits_period: str = "monthly"
    role: str = "member"


class UpdateCreditsRequest(BaseModel):
    credits_limit: float
    credits_period: str = "monthly"


@router.get("/")
async def list_users(
    _: dict = Depends(require_super_admin),
    store: UserStore = Depends(get_user_store),
):
    users = await asyncio.to_thread(store.list_all)
    return [_safe(u) for u in users]


@router.post("/")
async def create_user(
    body: CreateUserRequest,
    _: dict = Depends(require_super_admin),
    store: UserStore = Depends(get_user_store),
):
    existing = await asyncio.to_thread(store.get_by_email, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    if body.role not in ("member", "admin", "super_admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    doc = await asyncio.to_thread(
        store.create,
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        role=body.role,
        credits_limit=body.credits_limit,
        credits_period=body.credits_period,
    )
    return _safe(doc)


@router.patch("/{user_id}/credits")
async def update_credits(
    user_id: str,
    body: UpdateCreditsRequest,
    _: dict = Depends(require_super_admin),
    store: UserStore = Depends(get_user_store),
):
    if body.credits_limit < 0:
        raise HTTPException(status_code=400, detail="Credits limit cannot be negative")
    if body.credits_period not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="Period must be daily, weekly, or monthly")
    ok = await asyncio.to_thread(store.update_credits_config, user_id, body.credits_limit, body.credits_period)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    requester: dict = Depends(require_super_admin),
    store: UserStore = Depends(get_user_store),
):
    if user_id == requester["id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    ok = await asyncio.to_thread(store.deactivate, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
