import json

from fastmcp import FastMCP

from app.services.classification_service import (
    INTENT_TO_DEPARTMENT,
    department_for_intent,
    normalize_priority,
)
from app.mcp.helpers import (
    mcp_classify_freight_email,
    mcp_dashboard,
    mcp_employee_metrics,
    mcp_fetch_gmail_unread,
    mcp_get_ticket,
    mcp_employee_dashboard,
    mcp_list_employees,
    mcp_list_tickets,
    mcp_process_email,
    mcp_process_gmail_unread,
    mcp_review_queue,
    mcp_smart_assign_preview,
    mcp_sla_dashboard,
    mcp_update_ticket_status,
)

mcp = FastMCP("freight-tools")


@mcp.tool()
def classify_department(intent: str) -> dict:
    return {"department": department_for_intent(intent)}


@mcp.tool()
def calculate_priority(priority: str) -> dict:
    return {"priority": normalize_priority(priority)}


@mcp.tool()
def classify_freight_email(
    email_body: str,
    subject: str | None = None,
    force_rule_based: bool = False,
) -> dict:
    """Classify freight email content. Uses Anthropic when configured, else rule-based."""
    return mcp_classify_freight_email(email_body, subject, force_rule_based)


@mcp.tool()
def process_email(subject: str, sender: str, body: str) -> dict:
    """Classify an email and create a ticket with smart assignment."""
    return mcp_process_email(subject, sender, body)


@mcp.tool()
def list_tickets(
    status_filter: str | None = None,
    department: str | None = None,
) -> dict:
    """List tickets with optional status (e.g. NEW) and department filters."""
    return mcp_list_tickets(status_filter, department)


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Get ticket details and lifecycle events."""
    return mcp_get_ticket(ticket_id)


@mcp.tool()
def update_ticket_status(
    ticket_id: int,
    employee_id: int,
    status: str,
    note: str | None = None,
) -> dict:
    """Update ticket status (NEW, ASSIGNED, IN_PROGRESS, WAITING_CUSTOMER, ESCALATED, CLOSED)."""
    return mcp_update_ticket_status(ticket_id, employee_id, status, note)


@mcp.tool()
def get_dashboard() -> dict:
    """Operational dashboard summary and recent tickets."""
    return mcp_dashboard()


@mcp.tool()
def get_employee_metrics() -> dict:
    """Per-employee assigned and closed ticket metrics."""
    return mcp_employee_metrics()


@mcp.tool()
def get_employee_dashboard() -> dict:
    """Employee workload, capacity, department, and recent-ticket dashboard."""
    return mcp_employee_dashboard()


@mcp.tool()
def get_sla_dashboard() -> dict:
    """SLA breach and at-risk ticket dashboard."""
    return mcp_sla_dashboard()


@mcp.tool()
def get_review_queue() -> dict:
    """Gmail messages saved for human review or rejected with reasons."""
    return mcp_review_queue()


@mcp.tool()
def list_employees() -> dict:
    """List employees ordered by department and workload."""
    return mcp_list_employees()


@mcp.tool()
def smart_assign_preview(department: str) -> dict:
    """Preview which active employee would receive the next ticket."""
    return mcp_smart_assign_preview(department)


@mcp.tool()
def fetch_gmail_unread(
    from_email: str | None = None,
    max_results: int = 10,
) -> dict:
    """Fetch unread emails from Gmail (or mock inbox when unavailable)."""
    return mcp_fetch_gmail_unread(from_email, max_results)


@mcp.tool()
def process_gmail_unread(
    from_email: str | None = None,
    max_results: int = 10,
) -> dict:
    """Classify unread emails, skip non-freight, and create tickets."""
    return mcp_process_gmail_unread(from_email, max_results)


@mcp.resource("freight://routing-rules")
def routing_rules_resource() -> str:
    return json.dumps(
        {
            "intent_to_department": INTENT_TO_DEPARTMENT,
            "freight_departments": [
                "sales",
                "operations",
                "finance",
                "customs",
                "support",
            ],
        },
        indent=2,
    )


@mcp.resource("freight://ticket-statuses")
def ticket_statuses_resource() -> str:
    return json.dumps(
        [
            "NEW",
            "ASSIGNED",
            "IN_PROGRESS",
            "WAITING_CUSTOMER",
            "ESCALATED",
            "CLOSED",
        ],
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
