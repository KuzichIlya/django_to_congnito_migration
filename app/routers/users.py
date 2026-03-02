"""API routes for User CRUD and the /api/me profile endpoint.

  GET    /api/me             — any authenticated user (own profile)
  GET    /api/users          — admin+  (scope-filtered)
  POST   /api/users          — admin+  (scope-enforced)
  DELETE /api/users/{pk}    — admin+  (privilege-guarded)
  POST   /api/access-check  — admin+  (try user access)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import CurrentUser, get_current_user, require_admin
from models import Company, Permission, User, engine
from pydantic import BaseModel

from schemas import UserIn
from services import (
    assert_within_scope,
    compute_effective_company_ids,
    load_admin_scope,
    load_user_info,
    serialise_user,
    fetch_company_assignments,
)

router = APIRouter(tags=["users"])


# ---------------------------------------------------------------------------
# /api/me — own profile (any authenticated user)
# ---------------------------------------------------------------------------

@router.get("/api/me")
async def me(current: CurrentUser = Depends(get_current_user)):
    """Return the caller's JWT claims plus enriched local user info."""
    return JSONResponse({
        "sub": current.sub,
        "username": current.username,
        "name": current.claims.get("name"),
        "email": current.claims.get("email"),
        "user_info": await load_user_info(current.sub),
    })


# ---------------------------------------------------------------------------
# /api/users — list (admin+)
# ---------------------------------------------------------------------------

@router.get("/api/users")
async def list_users(current: CurrentUser = Depends(require_admin)):
    """
    List users visible to the caller:
      - superadmin → all users
      - admin      → users who share at least one company with the caller's scope
    """
    async with AsyncSession(engine) as db:
        rows = list((await db.execute(select(User))).scalars().all())
        for u in rows:
            await db.refresh(u, [
                "companies", "blocked_companies",
                "role", "add_rights", "minus_rights",
            ])

        if not current.is_superadmin:
            assert current.user is not None
            # load_admin_scope re-fetches the caller fresh with selectinload,
            # avoiding the InvalidRequestError on detached instances.
            scope = await load_admin_scope(current.user, db)
            rows = [u for u in rows if any(c.id in scope for c in u.companies)]

        # Batch-fetch per-company assignments for all visible users
        user_ids = [u.id for u in rows]
        all_assignments = await fetch_company_assignments(user_ids, db)

    return JSONResponse([
        serialise_user(u, all_assignments.get(u.id, {}))
        for u in rows
    ])


# ---------------------------------------------------------------------------
# /api/users — create (admin+)
# ---------------------------------------------------------------------------

@router.post("/api/users", status_code=201)
async def create_user(
    body: UserIn,
    current: CurrentUser = Depends(require_admin),
):
    """
    Create a local user record linked to an existing Cognito identity via ``sub``.

    Scope enforcement:
      - superadmin: may assign any company.
      - admin:      all requested company_ids must be within caller's own scope.

    Escalation guards (superadmin only):
      - ``is_admin``      — promoting a user to admin.
      - ``is_superadmin`` — promoting a user to superadmin.
    """
    if body.is_admin and not current.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can grant admin privileges",
        )
    if body.is_superadmin and not current.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can grant superadmin privileges",
        )

    company_ids = [a.company_id for a in body.company_assignments]

    async with AsyncSession(engine) as db:
        if not current.is_superadmin:
            assert current.user is not None
            scope = await load_admin_scope(current.user, db)
            assert_within_scope(company_ids, scope, "company_ids")
            assert_within_scope(body.blocked_company_ids, scope, "blocked_company_ids")

        minus_perms = list(
            (await db.execute(select(Permission).where(Permission.id.in_(body.minus_right_ids))))
            .scalars().all()
        )
        companies = list(
            (await db.execute(select(Company).where(Company.id.in_(company_ids))))
            .scalars().all()
        )
        blocked_companies = list(
            (await db.execute(select(Company).where(Company.id.in_(body.blocked_company_ids))))
            .scalars().all()
        )

        u = User(
            cognito_sub=body.cognito_sub,
            notes=body.notes,
            username=body.username,
            name=body.name,
            is_admin=body.is_admin,
            is_superadmin=body.is_superadmin,
            companies=companies,
            blocked_companies=blocked_companies,
            minus_rights=minus_perms,
        )
        db.add(u)
        await db.flush()  # get u.id before raw inserts

        # Write per-company role + permission assignments
        for asgn in body.company_assignments:
            if asgn.role_id is not None:
                await db.execute(text(
                    "INSERT INTO user_company_roles (user_id, company_id, role_id) "
                    "VALUES (:uid, :cid, :rid) "
                    "ON CONFLICT (user_id, company_id) DO UPDATE SET role_id = :rid"
                ), {"uid": u.id, "cid": asgn.company_id, "rid": asgn.role_id})

            for pid in asgn.permission_ids:
                await db.execute(text(
                    "INSERT INTO user_company_permissions (user_id, company_id, permission_id) "
                    "VALUES (:uid, :cid, :pid) ON CONFLICT DO NOTHING"
                ), {"uid": u.id, "cid": asgn.company_id, "pid": pid})


        await db.commit()
        await db.refresh(u)  # reload expired scalar columns (id, username, …)
        await db.refresh(u, [
            "companies", "blocked_companies",
            "role", "add_rights", "minus_rights",
        ])
        # Fetch per-company assignments while session is open
        per_company = await fetch_company_assignments([u.id], db)
        payload = serialise_user(u, per_company.get(u.id, {}))

    return JSONResponse(payload, status_code=201)


# ---------------------------------------------------------------------------
# /api/users/{pk} — update (admin+)
# ---------------------------------------------------------------------------

@router.put("/api/users/{pk}", status_code=200)
async def update_user(
    pk: int,
    body: UserIn,
    current: CurrentUser = Depends(require_admin),
):
    """
    Update an existing local user record.

    Applies the same scope and escalation guards as create_user.
    Per-company role/permission assignments are fully replaced.
    """
    if body.is_admin and not current.is_superadmin:
        raise HTTPException(403, detail="Only superadmin can grant admin privileges")
    if body.is_superadmin and not current.is_superadmin:
        raise HTTPException(403, detail="Only superadmin can grant superadmin privileges")

    company_ids = [a.company_id for a in body.company_assignments]

    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(User)
            .where(User.id == pk)
            .options(
                selectinload(User.companies),
                selectinload(User.blocked_companies),
                selectinload(User.minus_rights),
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise HTTPException(404)

        if not current.is_superadmin:
            if obj.is_superadmin:
                raise HTTPException(403, detail="Admins cannot edit superadmin users")
            if obj.is_admin and current.user and current.user.id != pk:
                raise HTTPException(403, detail="Admins cannot edit other admin users")
            scope = await load_admin_scope(current.user, db)
            assert_within_scope(company_ids, scope, "company_ids")
            assert_within_scope(body.blocked_company_ids, scope, "blocked_company_ids")

        # Update scalar fields
        obj.cognito_sub = body.cognito_sub
        obj.username = body.username
        obj.name = body.name
        obj.is_admin = body.is_admin
        obj.is_superadmin = body.is_superadmin
        obj.notes = body.notes

        # Update relationship collections
        minus_perms = list(
            (await db.execute(select(Permission).where(Permission.id.in_(body.minus_right_ids))))
            .scalars().all()
        )
        companies = list(
            (await db.execute(select(Company).where(Company.id.in_(company_ids))))
            .scalars().all()
        )
        blocked_companies = list(
            (await db.execute(select(Company).where(Company.id.in_(body.blocked_company_ids))))
            .scalars().all()
        )
        obj.companies = companies
        obj.blocked_companies = blocked_companies
        obj.minus_rights = minus_perms

        await db.flush()

        # Clear + rewrite per-company role/permission assignments
        await db.execute(
            text("DELETE FROM user_company_roles WHERE user_id = :uid"), {"uid": pk}
        )
        await db.execute(
            text("DELETE FROM user_company_permissions WHERE user_id = :uid"), {"uid": pk}
        )
        for asgn in body.company_assignments:
            if asgn.role_id is not None:
                await db.execute(text(
                    "INSERT INTO user_company_roles (user_id, company_id, role_id) "
                    "VALUES (:uid, :cid, :rid) "
                    "ON CONFLICT (user_id, company_id) DO UPDATE SET role_id = :rid"
                ), {"uid": pk, "cid": asgn.company_id, "rid": asgn.role_id})
            for pid in asgn.permission_ids:
                await db.execute(text(
                    "INSERT INTO user_company_permissions (user_id, company_id, permission_id) "
                    "VALUES (:uid, :cid, :pid) ON CONFLICT DO NOTHING"
                ), {"uid": pk, "cid": asgn.company_id, "pid": pid})

        await db.commit()
        await db.refresh(obj)
        await db.refresh(obj, [
            "companies", "blocked_companies",
            "role", "add_rights", "minus_rights",
        ])
        per_company = await fetch_company_assignments([obj.id], db)
        payload = serialise_user(obj, per_company.get(obj.id, {}))

    return JSONResponse(payload)


# ---------------------------------------------------------------------------
# /api/users/{pk} — delete (admin+)
# ---------------------------------------------------------------------------

@router.delete("/api/users/{pk}")
async def delete_user(
    pk: int,
    current: CurrentUser = Depends(require_admin),
):
    """
    Delete a local user record (Cognito identity is NOT touched).

    Guards:
      - Admins cannot delete superadmin or peer admin records.
      - Superadmins may delete any record.
    """
    async with AsyncSession(engine) as db:
        obj = await db.get(User, pk)
        if obj is None:
            raise HTTPException(404)

        if not current.is_superadmin:
            if obj.is_superadmin:
                raise HTTPException(
                    status_code=403, detail="Admins cannot delete superadmin users"
                )
            if obj.is_admin:
                raise HTTPException(
                    status_code=403, detail="Admins cannot delete other admin users"
                )

        await db.delete(obj)
        await db.commit()
    return JSONResponse({"detail": "deleted"})


# ---------------------------------------------------------------------------
# /api/access-check — try a user's access  (admin+)
# ---------------------------------------------------------------------------

_OP_TO_PERM: dict[str, str] = {
    "get":    "read",
    "update": "edit",
    "create": "edit",
    "delete": "delete",
}


class AccessCheckIn(BaseModel):
    username: str          # username or email of the target user
    company_name: str      # exact company name
    operation: str         # get | update | create | delete


@router.post("/api/access-check")
async def access_check(
    body: AccessCheckIn,
    current: CurrentUser = Depends(require_admin),
):
    """
    Simulate whether a given user can perform an operation on a company.

    Operation → required permission:
      get    → read
      update → edit
      create → edit
      delete → delete
    """
    op = body.operation.lower()
    required_perm = _OP_TO_PERM.get(op)
    if required_perm is None:
        raise HTTPException(400, detail=f"Unknown operation '{body.operation}'. Use: get, update, create, delete")

    async with AsyncSession(engine) as db:
        # ── 1. Resolve user ────────────────────────────────────────────────
        result = await db.execute(
            select(User)
            .where(User.username == body.username)
            .options(
                selectinload(User.companies),
                selectinload(User.blocked_companies),
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(404, detail=f"User '{body.username}' not found")

        # ── 2. Resolve company ─────────────────────────────────────────────
        comp_result = await db.execute(
            select(Company).where(Company.name == body.company_name)
        )
        company = comp_result.scalar_one_or_none()
        if company is None:
            raise HTTPException(404, detail=f"Company '{body.company_name}' not found")

        # ── 3. Effective scope check ───────────────────────────────────────
        all_companies = list((await db.execute(select(Company))).scalars().all())
        effective_ids = compute_effective_company_ids(user, all_companies)

        if company.id not in effective_ids:
            # Determine a more specific reason
            assigned_ids = {c.id for c in user.companies}
            if not assigned_ids:
                reason = "User is not assigned to any company"
            else:
                # Check if the company is a descendant of an assigned one
                ancestors = set()
                cur: Company | None = company
                while cur and cur.parent_id:
                    cur = await db.get(Company, cur.parent_id)
                    if cur:
                        ancestors.add(cur.id)
                if not ancestors & assigned_ids:
                    reason = f"Company '{company.name}' is not within user's assigned scope"
                else:
                    reason = f"Company '{company.name}' is blocked for this user"
            return JSONResponse({
                "allowed": False,
                "reason": reason,
                "user": user.username,
                "company": company.name,
                "operation": op,
                "required_permission": required_perm,
                "user_permissions": [],
            })

        # ── 4. Find the covering assignment (direct or ancestor) ───────────
        assigned_ids = {c.id for c in user.companies}
        covering_company: Company | None = None
        cur = company
        visited: set[int] = set()
        while cur is not None and cur.id not in visited:
            visited.add(cur.id)
            if cur.id in assigned_ids:
                covering_company = cur
                break
            if cur.parent_id is None:
                break
            cur = await db.get(Company, cur.parent_id)

        if covering_company is None:
            return JSONResponse({
                "allowed": False,
                "reason": "Could not locate the direct company assignment covering this company",
                "user": user.username,
                "company": company.name,
                "operation": op,
                "required_permission": required_perm,
                "user_permissions": [],
            })

        # ── 5. Permission check ────────────────────────────────────────────
        perm_rows = (await db.execute(
            text(
                "SELECT p.name "
                "FROM user_company_permissions ucp "
                "JOIN permissions p ON p.id = ucp.permission_id "
                "WHERE ucp.user_id = :uid AND ucp.company_id = :cid"
            ),
            {"uid": user.id, "cid": covering_company.id},
        )).fetchall()
        user_perms = sorted({row[0] for row in perm_rows})

        has_perm = required_perm in user_perms

        via = (
            f" (via direct assignment)"
            if covering_company.id == company.id
            else f" (via ancestor '{covering_company.name}')"
        )

        return JSONResponse({
            "allowed": has_perm,
            "reason": (
                f"User has '{required_perm}' permission{via}"
                if has_perm
                else f"User lacks '{required_perm}' permission{via}. "
                     f"Granted: {', '.join(user_perms) if user_perms else 'none'}"
            ),
            "user": user.username,
            "company": company.name,
            "covering_company": covering_company.name,
            "operation": op,
            "required_permission": required_perm,
            "user_permissions": user_perms,
        })
