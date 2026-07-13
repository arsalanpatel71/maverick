"""Reusable FastAPI dependencies for auth, roles, and store access."""
from fastapi import Depends, HTTPException, Request, status


def get_current_user(request: Request) -> dict:
    """Raise 401 if no authenticated user attached to request.state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_optional_user(request: Request) -> dict | None:
    """Return user dict or None — never raises."""
    return getattr(request.state, "user", None)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require super_admin or admin role."""
    if user["role"] not in ("super_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require super_admin role."""
    if user["role"] != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return user


def get_user_store():
    from users.store import UserStore
    return UserStore()


def get_share_store():
    from shares.store import ShareStore
    return ShareStore()
