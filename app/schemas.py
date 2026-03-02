"""Pydantic request schemas for all API endpoints."""

from pydantic import BaseModel


class PermissionIn(BaseModel):
    name: str


class RoleIn(BaseModel):
    name: str
    description: str | None = None
    permission_ids: list[int] = []


class CompanyIn(BaseModel):
    name: str
    parent_id: int | None = None
    is_hierarchical: bool = False
    role_ids: list[int] = []
    permission_ids: list[int] = []


class CompanyPatch(BaseModel):
    """Partial update: set the single role and/or permission list for a company."""
    role_id: int | None = None      # None = clear the role
    permission_ids: list[int] = []  # full replacement of the permission list


class CompanyAssignment(BaseModel):
    """Per-company role + permission assignment for a user."""
    company_id: int
    role_id: int | None = None      # one role for this user at this company
    permission_ids: list[int] = []  # permissions granted at this company


class UserIn(BaseModel):
    cognito_sub: str            # Cognito user's UUID sub — links Cognito identity to local record
    username: str
    name: str | None = None
    email: str | None = None    # Stored for reference; Cognito manages authentication
    # Per-company access with optional role + permissions per company
    company_assignments: list[CompanyAssignment] = []
    blocked_company_ids: list[int] = []
    notes: str | None = None
    minus_right_ids: list[int] = []     # global permission denials (override all companies)
    is_admin: bool = False
    is_superadmin: bool = False
