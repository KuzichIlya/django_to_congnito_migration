"""API routes for Role CRUD.

  GET  /api/roles        — any authenticated user
  POST /api/roles        — admin+
  DELETE /api/roles/{pk} — admin+
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user, require_admin
from models import Permission, Role, engine
from schemas import RoleIn

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("")
async def list_roles(current: CurrentUser = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        rows = (await db.execute(select(Role))).scalars().all()
        result = []
        for r in rows:
            await db.refresh(r, ["permissions"])
            result.append({
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "permission_ids": [p.id for p in r.permissions],
            })
    return JSONResponse(result)


@router.post("", status_code=201)
async def create_role(
    body: RoleIn,
    current: CurrentUser = Depends(require_admin),
):
    async with AsyncSession(engine) as db:
        perms = list(
            (await db.execute(select(Permission).where(Permission.id.in_(body.permission_ids))))
            .scalars().all()
        )
        r = Role(name=body.name, description=body.description, permissions=perms)
        db.add(r)
        await db.commit()
        await db.refresh(r, ["permissions"])
        # Serialize while the session is still open (avoids DetachedInstanceError)
        payload = {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permission_ids": [p.id for p in r.permissions],
        }
    return JSONResponse(payload, status_code=201)


@router.delete("/{pk}")
async def delete_role(
    pk: int,
    current: CurrentUser = Depends(require_admin),
):
    async with AsyncSession(engine) as db:
        obj = await db.get(Role, pk)
        if obj is None:
            raise HTTPException(404)
        await db.delete(obj)
        await db.commit()
    return JSONResponse({"detail": "deleted"})
