"""Auth middleware — reads httpOnly cookie and attaches user to request.state."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from auth.service import COOKIE_NAME, decode_token

_PUBLIC = {"/auth/login", "/health", "/openapi.json", "/docs", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None

        token = request.cookies.get(COOKIE_NAME)
        if token:
            payload = decode_token(token)
            if payload:
                request.state.user = {
                    "id": payload["sub"],
                    "email": payload["email"],
                    "role": payload["role"],
                }

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if path in _PUBLIC or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        if request.state.user is None:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        return await call_next(request)
