"""SQLAlchemy database engine, ORM models, and startup lifespan migrations."""

import logging
from contextlib import asynccontextmanager

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(settings.database_url, echo=False)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# M2M association tables
# ---------------------------------------------------------------------------
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

company_roles = Table(
    "company_roles",
    Base.metadata,
    Column("company_id", Integer, ForeignKey("companies.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

company_permissions = Table(
    "company_permissions",
    Base.metadata,
    Column("company_id", Integer, ForeignKey("companies.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

user_add_rights = Table(
    "user_add_rights",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

user_minus_rights = Table(
    "user_minus_rights",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

user_companies = Table(
    "user_companies",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("company_id", Integer, ForeignKey("companies.id"), primary_key=True),
)

user_blocked_companies = Table(
    "user_blocked_companies",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("company_id", Integer, ForeignKey("companies.id"), primary_key=True),
)

user_granular_blocked_companies = Table(
    "user_granular_blocked_companies",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("company_id", Integer, ForeignKey("companies.id"), primary_key=True),
)


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------
class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[Permission]] = relationship(
        "Permission", secondary=role_permissions
    )


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=True
    )
    is_hierarchical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    parent: Mapped["Company | None"] = relationship(
        "Company", remote_side=[id], foreign_keys=[parent_id]
    )
    children: Mapped[list["Company"]] = relationship("Company", foreign_keys=[parent_id])
    roles: Mapped[list[Role]] = relationship("Role", secondary=company_roles)
    permissions: Mapped[list[Permission]] = relationship(
        "Permission", secondary=company_permissions
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # cognito_sub: links this local record to the Cognito user identity (sub claim)
    cognito_sub: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    companies: Mapped[list[Company]] = relationship("Company", secondary=user_companies)
    blocked_companies: Mapped[list[Company]] = relationship(
        "Company", secondary=user_blocked_companies
    )
    granular_blocked_companies: Mapped[list[Company]] = relationship(
        "Company", secondary=user_granular_blocked_companies
    )
    role: Mapped[Role | None] = relationship("Role")
    add_rights: Mapped[list[Permission]] = relationship(
        "Permission", secondary=user_add_rights
    )
    minus_rights: Mapped[list[Permission]] = relationship(
        "Permission", secondary=user_minus_rights
    )


# ---------------------------------------------------------------------------
# Company seed data
# ---------------------------------------------------------------------------
_COMPANY_TREES = [
    {
        "global": "Google Global",
        "continents": {
            "Google Americas": [
                "Google USA", "Google Canada", "Google Brazil",
                "Google Mexico", "Google Argentina",
            ],
            "Google Europe": [
                "Google Germany", "Google France", "Google United Kingdom",
                "Google Netherlands", "Google Spain",
            ],
            "Google Asia Pacific": [
                "Google Japan", "Google India", "Google Australia",
                "Google Singapore", "Google South Korea",
            ],
        },
    },
    {
        "global": "Amazon Global",
        "continents": {
            "Amazon Americas": [
                "Amazon USA", "Amazon Canada", "Amazon Brazil",
                "Amazon Mexico", "Amazon Colombia",
            ],
            "Amazon Europe": [
                "Amazon Germany", "Amazon France", "Amazon United Kingdom",
                "Amazon Italy", "Amazon Poland",
            ],
            "Amazon Asia Pacific": [
                "Amazon Japan", "Amazon India", "Amazon Australia",
                "Amazon Singapore", "Amazon Indonesia",
            ],
        },
    },
    {
        "global": "Azure Global",
        "continents": {
            "Azure Americas": [
                "Azure USA", "Azure Canada", "Azure Brazil",
                "Azure Mexico", "Azure Chile",
            ],
            "Azure Europe": [
                "Azure Germany", "Azure France", "Azure United Kingdom",
                "Azure Netherlands", "Azure Sweden",
            ],
            "Azure Asia Pacific": [
                "Azure Japan", "Azure India", "Azure Australia",
                "Azure Singapore", "Azure South Korea",
            ],
        },
    },
    {
        "global": "Test Company Global",
        "continents": {
            "Test Company Americas": [
                "Test Company USA", "Test Company Canada", "Test Company Brazil",
            ],
            "Test Company Europe": [
                "Test Company Germany", "Test Company France",
                "Test Company United Kingdom", "Test Company Sweden",
            ],
            "Test Company Asia Pacific": [
                "Test Company Japan", "Test Company India",
                "Test Company Australia", "Test Company Singapore",
            ],
        },
    },
]


async def _seed_companies(db: AsyncSession) -> None:
    """Insert the example company trees if they don't already exist."""
    for tree in _COMPANY_TREES:
        # Level 1 — Global root
        res = await db.execute(select(Company).where(Company.name == tree["global"]))
        global_co = res.scalar_one_or_none()
        if global_co is None:
            global_co = Company(name=tree["global"], parent_id=None, is_hierarchical=True)
            db.add(global_co)
            await db.flush()
            logger.info("Seeded: %s", tree["global"])

        for continent_name, countries in tree["continents"].items():
            # Level 2 — Continent
            res = await db.execute(select(Company).where(Company.name == continent_name))
            cont_co = res.scalar_one_or_none()
            if cont_co is None:
                cont_co = Company(
                    name=continent_name, parent_id=global_co.id, is_hierarchical=True
                )
                db.add(cont_co)
                await db.flush()
                logger.info("  Seeded: %s", continent_name)

            for country_name in countries:
                # Level 3 — Country
                res = await db.execute(select(Company).where(Company.name == country_name))
                if res.scalar_one_or_none() is None:
                    db.add(Company(
                        name=country_name, parent_id=cont_co.id, is_hierarchical=True
                    ))
                    logger.info("    Seeded: %s", country_name)


# ---------------------------------------------------------------------------
# Predefined permissions & role seed
# ---------------------------------------------------------------------------
_SEED_PERMISSIONS = ["read", "edit", "delete"]

# name → list of permission names included in the role
# Admin grants user-management access (via is_admin flag) but no data permissions by default.
# Additional data permissions (read/edit/delete) can be granted explicitly per company.
_SEED_ROLES: dict[str, list[str]] = {
    "Admin":  [],                        # user management only; no data perms by default
    "Owner":  ["read", "edit", "delete"],
    "Editor": ["read", "edit"],
    "Reader": ["read"],
}


async def _seed_permissions_and_roles(db: AsyncSession) -> None:
    """Idempotently seed the predefined permissions and roles."""
    for pname in _SEED_PERMISSIONS:
        res = await db.execute(select(Permission).where(Permission.name == pname))
        if res.scalar_one_or_none() is None:
            db.add(Permission(name=pname))
            logger.info("Seeded permission: %s", pname)

    await db.flush()  # ensure permissions get IDs before role references them

    for role_name, perm_names in _SEED_ROLES.items():
        res = await db.execute(select(Role).where(Role.name == role_name))
        if res.scalar_one_or_none() is None:
            perms = list(
                (await db.execute(select(Permission).where(Permission.name.in_(perm_names))))
                .scalars().all()
            )
            db.add(Role(name=role_name, permissions=perms))
            logger.info("Seeded role: %s (permissions: %s)", role_name, ", ".join(perm_names))


# ---------------------------------------------------------------------------
# Superadmin seed
# ---------------------------------------------------------------------------
_SUPERADMIN_SUB      = "549884c8-50d1-70a6-e221-ee7b4d710ce8"
_SUPERADMIN_USERNAME = "superadmin@example.com"


# ---------------------------------------------------------------------------
# Default demo users seed
# ---------------------------------------------------------------------------
_DEFAULT_USERS = [
    {
        "cognito_sub": "f4e8d418-e071-7032-1266-1fdaf0ee8fe3",
        "username":    "user1@example.com",
        "name":        "User One",
        "companies":   ["Google Global"],
    },
    {
        "cognito_sub": "c4b8b488-a061-707b-9be0-3b4f3d7656c0",
        "username":    "user2@example.com",
        "name":        "User Two",
        "companies":   ["Azure Americas"],
    },
    {
        "cognito_sub": "744804c8-50e1-70ea-849e-d939c5519d8c",
        "username":    "user3@example.com",
        "name":        "User Three",
        "companies":   ["Azure Europe", "Amazon Asia Pacific"],
    },
]


async def _seed_default_users(db: AsyncSession) -> None:
    """Idempotently seed the three default demo users with company assignments."""
    # Use the Editor role (read + edit) for default users
    editor_role  = (await db.execute(select(Role).where(Role.name == "Editor"))).scalar_one_or_none()
    editor_perms = list(
        (await db.execute(
            select(Permission).where(Permission.name.in_(["read", "edit"]))
        )).scalars().all()
    )

    async def get_all_descendant_ids(root_id: int) -> list[int]:
        """Return root_id plus all descendant company ids via recursive CTE."""
        cte_result = await db.execute(text("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM companies WHERE id = :root_id
                UNION ALL
                SELECT c.id FROM companies c
                JOIN descendants d ON c.parent_id = d.id
            )
            SELECT id FROM descendants
        """), {"root_id": root_id})
        return [row[0] for row in cte_result.fetchall()]

    for spec in _DEFAULT_USERS:
        # Skip if user already exists
        existing = (
            await db.execute(select(User).where(User.cognito_sub == spec["cognito_sub"]))
        ).scalar_one_or_none()
        if existing is not None:
            continue

        user = User(
            cognito_sub=spec["cognito_sub"],
            username=spec["username"],
            name=spec["name"],
            is_admin=False,
            is_superadmin=False,
            notes="Seeded default demo user.",
        )
        db.add(user)
        await db.flush()  # get user.id

        for company_name in spec["companies"]:
            root_company = (
                await db.execute(select(Company).where(Company.name == company_name))
            ).scalar_one_or_none()
            if root_company is None:
                logger.warning("Default user seed: company '%s' not found — skipping", company_name)
                continue

            # Propagate to root + all descendants
            target_ids = await get_all_descendant_ids(root_company.id)
            logger.info(
                "Default user seed: '%s' -> '%s' (id=%d): found %d company nodes to assign",
                spec["username"], company_name, root_company.id, len(target_ids),
            )
            for cid in target_ids:
                # Grant access
                await db.execute(text(
                    "INSERT INTO user_companies (user_id, company_id) "
                    "VALUES (:uid, :cid) ON CONFLICT DO NOTHING"
                ), {"uid": user.id, "cid": cid})

                # Assign Editor role
                if editor_role:
                    await db.execute(text(
                        "INSERT INTO user_company_roles (user_id, company_id, role_id) "
                        "VALUES (:uid, :cid, :rid) ON CONFLICT DO NOTHING"
                    ), {"uid": user.id, "cid": cid, "rid": editor_role.id})

                # Grant read + edit permissions
                for perm in editor_perms:
                    await db.execute(text(
                        "INSERT INTO user_company_permissions (user_id, company_id, permission_id) "
                        "VALUES (:uid, :cid, :pid) ON CONFLICT DO NOTHING"
                    ), {"uid": user.id, "cid": cid, "pid": perm.id})

            logger.info(
                "Default user seed: '%s' → '%s' + %d descendants (Editor)",
                spec["username"], company_name, len(target_ids) - 1,
            )

        logger.info("Seeded default user: %s", spec["username"])


async def _seed_superadmin(db: AsyncSession) -> None:
    """Ensure the designated superadmin user exists in the local DB."""
    res = await db.execute(select(User).where(User.cognito_sub == _SUPERADMIN_SUB))
    if res.scalar_one_or_none() is not None:
        return  # already exists

    superadmin = User(
        cognito_sub=_SUPERADMIN_SUB,
        username=_SUPERADMIN_USERNAME,
        name="Superadmin",
        is_admin=True,
        is_superadmin=True,
        notes="System superadmin — seeded on startup.",
    )
    db.add(superadmin)
    logger.info("Seeded superadmin user: %s (%s)", _SUPERADMIN_USERNAME, _SUPERADMIN_SUB)


# ---------------------------------------------------------------------------
# Lifespan — schema creation + idempotent column migrations + seed data
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app):  # type: ignore[no-untyped-def]
    async with engine.begin() as conn:
        # Create any tables that do not yet exist (idempotent for fresh installs)
        await conn.run_sync(Base.metadata.create_all)

        # cognito_sub column + unique partial index
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cognito_sub VARCHAR(200)"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_cognito_sub "
            "ON users (cognito_sub) WHERE cognito_sub IS NOT NULL"
        ))

        # Migrate data from legacy authentik_sub column (if still present)
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='authentik_sub'"
        ))
        if result.fetchone() is not None:
            await conn.execute(text(
                "UPDATE users SET cognito_sub = authentik_sub "
                "WHERE cognito_sub IS NULL AND authentik_sub IS NOT NULL"
            ))
            logger.info("Migrated authentik_sub → cognito_sub for existing rows")

        # username / name columns (backward compat)
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(200)"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(200)"
        ))

        # Admin flags
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "is_admin BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "is_superadmin BOOLEAN NOT NULL DEFAULT FALSE"
        ))

        # Per-user-per-company role assignment (one role per company per user)
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS user_company_roles ("
            "  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,"
            "  company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,"
            "  role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL,"
            "  PRIMARY KEY (user_id, company_id)"
            ")"
        ))

        # Per-user-per-company permission grants (the '+' list)
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS user_company_permissions ("
            "  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,"
            "  company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,"
            "  permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,"
            "  PRIMARY KEY (user_id, company_id, permission_id)"
            ")"
        ))

        # Per-user-per-company permission denials (the '−' list)
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS user_company_minus_permissions ("
            "  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,"
            "  company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,"
            "  permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,"
            "  PRIMARY KEY (user_id, company_id, permission_id)"
            ")"
        ))

        # Legacy single company_id → many-to-many migration
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='company_id'"
        ))
        if result.fetchone() is not None:
            await conn.execute(text(
                "INSERT INTO user_companies (user_id, company_id) "
                "SELECT id, company_id FROM users WHERE company_id IS NOT NULL "
                "ON CONFLICT DO NOTHING"
            ))
            await conn.execute(text("ALTER TABLE users DROP COLUMN company_id"))

    # Seed predefined permissions and roles
    async with AsyncSession(engine) as db:
        async with db.begin():
            await _seed_permissions_and_roles(db)

    # Seed example company trees (idempotent — skips existing names)
    async with AsyncSession(engine) as db:
        async with db.begin():
            await _seed_companies(db)

    # Seed the designated superadmin user (idempotent)
    async with AsyncSession(engine) as db:
        async with db.begin():
            await _seed_superadmin(db)

    # Seed default demo users (idempotent)
    async with AsyncSession(engine) as db:
        async with db.begin():
            await _seed_default_users(db)
    yield
