"""
FastAPI application factory.

Wires together:
  - DB lifespan (table creation + schema migrations) from models.py
  - Auth layer                                        from auth.py
  - Business-logic helpers                            from services.py
  - API routers                                       from routers/
  - Embedded HTML SPA                                 from page.py
"""

import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from models import lifespan
from page import PAGE_HTML
from routers import auth, companies, permissions, roles, users

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Company & User Management (Cognito Auth)",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(permissions.router)
app.include_router(roles.router)
app.include_router(companies.router)
app.include_router(users.router)

# ---------------------------------------------------------------------------
# HTML SPA
# ---------------------------------------------------------------------------


@app.get("/users", include_in_schema=False)
async def users_page() -> HTMLResponse:
    """Serve the single-page admin UI. Auth is handled client-side via bearer token."""
    return HTMLResponse(PAGE_HTML)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/users")
