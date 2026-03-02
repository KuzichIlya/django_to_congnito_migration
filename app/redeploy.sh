#!/bin/bash
set -euo pipefail

# ── Auto-elevate to root if not already ───────────────────────────────────────
if [[ "${EUID}" -ne 0 ]]; then
  exec sudo --preserve-env \
    ARTIFACT_BUCKET="${ARTIFACT_BUCKET:-}" \
    ARTIFACT_KEY="${ARTIFACT_KEY:-}" \
    COGNITO_REGION="${COGNITO_REGION:-}" \
    COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-}" \
    COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-}" \
    APP_BASE_URL="${APP_BASE_URL:-}" \
    DATABASE_URL="${DATABASE_URL:-}" \
    AWS_REGION="${AWS_REGION:-}" \
    "$0" "$@"
fi

# ── Defaults ──────────────────────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-us-east-1}"
BASE_DIR="${BASE_DIR:-/opt/user-management}"
ARTIFACT_BUCKET="${ARTIFACT_BUCKET:-}"
ARTIFACT_KEY="${ARTIFACT_KEY:-app/user-management.zip}"
COGNITO_REGION="${COGNITO_REGION:-}"
COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-}"
COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-}"
APP_BASE_URL="${APP_BASE_URL:-}"
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://app:app@db:5432/app}"

# ── Positional arg overrides ──────────────────────────────────────────────────
ARTIFACT_BUCKET="${ARTIFACT_BUCKET:-${1:-}}"
ARTIFACT_KEY="${ARTIFACT_KEY:-${2:-app/user-management.zip}}"
COGNITO_REGION="${COGNITO_REGION:-${3:-}}"
COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-${4:-}}"
COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-${5:-}}"
APP_BASE_URL="${APP_BASE_URL:-${6:-}}"

# ── Validation ────────────────────────────────────────────────────────────────
require_env() {
  local key="$1" value="$2"
  if [[ -z "${value}" ]]; then
    echo "ERROR: required variable '${key}' is missing." >&2
    exit 1
  fi
}

if [[ -z "${ARTIFACT_BUCKET}" ]]; then
  echo "Usage: $0 <artifact-bucket> [artifact-key] <cognito-region> <cognito-user-pool-id> <cognito-client-id> <app-base-url>" >&2
  exit 1
fi

require_env "COGNITO_REGION"       "${COGNITO_REGION}"
require_env "COGNITO_USER_POOL_ID" "${COGNITO_USER_POOL_ID}"
require_env "COGNITO_CLIENT_ID"    "${COGNITO_CLIENT_ID}"
require_env "APP_BASE_URL"         "${APP_BASE_URL}"

# ── Docker Compose binary ─────────────────────────────────────────────────────
# Prefer standalone /usr/local/bin/docker-compose; fall back to CLI plugin.
if command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
elif docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  echo "ERROR: docker-compose / docker compose not found." >&2
  exit 1
fi

echo "Starting user-management redeploy."
echo "Region:          ${AWS_REGION}"
echo "Artifact:        s3://${ARTIFACT_BUCKET}/${ARTIFACT_KEY}"
echo "Base dir:        ${BASE_DIR}"
echo "APP_BASE_URL:    ${APP_BASE_URL}"
echo "Compose command: ${COMPOSE_CMD}"

# ── Stop existing stack ───────────────────────────────────────────────────────
COMPOSE_FILE="${BASE_DIR}/docker-compose.yml"

if [[ -f "${COMPOSE_FILE}" ]]; then
  echo "Stopping existing containers..."
  ${COMPOSE_CMD} -f "${COMPOSE_FILE}" down --remove-orphans || true
fi

# ── Clean previous files (keep pgdata volume mount-point) ────────────────────
echo "Cleaning previous application files..."
find "${BASE_DIR}" -maxdepth 1 -mindepth 1 \
     -not -name 'pgdata' \
     -exec rm -rf {} + 2>/dev/null || true

# ── Download artifact ─────────────────────────────────────────────────────────
TMP_ZIP="/tmp/user-management-app.zip"
echo "Downloading artifact..."
aws s3 cp "s3://${ARTIFACT_BUCKET}/${ARTIFACT_KEY}" "${TMP_ZIP}" --region "${AWS_REGION}"

# ── Extract ───────────────────────────────────────────────────────────────────
echo "Extracting artifact..."
mkdir -p "${BASE_DIR}"
unzip -o "${TMP_ZIP}" -d "${BASE_DIR}"
rm -f "${TMP_ZIP}"

# ── Write .env ────────────────────────────────────────────────────────────────
echo "Writing .env..."
cat > "${BASE_DIR}/.env" <<EOF
COGNITO_REGION=${COGNITO_REGION}
COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID}
COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
DATABASE_URL=${DATABASE_URL}
APP_BASE_URL=${APP_BASE_URL}
EOF

# ── Start app ─────────────────────────────────────────────────────────────────
echo "Starting containers..."
cd "${BASE_DIR}"
${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d --build

echo "Redeploy completed successfully."
echo "Logs: ${COMPOSE_CMD} -f ${COMPOSE_FILE} logs -f"
