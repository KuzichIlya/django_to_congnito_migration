"""
Business-logic layer.

Responsibilities:
  - Company-scope computation  (effective access set for a user)
  - Scope enforcement          (assert requested IDs are within caller's scope)
  - User-info enrichment       (_load_user_info, used by /api/me)
  - User serialisation         (_serialise_user, shared by list/create endpoints)
"""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Company, User, engine


# ---------------------------------------------------------------------------
# Company scope helpers
# ---------------------------------------------------------------------------

def _get_descendants(company_id: int, all_companies: list[Company]) -> set[int]:
    """Recursively collect all descendant company IDs for a given parent."""
    result: set[int] = set()
    for c in all_companies:
        if c.parent_id == company_id:
            result.add(c.id)
            result |= _get_descendants(c.id, all_companies)
    return result


def compute_effective_company_ids(user: User, all_companies: list[Company]) -> set[int]:
    """
    Compute the set of company IDs the user can effectively access:

        (assigned + all descendants)
        − blocked companies (and their descendants)
    """
    effective: set[int] = set()

    for c in user.companies:
        effective.add(c.id)
        effective |= _get_descendants(c.id, all_companies)

    for c in user.blocked_companies:
        effective.discard(c.id)
        effective -= _get_descendants(c.id, all_companies)

    return effective


def assert_within_scope(
    requested_ids: list[int],
    scope: set[int],
    field: str = "company_ids",
) -> None:
    """Raise HTTP 403 if any of the requested IDs fall outside the caller's scope."""
    out_of_scope = set(requested_ids) - scope
    if out_of_scope:
        raise HTTPException(
            status_code=403,
            detail=f"Company IDs {sorted(out_of_scope)} are outside your scope ({field})",
        )


async def load_admin_scope(user: User, db: AsyncSession) -> set[int]:
    """
    Load all companies from DB and compute the effective scope for *user*.

    Re-fetches the user from *db* with selectinload so that the relationship
    attributes are always bound to the *current* session — avoiding
    DetachedInstanceError when *user* was originally loaded in a different
    session (e.g. inside get_current_user).
    """
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.companies),
            selectinload(User.blocked_companies),
        )
    )
    fresh_user = result.scalar_one_or_none()
    if fresh_user is None:
        return set()
    all_companies = list((await db.execute(select(Company))).scalars().all())
    return compute_effective_company_ids(fresh_user, all_companies)


# ---------------------------------------------------------------------------
# User info enrichment  (for /api/me)
# ---------------------------------------------------------------------------

async def load_user_info(sub: str) -> dict[str, Any] | None:
    """
    Look up a user by ``cognito_sub``, then build the full enriched info dict
    used by ``GET /api/me``.

    Returns ``None`` if no local record is found for *sub*.
    """
    async with AsyncSession(engine) as db:
        result = await db.execute(select(User).where(User.cognito_sub == sub))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        await db.refresh(user, ["companies", "blocked_companies"])

        # Per-company role + permission assignments
        per_company_roles = (await db.execute(
            text(
                "SELECT ucr.company_id, r.name "
                "FROM user_company_roles ucr "
                "JOIN roles r ON r.id = ucr.role_id "
                "WHERE ucr.user_id = :uid"
            ),
            {"uid": user.id},
        )).fetchall()
        per_company_perms = (await db.execute(
            text(
                "SELECT ucp.company_id, p.name "
                "FROM user_company_permissions ucp "
                "JOIN permissions p ON p.id = ucp.permission_id "
                "WHERE ucp.user_id = :uid"
            ),
            {"uid": user.id},
        )).fetchall()

        # Build {company_id: {role_name, permission_names}}
        company_detail: dict[int, dict] = {}
        for cid, rname in per_company_roles:
            company_detail.setdefault(cid, {"role": None, "permissions": []})["role"] = rname
        for cid, pname in per_company_perms:
            company_detail.setdefault(cid, {"role": None, "permissions": []})["permissions"].append(pname)

        # Build enriched company list with breadcrumb chain + role/permissions
        companies_out: list[dict] = []
        for company in user.companies:
            chain: list[dict[str, Any]] = []
            cur: Company | None = company
            while cur is not None:
                chain.append({"id": cur.id, "name": cur.name})
                if cur.parent_id is None:
                    break
                cur = await db.get(Company, cur.parent_id)
            chain.reverse()
            detail = company_detail.get(company.id, {"role": None, "permissions": []})
            companies_out.append({
                "id": company.id,
                "name": company.name,
                "chain": chain,
                "role": detail["role"],
                "permissions": detail["permissions"],
            })

        return {
            "user_id": user.id,
            "is_admin": user.is_admin,
            "is_superadmin": user.is_superadmin,
            "companies": companies_out,
            "blocked_companies": [
                {"id": c.id, "name": c.name} for c in user.blocked_companies
            ],
            "notes": user.notes,
        }


# ---------------------------------------------------------------------------
# Per-company assignment fetcher  (batch, for list + create endpoints)
# ---------------------------------------------------------------------------

async def fetch_company_assignments(
    user_ids: list[int],
    db: AsyncSession,
) -> dict[int, dict[int, dict[str, Any]]]:
    """
    Return per-user, per-company role + permission assignments.

    Shape:
        { user_id: { company_id: { role_id, permission_ids, minus_permission_ids } } }
    """
    if not user_ids:
        return {}

    result: dict[int, dict[int, dict[str, Any]]] = {}

    # Roles
    rows = await db.execute(
        text("SELECT user_id, company_id, role_id FROM user_company_roles WHERE user_id = ANY(:ids)"),
        {"ids": user_ids},
    )
    for row in rows:
        result.setdefault(row.user_id, {}).setdefault(
            row.company_id, {"role_id": None, "permission_ids": []}
        )["role_id"] = row.role_id

    # Permissions
    rows = await db.execute(
        text("SELECT user_id, company_id, permission_id FROM user_company_permissions WHERE user_id = ANY(:ids)"),
        {"ids": user_ids},
    )
    for row in rows:
        d = result.setdefault(row.user_id, {}).setdefault(
            row.company_id, {"role_id": None, "permission_ids": []}
        )
        d["permission_ids"].append(row.permission_id)

    return result


# ---------------------------------------------------------------------------
# User serialisation  (shared by list + create endpoints)
# ---------------------------------------------------------------------------

def serialise_user(
    u: User,
    per_company: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Convert a fully-loaded User ORM object to a JSON-safe dict.

    ``per_company`` maps company_id → {role_id, permission_ids, minus_permission_ids}
    as returned by ``fetch_company_assignments``.
    """
    per_company = per_company or {}
    company_assignments = []
    for c in u.companies:
        asgn = per_company.get(c.id, {})
        company_assignments.append({
            "company_id": c.id,
            "company_name": c.name,
            "role_id": asgn.get("role_id"),
            "permission_ids": asgn.get("permission_ids", []),
        })

    return {
        "id": u.id,
        "cognito_sub": u.cognito_sub,
        "username": u.username,
        "name": u.name,
        "is_admin": u.is_admin,
        "is_superadmin": u.is_superadmin,
        "notes": u.notes,
        # Structured per-company access
        "company_assignments": company_assignments,
        # Kept for backward compat (used by JS to filter/match)
        "company_ids": [c.id for c in u.companies],
        "company_names": [c.name for c in u.companies],
        "blocked_company_ids": [c.id for c in u.blocked_companies],
        "blocked_company_names": [c.name for c in u.blocked_companies],
        "minus_right_ids": [p.id for p in u.minus_rights],
    }
