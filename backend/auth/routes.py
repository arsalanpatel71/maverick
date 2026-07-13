"""Auth routes: /auth/login, /auth/logout, /auth/me."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from auth.dependencies import get_current_user, get_user_store
from auth.service import COOKIE_NAME, TOKEN_EXPIRE_DAYS, create_token, verify_password
from settings import Settings, get_settings
from users.store import UserStore

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    store: UserStore = Depends(get_user_store),
):
    user = store.get_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_token(str(user["_id"]), user["email"], user["role"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.env == "production",
        samesite="lax",
        max_age=TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(
    user: dict = Depends(get_current_user),
    store: UserStore = Depends(get_user_store),
):
    doc = store.get_by_id(user["id"])
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "name": doc["name"],
        "role": doc["role"],
        "credits_limit": doc.get("credits_limit", 10.0),
        "credits_used": doc.get("credits_used", 0.0),
    }
