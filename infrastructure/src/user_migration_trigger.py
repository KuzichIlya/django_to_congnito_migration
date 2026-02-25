import json
import logging
import os
from urllib import error as urllib_error
from urllib import request as urllib_request

import boto3
import pymysql


logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

ssm_client = boto3.client("ssm")

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USERNAME_SSM_PATH = os.environ.get("DB_USERNAME_SSM_PATH")
DB_PASSWORD_SSM_PATH = os.environ.get("DB_PASSWORD_SSM_PATH")
DJANGO_LOGIN_URL = os.environ.get("DJANGO_LOGIN_URL")

_db_credentials = None


def _get_db_credentials():
    global _db_credentials
    if _db_credentials is None:
        logger.info("Loading DB credentials from SSM paths.")
        username = ssm_client.get_parameter(Name=DB_USERNAME_SSM_PATH)["Parameter"]["Value"]
        password = ssm_client.get_parameter(Name=DB_PASSWORD_SSM_PATH)["Parameter"]["Value"]
        _db_credentials = (username, password)
        logger.info("DB credentials loaded from SSM successfully.")
    return _db_credentials


def _get_connection():
    username, password = _get_db_credentials()
    return pymysql.connect(
        host=DB_HOST,
        user=username,
        password=password,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        autocommit=True,
    )


def _validate_django_credentials(email, password):
    if not DJANGO_LOGIN_URL:
        logger.error("DJANGO_LOGIN_URL is not configured.")
        raise RuntimeError("DJANGO_LOGIN_URL is not configured")

    logger.info("Validating Django credentials via URL: %s", DJANGO_LOGIN_URL)
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib_request.Request(
        DJANGO_LOGIN_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=10) as response:
            logger.info("Django login request succeeded with status %s", response.status)
            return True
    except urllib_error.HTTPError as exc:
        logger.warning("Django login returned HTTP %s for user %s", exc.code, email)
        if exc.code == 401:
            return False
        raise
    except urllib_error.URLError as exc:
        logger.error("Django login network error for user %s: %s", email, exc.reason)
        raise


def _get_django_user(email):
    logger.info("Querying Django user by email from MySQL.")
    connection = _get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, email
                FROM auth_user
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email,),
            )
            result = cursor.fetchone()
            if result:
                logger.info("Django user found in DB for email %s.", email)
            else:
                logger.warning("Django user not found in DB for email %s.", email)
            return result


def _upsert_mapping(django_user_id, email, cognito_user_id):
    logger.info("Upserting migration mapping for email %s.", email)
    connection = _get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_migration_mapping (django_user_id, cognito_user_id, email, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                  cognito_user_id = VALUES(cognito_user_id),
                  email = VALUES(email),
                  updated_at = NOW()
                """,
                (django_user_id, cognito_user_id, email),
            )
    logger.info("Migration mapping upserted for email %s.", email)


def handler(event, context):
    logger.info("User migration trigger invoked.")
    trigger_source = event.get("triggerSource")
    logger.info("Trigger source: %s", trigger_source)
    if trigger_source != "UserMigration_Authentication":
        logger.info("Skipping trigger source %s.", trigger_source)
        return event

    email = event.get("userName", "")
    password = event.get("request", {}).get("password", "")
    logger.info("Processing migration for username/email: %s", email)
    if not email or not password:
        logger.error("Invalid migration request: missing email or password.")
        raise Exception("Invalid migration request")

    is_valid = _validate_django_credentials(email, password)
    if not is_valid:
        logger.warning("Django credential validation failed for user %s.", email)
        raise Exception("Invalid credentials")
    logger.info("Django credential validation passed for user %s.", email)

    django_user = _get_django_user(email)
    if not django_user:
        raise Exception("Django user not found")

    django_user_id = django_user["id"]
    _upsert_mapping(
        django_user_id=django_user_id,
        email=django_user["email"],
        cognito_user_id=email,
    )

    logger.info("Building Cognito migration response for user %s.", email)
    event["response"]["userAttributes"] = {
        "email": django_user["email"],
        "email_verified": "true",
        "custom:django_id": str(django_user_id),
    }
    event["response"]["finalUserStatus"] = "CONFIRMED"
    event["response"]["messageAction"] = "SUPPRESS"
    event["response"]["desiredDeliveryMediums"] = []
    logger.info("Migration completed for user %s.", email)
    return event
