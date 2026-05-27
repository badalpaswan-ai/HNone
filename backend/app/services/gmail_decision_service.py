import json

from app.models.gmail_processing_decision import GmailProcessingDecision
from app.models.employee import Employee
from app.models.ticket import Ticket


NOT_ACCEPTED = "not_accepted"
ACCEPTED = "accepted"
REVIEW_REQUIRED = "review_required"


def get_saved_decisions(db, message_ids: list[str]) -> dict[str, GmailProcessingDecision]:
    if not message_ids:
        return {}

    decisions = (
        db.query(GmailProcessingDecision)
        .filter(GmailProcessingDecision.gmail_message_id.in_(message_ids))
        .all()
    )

    return {
        decision.gmail_message_id: decision
        for decision in decisions
    }


def split_unchecked_emails(db, emails: list[dict]) -> tuple[list[dict], list[dict]]:
    message_ids = [
        email.get("gmail_message_id")
        for email in emails
        if email.get("gmail_message_id")
    ]
    saved_decisions = get_saved_decisions(db, message_ids)

    unchecked = []
    previously_processed = []

    for email in emails:
        message_id = email.get("gmail_message_id")
        decision = saved_decisions.get(message_id)

        if decision:
            previously_processed.append({
                **email,
                "skipped": True,
                "reason": decision.reason,
                "decision": decision.decision,
                "ticket_id": decision.ticket_id,
                "welcome_sent_at": (
                    decision.welcome_sent_at.isoformat()
                    if decision.welcome_sent_at
                    else None
                ),
                "decision_saved_at": (
                    decision.updated_at.isoformat()
                    if decision.updated_at
                    else None
                )
            })
            continue

        unchecked.append(email)

    return unchecked, previously_processed


def save_not_accepted_decision(
    db,
    email: dict,
    reason: str,
    ai_result: dict | None = None,
) -> dict:
    message_id = email.get("gmail_message_id")

    if not message_id:
        return {
            "saved": False,
            "reason": "Missing Gmail message id"
        }

    decision = (
        db.query(GmailProcessingDecision)
        .filter(GmailProcessingDecision.gmail_message_id == message_id)
        .first()
    )

    if not decision:
        decision = GmailProcessingDecision(gmail_message_id=message_id)
        db.add(decision)

    decision.decision = NOT_ACCEPTED
    decision.reason = reason
    decision.subject = email.get("subject")
    decision.sender = email.get("sender")
    decision.body = email.get("body")
    decision.snippet = email.get("snippet")
    decision.internal_date = email.get("internal_date")
    decision.classification_json = json.dumps(ai_result or {})
    decision.welcome_sent_at = email.get("welcome_sent_at")

    db.commit()
    db.refresh(decision)

    return {
        "saved": True,
        "gmail_message_id": message_id,
        "decision": decision.decision,
        "reason": decision.reason,
        "decision_id": decision.id,
    }


def save_review_required_decision(
    db,
    email: dict,
    reason: str,
    ai_result: dict | None = None,
) -> dict:
    message_id = email.get("gmail_message_id")

    if not message_id:
        return {
            "saved": False,
            "reason": "Missing Gmail message id"
        }

    decision = (
        db.query(GmailProcessingDecision)
        .filter(GmailProcessingDecision.gmail_message_id == message_id)
        .first()
    )

    if not decision:
        decision = GmailProcessingDecision(gmail_message_id=message_id)
        db.add(decision)

    decision.decision = REVIEW_REQUIRED
    decision.reason = reason
    decision.subject = email.get("subject")
    decision.sender = email.get("sender")
    decision.body = email.get("body")
    decision.snippet = email.get("snippet")
    decision.internal_date = email.get("internal_date")
    decision.classification_json = json.dumps(ai_result or {})
    decision.welcome_sent_at = email.get("welcome_sent_at")

    db.commit()
    db.refresh(decision)

    return {
        "saved": True,
        "gmail_message_id": message_id,
        "decision": decision.decision,
        "reason": decision.reason,
        "decision_id": decision.id,
    }


def save_accepted_decision(
    db,
    email: dict,
    ticket_id: int,
    ai_result: dict | None = None,
) -> dict:
    message_id = email.get("gmail_message_id")

    if not message_id:
        return {
            "saved": False,
            "reason": "Missing Gmail message id"
        }

    decision = (
        db.query(GmailProcessingDecision)
        .filter(GmailProcessingDecision.gmail_message_id == message_id)
        .first()
    )

    if not decision:
        decision = GmailProcessingDecision(gmail_message_id=message_id)
        db.add(decision)

    decision.decision = ACCEPTED
    decision.reason = "Accepted for processing"
    decision.ticket_id = ticket_id
    decision.subject = email.get("subject")
    decision.sender = email.get("sender")
    decision.body = email.get("body")
    decision.snippet = email.get("snippet")
    decision.internal_date = email.get("internal_date")
    decision.classification_json = json.dumps(ai_result or {})
    decision.welcome_sent_at = email.get("welcome_sent_at")

    db.commit()
    db.refresh(decision)

    return {
        "saved": True,
        "gmail_message_id": message_id,
        "decision": decision.decision,
        "reason": decision.reason,
        "ticket_id": decision.ticket_id,
        "decision_id": decision.id,
    }


def processed_email_audit(db, decision_filter: str | None = None, limit: int = 100):
    query = db.query(GmailProcessingDecision)

    if decision_filter:
        query = query.filter(GmailProcessingDecision.decision == decision_filter)

    decisions = (
        query
        .order_by(GmailProcessingDecision.updated_at.desc())
        .limit(limit)
        .all()
    )

    ticket_ids = [
        decision.ticket_id for decision in decisions
        if decision.ticket_id
    ]
    tickets = {
        ticket.id: ticket
        for ticket in (
            db.query(Ticket)
            .filter(Ticket.id.in_(ticket_ids))
            .all()
            if ticket_ids
            else []
        )
    }
    employee_ids = [
        ticket.assigned_employee_id for ticket in tickets.values()
        if ticket.assigned_employee_id
    ]
    employees = {
        employee.id: employee
        for employee in (
            db.query(Employee)
            .filter(Employee.id.in_(employee_ids))
            .all()
            if employee_ids
            else []
        )
    }

    return {
        "count": len(decisions),
        "items": [
            _processed_email_row(decision, tickets, employees)
            for decision in decisions
        ],
    }


def _processed_email_row(decision, tickets, employees):
    ticket = tickets.get(decision.ticket_id)
    employee = employees.get(ticket.assigned_employee_id) if ticket else None

    try:
        classification = json.loads(decision.classification_json or "{}")
    except json.JSONDecodeError:
        classification = {}

    return {
        "gmail_message_id": decision.gmail_message_id,
        "email": {
            "subject": decision.subject,
            "sender": decision.sender,
            "body": decision.body,
            "snippet": decision.snippet,
            "internal_date": decision.internal_date,
        },
        "ai_processing": {
            "decision": decision.decision,
            "reason": decision.reason,
            "classification": classification,
            "welcome_sent_at": decision.welcome_sent_at,
            "processed_at": decision.updated_at,
        },
        "ticket": _ticket_row(ticket),
        "assignment": _assignment_row(ticket, employee),
    }


def _ticket_row(ticket):
    if not ticket:
        return None

    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "intent": ticket.intent,
        "department": ticket.department,
        "priority": ticket.priority,
        "customer_name": ticket.customer_name,
        "origin": ticket.origin,
        "destination": ticket.destination,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "assigned_at": ticket.assigned_at,
        "first_response_at": ticket.first_response_at,
        "closed_at": ticket.closed_at,
        "sla_due_at": ticket.sla_due_at,
        "sla_breached": ticket.sla_breached,
    }


def _assignment_row(ticket, employee):
    if not ticket:
        return {
            "assigned": False,
            "assigned_employee": None,
        }

    return {
        "assigned": bool(ticket.assigned_employee_id),
        "assigned_employee_id": ticket.assigned_employee_id,
        "assigned_employee": {
            "employee_id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "role": employee.role,
        } if employee else None,
        "ticket_status": ticket.status,
    }
