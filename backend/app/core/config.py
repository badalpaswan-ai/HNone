import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")

class Settings:

    APP_NAME = "Freight AI Operations POC"

    APP_VERSION = "1.0.0"

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'freight_ai.db'}"
    )

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    ANTHROPIC_MODEL = os.getenv(
        "ANTHROPIC_MODEL",
        "claude-3-5-sonnet-20241022"
    )

    AI_MODE = os.getenv(
        "AI_MODE",
        "auto"
    ).lower()

    RESET_INCOMPATIBLE_SQLITE_SCHEMA = os.getenv(
        "RESET_INCOMPATIBLE_SQLITE_SCHEMA",
        "true"
    ).lower() == "true"

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "dev-secret-change-me"
    )

    JWT_EXPIRE_MINUTES = int(os.getenv(
        "JWT_EXPIRE_MINUTES",
        "480"
    ))

    MAIL_OPEN_NOTIFICATION_SECONDS = int(os.getenv(
        "MAIL_OPEN_NOTIFICATION_SECONDS",
        "20"
    ))

    MAIL_RESOLVE_NOTIFICATION_SECONDS = int(os.getenv(
        "MAIL_RESOLVE_NOTIFICATION_SECONDS",
        "60"
    ))

    GMAIL_AUTO_CHECK_INTERVAL_SECONDS = int(os.getenv(
        "GMAIL_AUTO_CHECK_INTERVAL_SECONDS",
        "900"
    ))

    GMAIL_AUTO_CHECK_ENABLED = os.getenv(
        "GMAIL_AUTO_CHECK_ENABLED",
        "true"
    ).lower() == "true"

    WELCOME_EMAIL_SUBJECT = os.getenv(
        "WELCOME_EMAIL_SUBJECT",
        "Welcome to HNOne"
    )

    WELCOME_EMAIL_BODY = os.getenv(
        "WELCOME_EMAIL_BODY",
        "Welcome to HNOne, we will reach out to you with a response within 30 mins."
    )

settings = Settings()
