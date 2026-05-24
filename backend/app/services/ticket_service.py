from datetime import datetime

from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent

from app.services.assignment_service import smart_assign

def create_ticket(db, payload, ai_result):

    employee = smart_assign(
        db,
        ai_result["department"]
    )

    ticket = Ticket(
        subject=payload["subject"],
        sender=payload["sender"],
        body=payload["body"],

        intent=ai_result["intent"],

        department=ai_result["department"],

        priority=ai_result["priority"],

        status="ASSIGNED",

        assigned_employee_id=employee.id,

        assigned_at=datetime.utcnow()
    )

    db.add(ticket)

    db.commit()

    db.refresh(ticket)

    event = TicketEvent(
        ticket_id=ticket.id,
        employee_id=employee.id,
        event_type="ASSIGNED",
        new_status="ASSIGNED"
    )

    db.add(event)

    db.commit()

    return ticket


def update_ticket_status(
    db,
    ticket_id,
    employee_id,
    status
):

    ticket = (
        db.query(Ticket)
        .filter(
            Ticket.id == ticket_id
        )
        .first()
    )

    old_status = ticket.status

    ticket.status = status

    if status == "IN_PROGRESS":

        if not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()

    if status == "CLOSED":
        ticket.closed_at = datetime.utcnow()

    db.commit()

    event = TicketEvent(
        ticket_id=ticket.id,
        employee_id=employee_id,
        event_type="STATUS_CHANGE",
        old_status=old_status,
        new_status=status
    )

    db.add(event)

    db.commit()

    return ticket