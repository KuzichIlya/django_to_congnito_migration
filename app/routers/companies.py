"""API routes for Company CRUD.

Access policy:
  GET    /api/companies        — admin+  (superadmin: all; admin: scope only)
  POST   /api/companies        — admin+
    • parent_id=null (root)  → superadmin only
    • child company          → admin: parent must be within caller's scope
  PATCH  /api/companies/{pk}  — admin+  (company must be in scope)
  DELETE /api/companies/{pk}  — admin+  (company must be in scope)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, require_admin
from models import Company, Permission, Role, engine
from schemas import CompanyIn, CompanyPatch
from services import assert_within_scope, load_admin_scope

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _serialise_company(c: Company) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "parent_id": c.parent_id,
        "is_hierarchical": c.is_hierarchical,
        "role_ids": [r.id for r in c.roles],
        "permission_ids": [p.id for p in c.permissions],
    }


@router.get("")
async def list_companies(current: CurrentUser = Depends(require_admin)):
    """
    Superadmin → all companies.
    Admin      → only companies within their effective scope.
    """
    async with AsyncSession(engine) as db:
        rows = (await db.execute(select(Company))).scalars().all()
        for c in rows:
            await db.refresh(c, ["roles", "permissions"])

        if not current.is_superadmin:
            assert current.user is not None
            scope = await load_admin_scope(current.user, db)
            rows = [c for c in rows if c.id in scope]

    return JSONResponse([_serialise_company(c) for c in rows])


@router.post("", status_code=201)
async def create_company(
    body: CompanyIn,
    current: CurrentUser = Depends(require_admin),
):
    """
    Create a company.

    Rules:
      • parent_id=null (root node) → superadmin only.
        Roots start new independent company trees which only superadmin may own.
      • parent_id set → admin: the parent company must be within the caller's scope.
    """
    # Root company → superadmin only
    if body.parent_id is None and not current.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can create root (top-level) companies.",
        )

    async with AsyncSession(engine) as db:
        # Scope check for admins placing a child company
        if not current.is_superadmin and body.parent_id is not None:
            assert current.user is not None
            scope = await load_admin_scope(current.user, db)
            assert_within_scope([body.parent_id], scope, "parent_id")

        roles = list(
            (await db.execute(select(Role).where(Role.id.in_(body.role_ids)))).scalars().all()
        )
        perms = list(
            (await db.execute(select(Permission).where(Permission.id.in_(body.permission_ids))))
            .scalars().all()
        )
        c = Company(
            name=body.name,
            parent_id=body.parent_id,
            is_hierarchical=body.is_hierarchical,
            roles=roles,
            permissions=perms,
        )
        db.add(c)
        await db.flush()  # assigns c.id without committing

        # Inherit parent access: every user who has access to the parent company
        # is automatically granted the same role + permissions on the new child.
        if body.parent_id is not None:
            # Find all users assigned to the parent company
            parent_users = (
                await db.execute(
                    text("SELECT user_id FROM user_companies WHERE company_id = :pid"),
                    {"pid": body.parent_id},
                )
            ).fetchall()

            for (uid,) in parent_users:
                # Grant access to the new company
                await db.execute(
                    text(
                        "INSERT INTO user_companies (user_id, company_id) "
                        "VALUES (:uid, :cid) ON CONFLICT DO NOTHING"
                    ),
                    {"uid": uid, "cid": c.id},
                )

                # Copy the role the user has on the parent, if any
                parent_role = (
                    await db.execute(
                        text(
                            "SELECT role_id FROM user_company_roles "
                            "WHERE user_id = :uid AND company_id = :pid"
                        ),
                        {"uid": uid, "pid": body.parent_id},
                    )
                ).fetchone()
                if parent_role:
                    await db.execute(
                        text(
                            "INSERT INTO user_company_roles (user_id, company_id, role_id) "
                            "VALUES (:uid, :cid, :rid) ON CONFLICT DO NOTHING"
                        ),
                        {"uid": uid, "cid": c.id, "rid": parent_role[0]},
                    )

                # Copy all permissions the user has on the parent
                parent_perms = (
                    await db.execute(
                        text(
                            "SELECT permission_id FROM user_company_permissions "
                            "WHERE user_id = :uid AND company_id = :pid"
                        ),
                        {"uid": uid, "pid": body.parent_id},
                    )
                ).fetchall()
                for (pid,) in parent_perms:
                    await db.execute(
                        text(
                            "INSERT INTO user_company_permissions (user_id, company_id, permission_id) "
                            "VALUES (:uid, :cid, :pid) ON CONFLICT DO NOTHING"
                        ),
                        {"uid": uid, "cid": c.id, "pid": pid},
                    )

        await db.commit()
        await db.refresh(c)                          # reload expired scalars (name, parent_id, …)
        await db.refresh(c, ["roles", "permissions"])  # eagerly load relationships
        payload = _serialise_company(c)

    return JSONResponse(payload, status_code=201)


@router.patch("/{pk}")
async def patch_company(
    pk: int,
    body: CompanyPatch,
    current: CurrentUser = Depends(require_admin),
):
    """
    Update a company's single role and/or permission list (full replacement).
    The role list is capped at one entry; pass role_id=null to clear it.
    """
    async with AsyncSession(engine) as db:
        obj = await db.get(Company, pk)
        if obj is None:
            raise HTTPException(404)

        if not current.is_superadmin:
            assert current.user is not None
            scope = await load_admin_scope(current.user, db)
            if pk not in scope:
                raise HTTPException(403, detail="Company is outside your scope.")

        # Role — at most one
        if body.role_id is not None:
            role = await db.get(Role, body.role_id)
            if role is None:
                raise HTTPException(400, detail=f"Role {body.role_id} not found.")
            obj.roles = [role]
        else:
            obj.roles = []

        # Permissions — full replacement
        perms = list(
            (await db.execute(
                select(Permission).where(Permission.id.in_(body.permission_ids))
            )).scalars().all()
        )
        obj.permissions = perms

        await db.commit()
        await db.refresh(obj)                          # reload expired scalars
        await db.refresh(obj, ["roles", "permissions"])  # eagerly load relationships
        payload = _serialise_company(obj)

    return JSONResponse(payload)


@router.delete("/{pk}")
async def delete_company(
    pk: int,
    current: CurrentUser = Depends(require_admin),
):
    """
    Delete a company.
    Admin: the target company must be within their effective scope.
    Superadmin: unrestricted.
    """
    async with AsyncSession(engine) as db:
        obj = await db.get(Company, pk)
        if obj is None:
            raise HTTPException(404)

        if not current.is_superadmin:
            assert current.user is not None
            scope = await load_admin_scope(current.user, db)
            if pk not in scope:
                raise HTTPException(
                    status_code=403,
                    detail="Company is outside your scope.",
                )

        # Collect the entire subtree (this node + all descendants), deepest first.
        cte_result = await db.execute(
            text("""
                WITH RECURSIVE subtree AS (
                    SELECT id, 0 AS depth FROM companies WHERE id = :root
                    UNION ALL
                    SELECT c.id, s.depth + 1
                    FROM companies c
                    JOIN subtree s ON c.parent_id = s.id
                )
                SELECT id FROM subtree ORDER BY depth DESC
            """),
            {"root": pk},
        )
        subtree_ids: list[int] = [row[0] for row in cte_result.fetchall()]

        # 1. Remove all junction-table rows for every company in the subtree.
        for cid in subtree_ids:
            for tbl in (
                "user_company_roles",
                "user_company_permissions",
                "user_companies",
                "user_blocked_companies",
                "user_granular_blocked_companies",
                "company_roles",
                "company_permissions",
            ):
                await db.execute(
                    text(f"DELETE FROM {tbl} WHERE company_id = :cid"),
                    {"cid": cid},
                )

        # 2. Delete company rows deepest-first so the self-referential FK is respected.
        for cid in subtree_ids:
            await db.execute(
                text("DELETE FROM companies WHERE id = :cid"),
                {"cid": cid},
            )

        await db.commit()
    return JSONResponse({"detail": "deleted"})
