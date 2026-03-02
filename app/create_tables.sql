-- Database Schema: Company & User Management System (Cognito Auth)

-- Core Tables

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    parent_id INTEGER REFERENCES companies(id),
    is_hierarchical BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id),
    notes TEXT,
    -- cognito_sub: UUID 'sub' claim from the Cognito JWT; links local record to Cognito identity
    cognito_sub VARCHAR(200) UNIQUE,
    username VARCHAR(200),
    name VARCHAR(200),
    -- admin flags (managed locally; Cognito groups are NOT used for authorisation)
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_superadmin BOOLEAN NOT NULL DEFAULT FALSE
);

-- User <-> Company junction tables

CREATE TABLE user_companies (
    user_id INTEGER NOT NULL REFERENCES users(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    PRIMARY KEY (user_id, company_id)
);

CREATE TABLE user_blocked_companies (
    user_id INTEGER NOT NULL REFERENCES users(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    PRIMARY KEY (user_id, company_id)
);

CREATE TABLE user_granular_blocked_companies (
    user_id INTEGER NOT NULL REFERENCES users(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    PRIMARY KEY (user_id, company_id)
);

-- User <-> Permission junction tables

CREATE TABLE user_add_rights (
    user_id INTEGER NOT NULL REFERENCES users(id),
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (user_id, permission_id)
);

CREATE TABLE user_minus_rights (
    user_id INTEGER NOT NULL REFERENCES users(id),
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (user_id, permission_id)
);

-- Company/Role <-> Permission junction tables

CREATE TABLE role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(id),
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE company_roles (
    company_id INTEGER NOT NULL REFERENCES companies(id),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    PRIMARY KEY (company_id, role_id)
);

CREATE TABLE company_permissions (
    company_id INTEGER NOT NULL REFERENCES companies(id),
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (company_id, permission_id)
);
