import asyncio
from contextlib import suppress

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.gmail_auto_processor import process_unread_gmail_messages


async def gmail_auto_check_loop():
    while True:
        await asyncio.to_thread(_run_once)
        await asyncio.sleep(settings.GMAIL_AUTO_CHECK_INTERVAL_SECONDS)


def _run_once():
    db = SessionLocal()

    try:
        process_unread_gmail_messages(db)
    finally:
        db.close()


async def stop_gmail_auto_check(task):
    task.cancel()

    with suppress(asyncio.CancelledError):
        await task
