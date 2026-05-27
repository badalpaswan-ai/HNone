from datetime import datetime
from types import SimpleNamespace

from app.agents.freight_agent import classify_email, is_freight_email
from app.core.config import settings
from app.services.gmail_decision_service import (
    save_accepted_decision,
    save_not_accepted_decision,
    save_review_required_decision,
    split_unchecked_emails,
)
from app.services.gmail_factory import gmail_service_type, resolve_gmail_service
from app.services.ticket_service import create_ticket

AUTO_PROCESS_CONFIDENCE_THRESHOLD = 0.7


def process_unread_gmail_messages(
    db,
    from_email: str | None = None,
    max_results: int = 10,
    department: str | None = None,
):
    service = resolve_gmail_service()
    emails = service.fetch_unread_emails_filtered(
        from_email,
        max_results=max_results,
    )
    emails, previously_processed = split_unchecked_emails(db, emails)

    processed = [
        {
            "gmail_message_id": email.get("gmail_message_id"),
            "skipped": True,
            "already_saved": True,
            "reason": email.get("reason"),
            "decision": email.get("decision"),
            "ticket_id": email.get("ticket_id"),
            "welcome_sent_at": email.get("welcome_sent_at"),
        }
        for email in previously_processed
    ]

    for email in emails:
        try:
            welcome_result = _send_welcome_email(service, email)
            email["welcome_sent_at"] = datetime.utcnow()

            ai_result = classify_email(
                email["body"],
                subject=email.get("subject"),
            )

            if not is_freight_email(ai_result):
                decision_result = save_not_accepted_decision(
                    db,
                    email,
                    "Email not classified as freight-related",
                    ai_result,
                )
                processed.append({
                    "gmail_message_id": email.get("gmail_message_id"),
                    "skipped": True,
                    "reason": "Email not classified as freight-related",
                    "welcome_result": welcome_result,
                    "ai_result": ai_result,
                    "decision_result": decision_result,
                })
                continue

            if float(ai_result.get("confidence_score") or 0) < AUTO_PROCESS_CONFIDENCE_THRESHOLD:
                decision_result = save_review_required_decision(
                    db,
                    email,
                    "Low AI confidence; needs human review",
                    ai_result,
                )
                processed.append({
                    "gmail_message_id": email.get("gmail_message_id"),
                    "skipped": True,
                    "reason": "Low AI confidence; needs human review",
                    "welcome_result": welcome_result,
                    "ai_result": ai_result,
                    "decision_result": decision_result,
                })
                continue

            if department and ai_result["department"] != department:
                decision_result = save_review_required_decision(
                    db,
                    email,
                    "Email belongs to another department",
                    ai_result,
                )
                processed.append({
                    "gmail_message_id": email.get("gmail_message_id"),
                    "skipped": True,
                    "reason": "Email belongs to another department",
                    "welcome_result": welcome_result,
                    "ai_result": ai_result,
                    "decision_result": decision_result,
                })
                continue

            payload = SimpleNamespace(
                subject=email.get("subject"),
                sender=email.get("sender"),
                body=email.get("body"),
            )
            ticket = create_ticket(db, payload, ai_result)
            decision_result = save_accepted_decision(
                db,
                email,
                ticket.id,
                ai_result,
            )
            processed.append({
                "gmail_message_id": email.get("gmail_message_id"),
                "ticket_id": ticket.id,
                "assigned_employee_id": ticket.assigned_employee_id,
                "welcome_result": welcome_result,
                "classification": ai_result,
                "decision_result": decision_result,
            })
        except Exception as exc:
            processed.append({
                "gmail_message_id": email.get("gmail_message_id"),
                "error": str(exc),
            })

    return {
        "service": gmail_service_type(service),
        "processed_count": len(processed),
        "results": processed,
    }


def _send_welcome_email(service, email):
    sender = email.get("sender")

    if not sender:
        return {
            "sent": False,
            "reason": "Missing sender email",
        }

    return service.send_email(
        to_email=sender,
        subject=settings.WELCOME_EMAIL_SUBJECT,
        body=settings.WELCOME_EMAIL_BODY,
        thread_id=email.get("gmail_thread_id"),
    )
