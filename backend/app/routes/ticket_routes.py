from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal

from app.models.ticket import Ticket

from app.agents.freight_agent import classify_email

from app.services.ticket_service import (
    create_ticket,
    update_ticket_status
)

from app.utils.analytics import employee_metrics

router = APIRouter()

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

@router.post("/process-email")
def process_email(
    payload: dict,
    db: Session = Depends(get_db)
):
    # basic validation
    body = payload.get("body")

    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: body"
        )

    try:
        ai_result = classify_email(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI classification failed: {exc}"
        )

    try:
        ticket = create_ticket(
            db,
            payload,
            ai_result
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing ticket field: {exc}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {exc}"
        )

    return {
        "ticket_id": ticket.id,
        "intent": ticket.intent,
        "department": ticket.department,
        "priority": ticket.priority,
        "assigned_employee_id": ticket.assigned_employee_id,
        "status": ticket.status
    }

@router.put("/tickets/{ticket_id}/status")
def update_status(
    ticket_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):

    ticket = update_ticket_status(
        db,
        ticket_id,
        payload["employee_id"],
        payload["status"]
    )

    return {
        "ticket_id": ticket.id,
        "new_status": ticket.status
    }

@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db)
):

    tickets = db.query(Ticket).all()

    response = []

    for ticket in tickets:

        response.append({
            "ticket_id": ticket.id,
            "intent": ticket.intent,
            "department": ticket.department,
            "priority": ticket.priority,
            "status": ticket.status,
            "employee_id": ticket.assigned_employee_id
        })

    return response

@router.get("/employee-metrics")
def metrics(
    db: Session = Depends(get_db)
):

    return employee_metrics(db)