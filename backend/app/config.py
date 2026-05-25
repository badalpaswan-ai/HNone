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

settings = Settings()
