<<<<<<< HEAD
from app.api.v1.endpoints.gmail import router

__all__ = ["router"]
=======
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.services.mock_gmail_service import MockGmailService
try:
    from app.services.gmail_service import GmailService
except Exception:
    GmailService = None
from app.database import SessionLocal
from app.services.ticket_service import create_ticket
from app.agents.freight_agent import classify_email

router = APIRouter()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@router.get("/gmail/unread")
def fetch_unread(from_email: str | None = None):
    svc = None
    if GmailService:
        try:
            svc = GmailService()
        except Exception:
            svc = None

    if not svc:
        svc = MockGmailService()

    emails = svc.fetch_unread_emails_filtered(from_email)
    return emails


@router.post("/gmail/process-unread")
def process_unread(from_email: str | None = None, db: Session = Depends(get_db)):
    svc = None
    if GmailService:
        try:
            svc = GmailService()
        except Exception:
            svc = None

    if not svc:
        svc = MockGmailService()

    emails = svc.fetch_unread_emails_filtered(from_email)

    processed = []

    for e in emails:
        try:
            ai_result = classify_email(e["body"])

            # create a simple payload-like object for create_ticket
            payload = type("P", (object,), {
                "subject": e.get("subject"),
                "sender": e.get("sender"),
                "body": e.get("body")
            })()

            ticket = create_ticket(db, payload, ai_result)

            processed.append({
                "gmail_message_id": e.get("gmail_message_id"),
                "ticket_id": ticket.id
            })

        except Exception as exc:
            processed.append({
                "gmail_message_id": e.get("gmail_message_id"),
                "error": str(exc)
            })

    return processed
>>>>>>> 8fb891641c9da45804261409e0f79589b417a299
