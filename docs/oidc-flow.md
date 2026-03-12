# OIDC Authentication Flow

This document covers the OIDC authentication flow across three evolutionary phases:

1. **Pure Django** — Django acts as the OIDC Relying Party (RP); all OIDC logic lives in the monolith. No Cognito involvement.
2. **Migration (Cognito + Django)** — Cognito becomes the OIDC RP; Django provides internal Lambda APIs for access gating and user mapping; user accounts are linked transparently on first login.
3. **Post-Migration** — same as Migration, but the user already has a Cognito profile with `custom:django_id` set; no new mapping is created.

**Key difference from SAML**: There is **no discovery step** in the OIDC flow. The frontend redirects directly to Cognito's `/oauth2/authorize` with a hardcoded `identity_provider` name (`EntraOidc`). Django's `/api/auth/discovery` endpoint is not called. The frontend is responsible for knowing which Cognito provider name to use.

---

## Table of Contents

- [Entities](#entities)
- [1. Pure Django Approach](#1-pure-django-approach)
- [2. Migration Process (Cognito + Django)](#2-migration-process-cognito--django)
- [3. Post-Migration](#3-post-migration)
- [4. Comparison and Differences](#4-comparison-and-differences)
  - [4.1 Side-by-Side Comparison](#41-side-by-side-comparison)
  - [4.2 Endpoints Used vs. Not Used](#42-endpoints-used-vs-not-used)
- [5. PKCE in the OIDC Flow](#5-pkce-in-the-oidc-flow)
- [6. One-Time OIDC Provider Registration](#6-one-time-oidc-provider-registration)

---

## Entities

| Entity | Role |
|---|---|
| **Browser (SPA)** | Frontend single-page application (`web-login/app.js`). In the Cognito phase it generates PKCE pairs, stores `state` and `code_verifier` in `sessionStorage`, constructs the Cognito authorize URL directly, and exchanges the authorization code for tokens. |
| **Django Backend** | DRF REST API (`monolith/accounts/`), including the MySQL database. In the pure-Django phase it is the OIDC Relying Party. In the Cognito phase it provides internal Lambda APIs and is the authoritative store for users, company IdP configs, and migration mappings. It does **not** participate in the browser-facing redirect chain for OIDC in the Cognito phase. |
| **AWS Cognito** | Managed identity provider. In the Cognito phase it acts as the OIDC RP, federates with the IdP by exchanging authorization codes for ID tokens server-to-server, and issues its own JWT tokens to the frontend. |
| **IdP (Entra ID)** | The external OIDC Identity Provider (Microsoft Entra ID / Azure AD). Authenticates the user and issues an ID token. |
| **PostAuthFederationLink Lambda** | `infrastructure/src/post_auth_federation_link.py`. Runs after every federated login (SAML or OIDC). Calls Django internal APIs to look up the user and upsert `user_migration_mapping`, then sets `custom:django_id` on the Cognito profile via Admin API. |
| **PreTokenGeneration Lambda** | `infrastructure/src/pre_token_generation_claims.py`. Runs before every token issuance. Calls Django `POST /api/internal/login-access-check/` (unified gate for all methods). Django returns both the access decision and `django_id` in the same response. The Lambda injects `django_id` as a custom JWT claim. |
| **EnsureCognitoUser Lambda** | `infrastructure/src/ensure_cognito_user.py`. Non-VPC helper. Not involved in OIDC flows — used only in the password CUSTOM_AUTH flow. |

---

## 1. Pure Django Approach

In this phase Django is the OIDC **Relying Party (RP)**. There is no Cognito involvement. The browser communicates directly with Django and the IdP.

> **Note:** No pure Django OIDC implementation exists in the current codebase. The pure Django SAML flow (`saml_views.py`) is the only federated login path today. This section describes what a pure Django OIDC implementation would look like using a standard library such as [`mozilla-django-oidc`](https://mozilla-django-oidc.readthedocs.io/) or `social-auth-app-django`.

**Flow principle:** The browser navigates to a Django login-initiation endpoint. Django builds the IdP authorization URL (with PKCE), redirects the browser, and handles the IdP callback directly. No Cognito is involved.

### 1.1 Sequence Diagram

![](diagrams/oidc-01-pure-django.png)

### 1.2 Flow Summary

1. User clicks "Login with OIDC" on the frontend.
2. Frontend navigates the browser to `GET /api/auth/oidc/login/`.
3. Django generates a `state` nonce and a PKCE pair, stores them in the server-side session, builds the IdP `/authorize` URL, and returns `302` to the IdP.
4. The user authenticates on the IdP (Entra ID).
5. The IdP redirects back to Django's callback endpoint `GET /api/auth/oidc/callback/?code=AUTH_CODE&state=nonce`.
6. Django validates `state` against the session (CSRF check), then exchanges the authorization code for an ID token at the IdP's token endpoint (POST, with `code_verifier` for PKCE).
7. Django validates the ID token: signature (from IdP JWKS), issuer, audience, and expiry.
8. Django extracts the `email` claim from the ID token, creates or finds the `auth_user`, issues a DRF Token, and redirects the browser to `next#django_token=...&email=...`.
9. The frontend reads the token from the URL fragment and stores it.

### 1.3 Endpoint Contracts

#### `GET /api/auth/oidc/login/`

| Parameter | Location | Description |
|---|---|---|
| `next` | Query string | Optional redirect URL after successful login. Defaults to `settings.LOGIN_REDIRECT_URL`. |

**Response:** `302` redirect to IdP authorization URL:
```
https://login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize
  ?client_id=<django_client_id>
  &response_type=code
  &redirect_uri=https://app.example.com/api/auth/oidc/callback/
  &scope=openid+email+profile
  &state=<random_nonce>
  &code_challenge=<BASE64URL(SHA256(verifier))>
  &code_challenge_method=S256
```

#### `GET /api/auth/oidc/callback/`

| Parameter | Location | Description |
|---|---|---|
| `code` | Query string | Authorization code from the IdP. |
| `state` | Query string | Must match the value stored in the server-side session. |

Django exchanges the code for an ID token (server-to-server POST to IdP token endpoint) and validates it.

**Success response:** `302` redirect to `next#django_token=<token>&email=<email>`

**Error responses:**
- `400` `{"detail": "State mismatch — possible CSRF."}` when `state` does not match session value.
- `400` `{"detail": "Email claim not found in ID token."}` when the IdP token lacks an email claim.
- `400` `{"detail": "Token validation failed: <reason>."}` for signature / issuer / audience / expiry errors.
- `500` `{"detail": "<exception message>"}` for unexpected errors.

### 1.4 Required IdP Configuration

| Setting | Value |
|---|---|
| Application type | Web / Confidential client |
| Redirect URI | `https://app.example.com/api/auth/oidc/callback/` |
| Client ID | Registered with IdP; stored in `settings.OIDC_RP_CLIENT_ID` |
| Client Secret | Registered with IdP; stored in `settings.OIDC_RP_CLIENT_SECRET` |
| Token endpoint auth method | `client_secret_post` or `client_secret_basic` |
| Scopes | `openid email profile` |
| Access token version | 2 (for Entra ID — set `"accessTokenAcceptedVersion": 2` in app manifest) |

> Source files (to be created): `monolith/accounts/oidc_views.py`, Django settings `OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET`, `OIDC_OP_AUTHORIZATION_ENDPOINT`, `OIDC_OP_TOKEN_ENDPOINT`, `OIDC_OP_JWKS_ENDPOINT`.

---

## 2. Migration Process (Cognito + Django)

In this phase **Cognito becomes the OIDC Relying Party**. Django is not involved in the browser-facing redirect chain. Instead:

- The frontend constructs the Cognito `/oauth2/authorize` URL directly with `identity_provider=EntraOidc` and PKCE parameters. No Django discovery call is made.
- Cognito handles the OIDC handshake with Entra ID server-to-server: it exchanges the IdP authorization code for an ID token, validates it, and creates a federated Cognito user.
- Cognito's `PostAuthFederationLink` Lambda links the federated user to the Django user on first login.
- Cognito's `PreTokenGeneration` Lambda gates access and injects the `django_id` claim before tokens are issued.

**Statement:** There is no discovery step. The frontend has the Cognito provider name (`EntraOidc`) hardcoded in `LOGIN_CONFIG.oidcProviderName` and redirects directly to Cognito.

### 2.1 Sequence Diagram

![](diagrams/oidc-02-migration.png)

### 2.2 Flow Summary

1. User clicks "Login with OIDC" on the frontend.
2. Frontend generates a PKCE pair (`code_verifier`, `code_challenge`) and a random `state` nonce. All three values are stored in `sessionStorage`.
3. Frontend constructs the Cognito `/oauth2/authorize` URL directly with `identity_provider=EntraOidc`, PKCE parameters, and `state`, then navigates the browser to it.
4. Cognito looks up the `EntraOidc` OIDC provider, builds its own authorization request to the IdP, and redirects the browser to the IdP login page.
5. The user authenticates on Entra ID. The IdP redirects back to Cognito's response endpoint (`/oauth2/idpresponse`) with a short-lived authorization code.
6. Cognito exchanges the IdP code for an ID token (server-to-server POST to the IdP token endpoint), validates the ID token (signature, issuer, audience, expiry), extracts the email, creates a federated Cognito user, generates its own authorization code, and redirects the browser to the frontend callback URL with `?code=AUTH_CODE&state=nonce`.
7. Frontend asserts `state === sessionStorage.federated_auth_nonce` (client-side CSRF check).
8. Frontend exchanges the authorization code for tokens at `POST /oauth2/token` with the stored `code_verifier`.
9. Cognito triggers `PostAuthFederationLink`:
   - Calls `GET /api/internal/user-lookup/` to get the Django user ID by email.
   - Calls `POST /api/internal/link-cognito/` to upsert `user_migration_mapping`.
   - Calls `AdminUpdateUserAttributes` to set `custom:django_id` on the Cognito profile.
10. Cognito triggers `PreTokenGeneration`:
    - Detects `login_method = "oidc"` from the `identities` attribute (`providerType: "OIDC"`).
    - Calls `POST /api/internal/login-access-check/` to gate access.
    - The response includes `django_id` — no separate call needed, even on first login when `custom:django_id` is not yet on the Cognito profile.
    - Injects `django_id` claim into the ID token.
11. Cognito returns `{id_token, access_token, refresh_token}` to the frontend.

### 2.3 Endpoint Contracts

#### Cognito `/oauth2/authorize` (GET — constructed and followed directly by browser)

| Parameter | Location | Description |
|---|---|---|
| `identity_provider` | Query string | Cognito provider name — must match the `ProviderName` of the registered OIDC IdP (e.g. `EntraOidc`). |
| `response_type` | Query string | Must be `code`. |
| `client_id` | Query string | Cognito app client ID. |
| `redirect_uri` | Query string | Frontend callback URL (must be registered with the Cognito app client). |
| `scope` | Query string | `openid email profile`. |
| `state` | Query string | Random nonce generated by the frontend. |
| `code_challenge` | Query string | `BASE64URL(SHA256(code_verifier))` — PKCE challenge. |
| `code_challenge_method` | Query string | Must be `S256`. |

#### Cognito `/oauth2/token` (POST — browser fetch)

| Field | Value |
|---|---|
| `grant_type` | `authorization_code` |
| `client_id` | Cognito app client ID |
| `code` | Authorization code from callback |
| `redirect_uri` | Must match the one used in `/oauth2/authorize` |
| `code_verifier` | Original random verifier from PKCE pair |

**Response (200):**
```json
{
  "id_token":      "<JWT>",
  "access_token":  "<JWT>",
  "refresh_token": "<opaque>",
  "token_type":    "Bearer",
  "expires_in":    3600
}
```

#### `GET /api/internal/user-lookup/` (called by PostAuthFederationLink Lambda)

| Parameter | Location | Description |
|---|---|---|
| `email` | Query string | User email extracted from the Cognito user attributes. |

**Response (200):**
```json
{ "id": 42, "email": "user@example.com" }
```

**Response (404):** User not found in Django — PostAuth Lambda logs a warning and skips mapping.

#### `POST /api/internal/link-cognito/` (called by PostAuthFederationLink Lambda)

| Field | Type | Description |
|---|---|---|
| `django_user_id` | integer | Django `auth_user.id` returned by `/user-lookup/`. |
| `cognito_user_id` | string | Cognito user UUID (`sub` attribute). |
| `email` | string | User email. |

**Response (200):**
```json
{ "linked": true }
```

Operation is idempotent — on subsequent logins it updates the existing mapping record.

#### `POST /api/internal/login-access-check/` (called by PreTokenGeneration Lambda)

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | yes | User email from Cognito `userAttributes`. |
| `login_method` | `"oidc"` | yes | Login method detected from `identities` attribute. |
| `provider_name` | string | no | Cognito provider name (e.g. `EntraOidc`). |

**Response (200):**
```json
{ "allowed": true,  "django_id": "42" }
{ "allowed": false, "reason": "user_not_found", "django_id": null }
```

`django_id` is always returned alongside the access decision. `PreTokenGeneration` uses this value directly — no second round-trip to Django is needed, even on the first OIDC login when `custom:django_id` is not yet stored on the Cognito profile.

---

## 3. Post-Migration

In this phase the user already has a Cognito profile with `custom:django_id` set from a previous OIDC login. The flow is identical to the Migration phase with two differences:

1. Cognito matches the existing federated user — no new Cognito account is created.
2. `PostAuthFederationLink` performs an idempotent upsert (no-op if the mapping already exists).
3. `PreTokenGeneration` receives `django_id` directly from the `login-access-check` response — same as in the migration phase.

### 3.1 Sequence Diagram

![](diagrams/oidc-03-post-migration.png)

### 3.2 Flow Summary

Steps 1–8 are identical to the Migration flow (PKCE generation → direct Cognito redirect → IdP → callback → state check → token exchange).

On token exchange:
- `PostAuthFederationLink` runs the same lookup + upsert (idempotent).
- `PreTokenGeneration` calls `login-access-check`, receives `{"allowed":true,"django_id":"42"}`, and injects the claim. The flow is identical to the migration path.

### 3.3 Endpoint Contracts

All endpoints are identical to section 2.3. No additional endpoints are used or removed in the post-migration phase.

---

## 4. Comparison and Differences

### 4.1 Side-by-Side Comparison

| Concern | Pure Django | Migration / Post-Migration |
|---|---|---|
| **OIDC Relying Party** | Django (`mozilla-django-oidc`) | AWS Cognito |
| **IdP configuration stored in** | Django settings / DB (`OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET`, issuer URL) | Cognito `OidcIdentityProvider` resource (`client_id`, `client_secret`, `oidc_issuer`) |
| **Discovery step** | Not applicable — Django login URL is fixed | **Not used** — frontend goes directly to Cognito with hardcoded `identity_provider` name |
| **Authorization URL builder** | Django (server-side, returns 302 to IdP) | Browser (client-side, navigates directly to Cognito) |
| **OIDC token exchange** | Django ↔ IdP (server-to-server, with `code_verifier`) | Cognito ↔ IdP (server-to-server, Cognito's own PKCE) |
| **ID token validation** | Django (signature from IdP JWKS, issuer, audience, expiry) | Cognito (built-in OIDC RP functionality) |
| **Callback endpoint** | `GET /api/auth/oidc/callback/` on Django | Cognito `/oauth2/idpresponse` (invisible to browser) + browser callback via `/oauth2/authorize` |
| **Token issued to browser** | DRF Token (opaque), delivered in URL fragment | Cognito JWT (`id_token` + `access_token` + `refresh_token`), delivered as JSON |
| **PKCE** | Django generates for IdP request; stored in server session | Browser generates for Cognito request; stored in `sessionStorage` |
| **User creation** | Django callback view creates user if not found | `PostAuthFederationLink` Lambda links user; Cognito creates federated profile |
| **Access gate** | None | `PreTokenGeneration` → Django `/api/internal/login-access-check/` (returns `allowed` + `django_id`) |
| **`django_id` in token** | Not applicable | Injected as custom JWT claim by `PreTokenGeneration` |
| **Direct DB access from Lambda** | N/A | None — all via Django internal APIs |

### 4.2 Endpoints Used vs. Not Used

| Endpoint | Pure Django | Migration | Post-Migration |
|---|---|---|---|
| `GET /api/auth/oidc/login/` | **Used** (by browser) | Not used | Not used |
| `GET /api/auth/oidc/callback/` | **Used** (by IdP redirect) | Not used (Cognito handles `/oauth2/idpresponse`) | Not used |
| `GET /api/auth/discovery` | Not used | **Not used** — no discovery step for OIDC | **Not used** |
| `GET /api/internal/user-lookup/` | Not applicable | **Used** (by PostAuth Lambda) | **Used** (by PostAuth Lambda) |
| `POST /api/internal/link-cognito/` | Not applicable | **Used** (by PostAuth Lambda) | **Used** (by PostAuth Lambda — idempotent) |
| `POST /api/internal/login-access-check/` | Not applicable | **Used** (by PreToken Lambda) | **Used** (by PreToken Lambda) |
| `GET /api/internal/resolve-django-id/` | Not applicable | Not used — `django_id` returned by `login-access-check` | Not used |
| Cognito `/oauth2/authorize` | Not used | **Used** (constructed and followed directly by browser) | **Used** (constructed and followed directly by browser) |
| Cognito `/oauth2/token` | Not used | **Used** (by frontend — fetch) | **Used** (by frontend — fetch) |

---

## 5. PKCE in the OIDC Flow

PKCE (Proof Key for Code Exchange, RFC 7636) is used at two independent layers in this flow:

| Layer | Who generates PKCE | Who validates PKCE |
|---|---|---|
| **Browser → Cognito** | Browser (`app.js` `generateCodeVerifier`) | Cognito (verifies `code_verifier` against `code_challenge` on `POST /oauth2/token`) |
| **Cognito → IdP** | Cognito (internal, not visible to browser) | IdP (Entra ID validates Cognito's PKCE on its token endpoint) |

The browser's `code_verifier` is stored in `sessionStorage` and never sent to the IdP. Cognito generates its own independent PKCE pair for the IdP leg.

### Browser-side PKCE implementation (`app.js`)

```javascript
// Generate PKCE pair and state:
const codeVerifier  = generateCodeVerifier();          // random 32B base64url
const codeChallenge = await generateCodeChallenge(codeVerifier); // SHA-256
const state         = generateCodeVerifier();           // random nonce (reuse generator)

sessionStorage.setItem("federated_auth_nonce",    state);
sessionStorage.setItem("federated_code_verifier", codeVerifier);
sessionStorage.setItem("federated_provider_type", "OIDC");

// Navigate directly to Cognito (no discovery step):
window.location.href =
    `https://${cognitoDomain}/oauth2/authorize`
    + `?identity_provider=${encodeURIComponent(providerName)}`   // "EntraOidc"
    + `&response_type=code`
    + `&client_id=${encodeURIComponent(clientId)}`
    + `&redirect_uri=${encodeURIComponent(callbackUrl)}`
    + `&scope=openid+email+profile`
    + `&state=${encodeURIComponent(state)}`
    + `&code_challenge=${encodeURIComponent(codeChallenge)}`
    + `&code_challenge_method=S256`;
```

### Security properties

| Threat | Protection |
|---|---|
| Authorization code stolen from callback URL | **PKCE** — attacker cannot exchange the code without the `code_verifier` stored in the legitimate browser's `sessionStorage` |
| CSRF — attacker forces the callback to run in the victim's browser | **`state` parameter** — frontend asserts `state === sessionStorage.federated_auth_nonce` |
| IdP code intercepted between IdP and Cognito | **Cognito's own PKCE** — Cognito generates an independent PKCE pair for the IdP leg |

### Entra ID requirements

Microsoft Entra ID (v2.0 endpoint) requires PKCE for cross-origin authorization code redemption. Required Entra app manifest setting:

```json
{ "accessTokenAcceptedVersion": 2 }
```

The Cognito OIDC issuer must point to the v2.0 endpoint:
```
https://login.microsoftonline.com/<tenant-id>/v2.0
```

If Entra returns `AADSTS9002325: Proof Key for Code Exchange is required`, verify that the issuer URL is the v2.0 endpoint and that `accessTokenAcceptedVersion` is set to `2` in the app manifest.

---

## 6. One-Time OIDC Provider Registration

Before using the Cognito-based OIDC flow, the OIDC provider must be registered in the Cognito User Pool. This is done once via the SAM template — unlike SAML, there is no separate sync job because the OIDC configuration is captured entirely in infrastructure parameters.

### SAM template parameters

```yaml
# samconfig.toml — set these before deploying:
OidcProviderEnabled = "true"
OidcProviderName    = "EntraOidc"
OidcIssuer          = "https://login.microsoftonline.com/<tenant-id>/v2.0"
OidcClientId        = "<entra-application-client-id>"
OidcClientSecret    = "<entra-client-secret-value>"
OidcAuthorizeScopes = "openid email profile"
```

The `OidcIdentityProvider` resource in `infrastructure/template.yaml` (created conditionally when `OidcProviderEnabled = "true"`) registers the provider in the User Pool and adds it to the app client's `SupportedIdentityProviders`.

### Entra ID app registration (one-time)

| Setting in Entra | Value |
|---|---|
| **Application type** | Web / Confidential client |
| **Redirect URI** | `https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/idpresponse` |
| **Client ID** | Displayed in the app registration overview — use as `OidcClientId` |
| **Client Secret** | Created under "Certificates & secrets" — use as `OidcClientSecret` |
| **Supported account types** | Single-tenant or multi-tenant, depending on requirements |
| **Access token version** | `"accessTokenAcceptedVersion": 2` in app manifest |
| **ID token issuance** | Enable ID tokens under "Authentication → Implicit grant and hybrid flows" |

The Cognito domain and User Pool ID are stable after initial deployment and do not change between logins.

### Differences from SAML registration

| Aspect | SAML | OIDC |
|---|---|---|
| **Cognito provider type** | `SAML` (metadata XML URL) | `OIDC` (issuer URL + client credentials) |
| **Requires client secret** | No (trust is based on metadata + signature) | Yes (`OidcClientSecret`) |
| **IdP registration artifact** | SP metadata XML (`urn:amazon:cognito:sp:<pool-id>` entity ID) | Redirect URI + client ID |
| **Sync job needed** | Yes — one-time management command when migrating from Django | No — configuration is fully in SAM parameters |
| **Per-company config** | Stored in Django DB / `SAML_PROVIDER_MAP`; synced to Cognito | Stored in SAM parameters / Cognito directly; Django has `OIDC_PROVIDER_MAP` equivalent |

---

*Diagrams rendered with [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) v11. Source files are in `docs/diagrams/oidc-*.mmd`.*
