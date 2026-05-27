from types import SimpleNamespace

from fastapi import HTTPException

from app.db.session import SessionLocal
from app.services.gmail_decision_service import (
    save_accepted_decision,
    save_not_accepted_decision,
    save_review_required_decision,
    split_unchecked_emails,
)
from app.models.employee import Employee
from app.models.ticket_event import TicketEvent
from app.schemas import ProcessEmailRequest, TicketStatus
from app.services.assignment_service import smart_assign
from app.services.gmail_factory import gmail_service_type, resolve_gmail_service
from app.agents.freight_agent import classify_email, is_freight_email
from app.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_status,
)
from app.utils.analytics import dashboard_metrics, employee_dashboard, employee_metrics, sla_dashboard

AUTO_PROCESS_CONFIDENCE_THRESHOLD = 0.7


def db_session():
    return SessionLocal()


def ticket_to_dict(ticket) -> dict:
    return {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "sender": ticket.sender,
        "intent": ticket.intent,
        "department": ticket.department,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_employee_id": ticket.assigned_employee_id,
        "customer_name": ticket.customer_name,
        "origin": ticket.origin,
        "destination": ticket.destination,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "assigned_at": ticket.assigned_at.isoformat() if ticket.assigned_at else None,
        "first_response_at": (
            ticket.first_response_at.isoformat() if ticket.first_response_at else None
        ),
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
    }


def employee_to_dict(employee) -> dict:
    return {
        "id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "department": employee.department,
        "role": employee.role,
        "is_active": employee.is_active,
        "current_workload": employee.current_workload,
    }


def http_error_to_dict(exc: HTTPException) -> dict:
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }


def mcp_process_email(subject: str, sender: str, body: str) -> dict:
    db = db_session()

    try:
        payload = ProcessEmailRequest(
            subject=subject,
            sender=sender,
            body=body,
        )
        ai_result = classify_email(payload.body, subject=payload.subject)
        ticket = create_ticket(db, payload, ai_result)
        return {
            "success": True,
            "classification": ai_result,
            "ticket": ticket_to_dict(ticket),
        }
    except HTTPException as exc:
        return {"success": False, **http_error_to_dict(exc)}
    except KeyError as exc:
        return {
            "success": False,
            "error": f"AI result missing required field: {exc}",
            "status_code": 400,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to process email: {exc}",
            "status_code": 500,
        }
    finally:
        db.close()


def mcp_list_tickets(
    status_filter: str | None = None,
    department: str | None = None,
) -> dict:
    db = db_session()

    try:
        tickets = list_tickets(db, status_filter, department)
        return {
            "count": len(tickets),
            "tickets": [ticket_to_dict(ticket) for ticket in tickets],
        }
    finally:
        db.close()


def mcp_get_ticket(ticket_id: int) -> dict:
    db = db_session()

    try:
        ticket = get_ticket(db, ticket_id)
        events = (
            db.query(TicketEvent)
            .filter(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.timestamp.asc())
            .all()
        )

        return {
            "ticket": ticket_to_dict(ticket),
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "old_status": event.old_status,
                    "new_status": event.new_status,
                    "employee_id": event.employee_id,
                    "note": event.note,
                    "timestamp": event.timestamp.isoformat()
                    if event.timestamp
                    else None,
                }
                for event in events
            ],
        }
    except HTTPException as exc:
        return http_error_to_dict(exc)
    finally:
        db.close()


def mcp_update_ticket_status(
    ticket_id: int,
    employee_id: int,
    status: str,
    note: str | None = None,
) -> dict:
    db = db_session()

    try:
        normalized_status = status.strip().upper()
        ticket_status = TicketStatus(normalized_status)
        ticket = update_ticket_status(
            db,
            ticket_id,
            employee_id,
            ticket_status,
            note,
        )
        return {
            "success": True,
            "ticket_id": ticket.id,
            "new_status": ticket.status,
        }
    except HTTPException as exc:
        return {"success": False, **http_error_to_dict(exc)}
    finally:
        db.close()


def mcp_dashboard() -> dict:
    db = db_session()

    try:
        recent = list_tickets(db)[:10]
        return {
            "summary": dashboard_metrics(db),
            "recent_tickets": [ticket_to_dict(ticket) for ticket in recent],
        }
    finally:
        db.close()


def mcp_employee_metrics() -> dict:
    db = db_session()

    try:
        return {"employees": employee_metrics(db)}
    finally:
        db.close()


def mcp_employee_dashboard() -> dict:
    db = db_session()

    try:
        return employee_dashboard(db)
    finally:
        db.close()


def mcp_sla_dashboard() -> dict:
    db = db_session()

    try:
        return sla_dashboard(db)
    finally:
        db.close()


def mcp_review_queue() -> dict:
    from app.models.gmail_processing_decision import GmailProcessingDecision

    db = db_session()

    try:
        decisions = (
            db.query(GmailProcessingDecision)
            .filter(GmailProcessingDecision.decision.in_(["not_accepted", "review_required"]))
            .order_by(GmailProcessingDecision.updated_at.desc())
            .all()
        )

        return {
            "count": len(decisions),
            "items": [
                {
                    "id": decision.id,
                    "gmail_message_id": decision.gmail_message_id,
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "subject": decision.subject,
                    "sender": decision.sender,
                    "ticket_id": decision.ticket_id,
                    "classification_json": decision.classification_json,
                    "created_at": decision.created_at.isoformat()
                    if decision.created_at
                    else None,
                    "updated_at": decision.updated_at.isoformat()
                    if decision.updated_at
                    else None,
                }
                for decision in decisions
            ],
        }
    finally:
        db.close()


def mcp_list_employees() -> dict:
    db = db_session()

    try:
        employees = (
            db.query(Employee)
            .order_by(Employee.department.asc(), Employee.current_workload.asc())
            .all()
        )
        return {
            "count": len(employees),
            "employees": [employee_to_dict(employee) for employee in employees],
        }
    finally:
        db.close()


def mcp_smart_assign_preview(department: str) -> dict:
    db = db_session()

    try:
        employee = smart_assign(db, department)
        return {
            "department": department,
            "assigned_employee": employee_to_dict(employee) if employee else None,
        }
    finally:
        db.close()


def mcp_classify_freight_email(
    email_body: str,
    subject: str | None = None,
    force_rule_based: bool = False,
) -> dict:
    from app.agents.freight_agent import rule_based_classification_for_email

    if force_rule_based:
        result = rule_based_classification_for_email(email_body, subject)
    else:
        result = classify_email(email_body, subject=subject)

    return {
        "classification": result,
        "is_freight": is_freight_email(result),
    }


def mcp_fetch_gmail_unread(
    from_email: str | None = None,
    max_results: int = 10,
) -> dict:
    service = resolve_gmail_service()
    db = db_session()
    emails = service.fetch_unread_emails_filtered(from_email, max_results=max_results)

    try:
        unchecked, previously_processed = split_unchecked_emails(db, emails)

        return {
            "service": gmail_service_type(service),
            "query": service.build_query(from_email),
            "count": len(unchecked),
            "ignored_count": len(previously_processed),
            "emails": unchecked,
            "previously_processed": previously_processed,
        }
    finally:
        db.close()


def mcp_process_gmail_unread(
    from_email: str | None = None,
    max_results: int = 10,
) -> dict:
    service = resolve_gmail_service()
    emails = service.fetch_unread_emails_filtered(from_email, max_results=max_results)
    db = db_session()

    try:
        emails, previously_processed = split_unchecked_emails(db, emails)
        processed = [
            {
                "gmail_message_id": email.get("gmail_message_id"),
                "skipped": True,
                "already_saved": True,
                "reason": email.get("reason"),
                "decision": email.get("decision"),
                "ticket_id": email.get("ticket_id"),
            }
            for email in previously_processed
        ]

        for email in emails:
            try:
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
                    processed.append(
                        {
                            "gmail_message_id": email.get("gmail_message_id"),
                            "skipped": True,
                            "reason": "Email not classified as freight-related",
                            "ai_result": ai_result,
                            "decision_result": decision_result,
                        }
                    )
                    continue

                if float(ai_result.get("confidence_score") or 0) < AUTO_PROCESS_CONFIDENCE_THRESHOLD:
                    decision_result = save_review_required_decision(
                        db,
                        email,
                        "Low AI confidence; needs human review",
                        ai_result,
                    )
                    processed.append(
                        {
                            "gmail_message_id": email.get("gmail_message_id"),
                            "skipped": True,
                            "reason": "Low AI confidence; needs human review",
                            "ai_result": ai_result,
                            "decision_result": decision_result,
                        }
                    )
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
                processed.append(
                    {
                        "gmail_message_id": email.get("gmail_message_id"),
                        "ticket_id": ticket.id,
                        "assigned_employee_id": ticket.assigned_employee_id,
                        "classification": ai_result,
                        "decision_result": decision_result,
                    }
                )
            except Exception as exc:
                processed.append(
                    {
                        "gmail_message_id": email.get("gmail_message_id"),
                        "error": str(exc),
                    }
                )

        return {
            "service": gmail_service_type(service),
            "processed_count": len(processed),
            "results": processed,
        }
    finally:
        db.close()
