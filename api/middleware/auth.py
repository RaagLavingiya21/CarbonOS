"""Supabase JWT authentication for FastAPI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

load_dotenv()

PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

PUBLIC_PREFIXES: tuple[str, ...] = (
    "/docs/",
    "/redoc/",
)


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    access_token: str


_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not supabase_url:
            raise RuntimeError("SUPABASE_URL must be set for JWT verification.")
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        _jwk_client = PyJWKClient(jwks_url)
    return _jwk_client


def verify_supabase_jwt(token: str) -> str:
    """Verify a Supabase access token and return the user UUID."""
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    try:
        if jwt_secret:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256", "HS256"],
                audience="authenticated",
            )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (sub) claim.",
        )
    return str(user_id)


def _is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    """Verify Supabase JWT on protected routes and attach user context to request.state."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable):
        if request.method == "OPTIONS" or _is_public_path(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header."},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing bearer token."},
            )

        try:
            user_id = verify_supabase_jwt(token)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        request.state.user_id = user_id
        request.state.access_token = token
        return await call_next(request)


def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency: return authenticated user from request.state."""
    user_id = getattr(request.state, "user_id", None)
    access_token = getattr(request.state, "access_token", None)
    if not user_id or not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return CurrentUser(user_id=str(user_id), access_token=str(access_token))


CurrentUserDep = Depends(get_current_user)
