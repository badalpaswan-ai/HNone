from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.access import resolve_access_scope
from app.api.deps import get_db
from app.core.security import ROLE_MANAGER, require_roles
from app.services.gmail_decision_service import (
    processed_email_audit,
    split_unchecked_emails,
)
from app.services.gmail_auto_processor import process_unread_gmail_messages
from app.services.gmail_factory import gmail_service_type, resolve_gmail_service

router = APIRouter()


@router.get(
    "/gmail/unread",
    tags=["Gmail"],
    summary="Preview unread Gmail messages",
    dependencies=[Depends(require_roles(ROLE_MANAGER))]
)
def fetch_unread(
    from_email: str | None = None,
    max_results: int = 10,
    db: Session = Depends(get_db)
):
    svc = resolve_gmail_service()
    emails = svc.fetch_unread_emails_filtered(from_email, max_results=max_results)
    unchecked, previously_processed = split_unchecked_emails(db, emails)

    return {
        "count": len(unchecked),
        "ignored_count": len(previously_processed),
        "emails": unchecked,
        "previously_processed": previously_processed,
    }


@router.post(
    "/gmail/process-unread",
    tags=["Gmail"],
    summary="Process unread Gmail messages into tickets",
)
def process_unread(
    from_email: str | None = None,
    max_results: int = 10,
    user=Depends(require_roles(ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    result = process_unread_gmail_messages(
        db,
        from_email=from_email,
        max_results=max_results,
        department=None if scope.full_access else scope.department,
    )
    return result["results"]


@router.get(
    "/gmail/processed",
    tags=["Gmail"],
    summary="Audit processed Gmail decisions",
)
def processed_emails(
    decision: str | None = None,
    limit: int = 100,
    user=Depends(require_roles(ROLE_MANAGER)),
    db: Session = Depends(get_db)
):
    scope = resolve_access_scope(db, user)
    safe_limit = min(max(limit, 1), 500)
    rows = processed_email_audit(db, decision, safe_limit)

    if scope.full_access:
        return rows

    return [
        row for row in rows
        if row.get("ticket")
        and row["ticket"].get("department") == scope.department
    ]


@router.get(
    "/gmail/query",
    tags=["Gmail"],
    summary="Preview Gmail query and matching messages",
    dependencies=[Depends(require_roles(ROLE_MANAGER))]
)
def gmail_query(from_email: str | None = None, max_results: int = 10):
    svc = resolve_gmail_service()
    query = svc.build_query(from_email)
    emails = svc.fetch_unread_emails_filtered(from_email, max_results=max_results)
    service_type = gmail_service_type(svc)

    return {
        "service": service_type,
        "query": query,
        "count": len(emails),
        "emails": emails
    }
