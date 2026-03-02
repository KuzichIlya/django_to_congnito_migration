"""
Authentication helper routes — no bearer token required.

  POST /api/auth/token   Exchange Cognito username + password for tokens.
                         Requires USER_PASSWORD_AUTH flow enabled on the App Client.
"""

import asyncio
import logging

from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import _get_cognito_client
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/token")
async def get_token(body: LoginIn):
    """
    Exchange a Cognito username + password for an access token.

    The Cognito App Client must have **USER_PASSWORD_AUTH** enabled.
    Returns ``access_token`` (use as Bearer), ``id_token``, and ``refresh_token``.

    Common error codes:
      - 401  Invalid credentials / user not found
      - 400  Password change required or MFA challenge (not handled by this UI)
      - 500  Unexpected Cognito error
    """
    client = _get_cognito_client()

    def _initiate() -> dict:
        return client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": body.username,
                "PASSWORD": body.password,
            },
            ClientId=settings.cognito_client_id,
        )

    try:
        result = await asyncio.to_thread(_initiate)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        logger.warning("Cognito auth failed: %s — %s", code, exc.response["Error"]["Message"])
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if code == "PasswordResetRequiredException":
            raise HTTPException(status_code=400, detail="Password reset required")
        if code == "UserNotConfirmedException":
            raise HTTPException(status_code=400, detail="User account not confirmed")
        raise HTTPException(status_code=500, detail=f"Cognito error: {code}")

    challenge = result.get("ChallengeName")
    if challenge:
        # NEW_PASSWORD_REQUIRED, MFA, etc. — not handled by this simple UI
        raise HTTPException(
            status_code=400,
            detail=f"Authentication challenge required: {challenge}. "
                   "Use the AWS Console or CLI to complete it, then try again.",
        )

    auth = result["AuthenticationResult"]
    return JSONResponse({
        "access_token": auth["AccessToken"],
        "id_token": auth.get("IdToken"),
        "refresh_token": auth.get("RefreshToken"),
        "expires_in": auth.get("ExpiresIn", 3600),
        "token_type": "Bearer",
    })
