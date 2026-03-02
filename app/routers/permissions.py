"""API routes for Permission CRUD.

  GET  /api/permissions        — any authenticated user
  POST /api/permissions        — admin+
  DELETE /api/permissions/{pk} — admin+
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user, require_admin
from models import Permission, engine
from schemas import PermissionIn

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("")
async def list_permissions(current: CurrentUser = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        rows = (await db.execute(select(Permission))).scalars().all()
    return JSONResponse([{"id": p.id, "name": p.name} for p in rows])


@router.post("", status_code=201)
async def create_permission(
    body: PermissionIn,
    current: CurrentUser = Depends(require_admin),
):
    async with AsyncSession(engine) as db:
        p = Permission(name=body.name)
        db.add(p)
        await db.commit()
        await db.refresh(p)
    return JSONResponse({"id": p.id, "name": p.name}, status_code=201)


@router.delete("/{pk}")
async def delete_permission(
    pk: int,
    current: CurrentUser = Depends(require_admin),
):
    async with AsyncSession(engine) as db:
        obj = await db.get(Permission, pk)
        if obj is None:
            raise HTTPException(404)
        await db.delete(obj)
        await db.commit()
    return JSONResponse({"detail": "deleted"})
