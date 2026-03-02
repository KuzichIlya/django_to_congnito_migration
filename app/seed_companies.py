"""
Seed script — inserts four hierarchical company trees:
  • Google  Global → Continents → Countries
  • Amazon  Global → Continents → Countries
  • Azure   Global → Continents → Countries
  • Test Co Global → Continents → Countries

NOTE: The FastAPI app now seeds these automatically on startup via the
lifespan hook in models.py.  This script is kept as a standalone utility
for manual re-seeding or local testing without running the full server.

Run from the project root (after the DB is up):
  python seed_companies.py

Idempotent: skips companies whose name already exists.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings  # noqa: F401 — triggers .env load
from models import Company, engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tree definitions
# ---------------------------------------------------------------------------
TREES = [
    {
        "global": "Google Global",
        "continents": {
            "Google Americas": [
                "Google USA",
                "Google Canada",
                "Google Brazil",
                "Google Mexico",
                "Google Argentina",
            ],
            "Google Europe": [
                "Google Germany",
                "Google France",
                "Google United Kingdom",
                "Google Netherlands",
                "Google Spain",
            ],
            "Google Asia Pacific": [
                "Google Japan",
                "Google India",
                "Google Australia",
                "Google Singapore",
                "Google South Korea",
            ],
        },
    },
    {
        "global": "Amazon Global",
        "continents": {
            "Amazon Americas": [
                "Amazon USA",
                "Amazon Canada",
                "Amazon Brazil",
                "Amazon Mexico",
                "Amazon Colombia",
            ],
            "Amazon Europe": [
                "Amazon Germany",
                "Amazon France",
                "Amazon United Kingdom",
                "Amazon Italy",
                "Amazon Poland",
            ],
            "Amazon Asia Pacific": [
                "Amazon Japan",
                "Amazon India",
                "Amazon Australia",
                "Amazon Singapore",
                "Amazon Indonesia",
            ],
        },
    },
    {
        "global": "Azure Global",
        "continents": {
            "Azure Americas": [
                "Azure USA",
                "Azure Canada",
                "Azure Brazil",
                "Azure Mexico",
                "Azure Chile",
            ],
            "Azure Europe": [
                "Azure Germany",
                "Azure France",
                "Azure United Kingdom",
                "Azure Netherlands",
                "Azure Sweden",
            ],
            "Azure Asia Pacific": [
                "Azure Japan",
                "Azure India",
                "Azure Australia",
                "Azure Singapore",
                "Azure South Korea",
            ],
        },
    },
    {
        "global": "Test Company Global",
        "continents": {
            "Test Company Americas": [
                "Test Company USA",
                "Test Company Canada",
                "Test Company Brazil",
            ],
            "Test Company Europe": [
                "Test Company Germany",
                "Test Company France",
                "Test Company United Kingdom",
                "Test Company Sweden",
            ],
            "Test Company Asia Pacific": [
                "Test Company Japan",
                "Test Company India",
                "Test Company Australia",
                "Test Company Singapore",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def get_or_create(db: AsyncSession, name: str, parent_id: int | None) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        log.info("  skip  %s (already exists)", name)
        return existing

    company = Company(name=name, parent_id=parent_id, is_hierarchical=True)
    db.add(company)
    await db.flush()        # get the PK without committing yet
    log.info("  create %s (id=%s, parent_id=%s)", name, company.id, parent_id)
    return company


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def seed() -> None:
    async with AsyncSession(engine) as db:
        async with db.begin():
            for tree in TREES:
                # Level 1 — Global
                log.info("\n── %s", tree["global"])
                global_co = await get_or_create(db, tree["global"], parent_id=None)

                for continent_name, countries in tree["continents"].items():
                    # Level 2 — Continent
                    log.info("  ── %s", continent_name)
                    continent_co = await get_or_create(db, continent_name, parent_id=global_co.id)

                    # Level 3 — Countries
                    for country_name in countries:
                        await get_or_create(db, country_name, parent_id=continent_co.id)

    log.info("\nDone — all companies seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
