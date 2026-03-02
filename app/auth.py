"""
Authentication layer for AWS Cognito bearer-token auth.

Exports:
  - CurrentUser          dataclass carrying verified claims + local User record
  - get_current_user     FastAPI dependency: any authenticated caller
  - require_admin        FastAPI dependency: admin or superadmin only
  - require_superadmin   FastAPI dependency: superadmin only
  - _get_cognito_client  boto3 Cognito-IDP client factory (for optional admin ops)
"""

import logging
from dataclasses import dataclass
from typing import Any

import boto3
import httpx
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User, engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS cache (refreshed once per process; auto-rotates on key-not-found)
# ---------------------------------------------------------------------------
_jwks_cache: dict[str, Any] | None = None


async def _get_jwks() -> dict[str, Any]:
    """Fetch and in-process-cache the Cognito JWKS document."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.cognito_jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------
async def _verify_cognito_token(token: str) -> dict[str, Any]:
    """
    Verify a Cognito JWT (access *or* ID token) fully offline via JWKS.

    Checks performed:
      - RS256 signature against the matching JWKS key
      - Expiry (verify_exp=True)
      - ``iss`` matches the configured Cognito user-pool issuer
      - ``token_use`` is ``"access"`` or ``"id"``
      - For ID tokens: ``aud`` matches ``cognito_client_id``

    On key-not-found the JWKS cache is flushed and refetched once
    (handles key rotation without a restart).
    """
    global _jwks_cache

    jwks = await _get_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Malformed token header: {exc}")

    kid = header.get("kid")
    key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if key is None:
        # Possibly a rotated key — clear cache and retry once
        _jwks_cache = None
        jwks = await _get_jwks()
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            raise HTTPException(status_code=401, detail="Signing key not found in JWKS")

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            # Cognito access tokens do not carry a standard aud claim;
            # we verify audience manually below for ID tokens only.
            options={"verify_aud": False, "verify_exp": True},
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    if claims.get("iss") != settings.cognito_issuer:
        raise HTTPException(status_code=401, detail="Token issuer mismatch")

    token_use = claims.get("token_use")
    if token_use == "id":
        if claims.get("aud") != settings.cognito_client_id:
            raise HTTPException(status_code=401, detail="Token audience mismatch")
    elif token_use != "access":
        raise HTTPException(
            status_code=401, detail=f"Unexpected token_use: {token_use!r}"
        )

    return claims


# ---------------------------------------------------------------------------
# boto3 Cognito-IDP client helper
# ---------------------------------------------------------------------------
def _get_cognito_client():
    """
    Return a synchronous boto3 Cognito-IDP client for the configured region.

    Useful for admin operations such as:
      ``client.admin_get_user(UserPoolId=..., Username=...)``
      ``client.admin_delete_user(UserPoolId=..., Username=...)``

    Credentials are resolved via the standard AWS chain
    (env vars, IAM role, ~/.aws/credentials).
    """
    return boto3.client("cognito-idp", region_name=settings.cognito_region)


# ---------------------------------------------------------------------------
# CurrentUser dataclass
# ---------------------------------------------------------------------------
@dataclass
class CurrentUser:
    claims: dict[str, Any]
    sub: str            # Cognito sub UUID
    username: str       # Cognito ``username`` claim, or sub as fallback
    user: User | None   # Local DB record; ``None`` if not yet linked
    is_admin: bool
    is_superadmin: bool


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """
    Dependency: parse the ``Authorization: Bearer <token>`` header,
    verify it against Cognito JWKS, and load the matching local User row.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")

    token = authorization.removeprefix("Bearer ").strip()
    claims = await _verify_cognito_token(token)

    sub: str = claims.get("sub", "")
    # Access tokens carry ``username``; ID tokens carry ``cognito:username``
    username: str = (
        claims.get("username")
        or claims.get("cognito:username")
        or sub
    )

    async with AsyncSession(engine) as db:
        result = await db.execute(select(User).where(User.cognito_sub == sub))
        user: User | None = result.scalar_one_or_none()

    return CurrentUser(
        claims=claims,
        sub=sub,
        username=username,
        user=user,
        is_admin=user.is_admin if user else False,
        is_superadmin=user.is_superadmin if user else False,
    )


async def require_admin(
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency: caller must be **admin** or **superadmin**."""
    if not current.user:
        raise HTTPException(
            status_code=403, detail="User not registered in local database"
        )
    if not (current.is_admin or current.is_superadmin):
        raise HTTPException(
            status_code=403, detail="Admin or superadmin access required"
        )
    return current


async def require_superadmin(
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency: caller must be **superadmin**."""
    if not current.user:
        raise HTTPException(
            status_code=403, detail="User not registered in local database"
        )
    if not current.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current
