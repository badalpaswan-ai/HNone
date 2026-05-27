from datetime import datetime

from app.models.gmail_processing_decision import GmailProcessingDecision
from app.models.ticket import Ticket
from app.models.employee import Employee

ACTIVE_STATUSES = {
    "NEW",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_CUSTOMER",
    "ESCALATED"
}


def employee_metrics(db):

    employees = db.query(Employee).all()

    response = []

    for employee in employees:

        tickets = (
            db.query(Ticket)
            .filter(
                Ticket.assigned_employee_id == employee.id
            )
            .all()
        )

        assigned = len(tickets)

        closed = len([
            t for t in tickets
            if t.status == "CLOSED"
        ])

        response.append({
            "employee": employee.name,
            "department": employee.department,
            "assigned_tickets": assigned,
            "closed_tickets": closed,
            "current_workload": employee.current_workload
        })

    return response


def admin_dashboard(db):
    now = datetime.utcnow()
    employees = db.query(Employee).all()
    tickets = db.query(Ticket).all()
    mail_decisions = db.query(GmailProcessingDecision).all()

    active_tickets = [
        ticket for ticket in tickets
        if ticket.status in ACTIVE_STATUSES
    ]
    assigned_tickets = [
        ticket for ticket in tickets
        if ticket.assigned_employee_id is not None
    ]
    closed_tickets = [
        ticket for ticket in tickets
        if ticket.status == "CLOSED"
    ]
    breached_tickets = [
        ticket for ticket in active_tickets
        if ticket.sla_due_at and ticket.sla_due_at < now
    ]
    at_risk_tickets = [
        ticket for ticket in active_tickets
        if (
            ticket.sla_due_at
            and ticket.sla_due_at >= now
            and (ticket.sla_due_at - now).total_seconds() <= 4 * 60 * 60
        )
    ]

    accepted_mails = [
        decision for decision in mail_decisions
        if decision.decision == "accepted"
    ]
    rejected_mails = [
        decision for decision in mail_decisions
        if decision.decision == "not_accepted"
    ]
    review_mails = [
        decision for decision in mail_decisions
        if decision.decision == "review_required"
    ]

    employee_rows = [
        _admin_employee_performance_row(employee, tickets, now)
        for employee in employees
    ]
    employee_rows = sorted(
        employee_rows,
        key=lambda row: row["performance_score"],
        reverse=True,
    )

    scored_employee_rows = [
        row for row in employee_rows
        if row["total_assigned"] > 0 or row["current_workload"] > 0
    ]

    average_score = _safe_average([
        row["performance_score"]
        for row in scored_employee_rows
    ])
    below_average = [
        row for row in scored_employee_rows
        if row["performance_score"] < average_score
    ]

    return {
        "summary": {
            "total_mail_received": len(mail_decisions),
            "accepted_mail_count": len(accepted_mails),
            "rejected_mail_count": len(rejected_mails),
            "review_required_mail_count": len(review_mails),
            "total_tickets": len(tickets),
            "total_assigned": len(assigned_tickets),
            "total_unassigned": len(tickets) - len(assigned_tickets),
            "active_tickets": len(active_tickets),
            "closed_tickets": len(closed_tickets),
            "breached_tickets": len(breached_tickets),
            "at_risk_tickets": len(at_risk_tickets),
            "total_employees": len(employees),
            "active_employees": len([
                employee for employee in employees
                if employee.is_active
            ]),
            "available_employees": len([
                employee for employee in employees
                if employee.is_available
            ]),
            "total_capacity": sum(
                employee.max_workload or 5
                for employee in employees
                if employee.is_active and employee.is_available
            ),
            "total_current_workload": sum(
                employee.current_workload or 0
                for employee in employees
            ),
            "average_employee_score": round(average_score, 2),
        },
        "mail_stats": {
            "by_decision": _count_by(mail_decisions, "decision"),
            "latest_decisions": [
                {
                    "gmail_message_id": decision.gmail_message_id,
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "subject": decision.subject,
                    "sender": decision.sender,
                    "ticket_id": decision.ticket_id,
                    "updated_at": decision.updated_at,
                }
                for decision in sorted(
                    mail_decisions,
                    key=lambda decision: decision.updated_at or decision.created_at,
                    reverse=True,
                )[:10]
            ],
        },
        "ticket_stats": {
            "by_status": _count_by(tickets, "status"),
            "by_priority": _count_by(tickets, "priority"),
            "by_department": _department_ticket_stats(tickets, employees, now),
        },
        "employee_performance": {
            "star_performers": employee_rows[:5],
            "below_average_performers": below_average,
            "all_employees": employee_rows,
        },
        "operational_alerts": {
            "breached_tickets": [_ticket_sla_row(ticket, now) for ticket in breached_tickets],
            "at_risk_tickets": [_ticket_sla_row(ticket, now) for ticket in at_risk_tickets],
            "overloaded_employees": [
                row for row in employee_rows
                if row["current_workload"] >= row["max_workload"]
            ],
            "unavailable_employees_with_work": [
                row for row in employee_rows
                if not row["is_available"] and row["current_workload"] > 0
            ],
        },
    }


def _admin_employee_performance_row(employee, tickets, now):
    employee_tickets = [
        ticket for ticket in tickets
        if ticket.assigned_employee_id == employee.id
    ]
    active = [
        ticket for ticket in employee_tickets
        if ticket.status in ACTIVE_STATUSES
    ]
    closed = [
        ticket for ticket in employee_tickets
        if ticket.status == "CLOSED"
    ]
    breached = [
        ticket for ticket in active
        if ticket.sla_due_at and ticket.sla_due_at < now
    ]
    urgent_active = [
        ticket for ticket in active
        if ticket.priority == "URGENT"
    ]
    high_priority_active = [
        ticket for ticket in active
        if ticket.priority in {"HIGH", "URGENT"}
    ]

    workload = employee.current_workload or 0
    max_workload = employee.max_workload or 5
    capacity_used_percent = round((workload / max_workload) * 100, 2) if max_workload else 0
    close_rate = (len(closed) / len(employee_tickets)) if employee_tickets else 0
    breach_penalty = min(len(breached) * 10, 40)
    load_penalty = 10 if workload > max_workload else 0
    availability_bonus = 5 if employee.is_available and employee.is_active else 0
    performance_score = round(
        max(
            0,
            min(
                100,
                50
                + (close_rate * 30)
                + availability_bonus
                + min(len(active), max_workload) * 2
                - breach_penalty
                - load_penalty,
            ),
        ),
        2,
    )

    return {
        "employee_id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "department": employee.department,
        "role": employee.role,
        "skills": employee.skills,
        "is_active": employee.is_active,
        "is_available": employee.is_available,
        "current_workload": workload,
        "max_workload": max_workload,
        "capacity_used_percent": capacity_used_percent,
        "capacity_remaining": max(max_workload - workload, 0),
        "total_assigned": len(employee_tickets),
        "active_tickets": len(active),
        "closed_tickets": len(closed),
        "urgent_active_tickets": len(urgent_active),
        "high_priority_active_tickets": len(high_priority_active),
        "breached_tickets": len(breached),
        "close_rate": round(close_rate, 2),
        "performance_score": performance_score,
    }


def _department_ticket_stats(tickets, employees, now):
    departments = {}

    for employee in employees:
        row = departments.setdefault(
            employee.department,
            {
                "department": employee.department,
                "employee_count": 0,
                "available_employee_count": 0,
                "total_capacity": 0,
                "current_workload": 0,
                "total_tickets": 0,
                "assigned_tickets": 0,
                "unassigned_tickets": 0,
                "active_tickets": 0,
                "closed_tickets": 0,
                "breached_tickets": 0,
            },
        )
        row["employee_count"] += 1
        row["available_employee_count"] += 1 if employee.is_available else 0
        row["total_capacity"] += employee.max_workload or 5
        row["current_workload"] += employee.current_workload or 0

    for ticket in tickets:
        row = departments.setdefault(
            ticket.department,
            {
                "department": ticket.department,
                "employee_count": 0,
                "available_employee_count": 0,
                "total_capacity": 0,
                "current_workload": 0,
                "total_tickets": 0,
                "assigned_tickets": 0,
                "unassigned_tickets": 0,
                "active_tickets": 0,
                "closed_tickets": 0,
                "breached_tickets": 0,
            },
        )
        row["total_tickets"] += 1
        row["assigned_tickets"] += 1 if ticket.assigned_employee_id else 0
        row["unassigned_tickets"] += 1 if not ticket.assigned_employee_id else 0
        row["active_tickets"] += 1 if ticket.status in ACTIVE_STATUSES else 0
        row["closed_tickets"] += 1 if ticket.status == "CLOSED" else 0
        row["breached_tickets"] += 1 if (
            ticket.status in ACTIVE_STATUSES
            and ticket.sla_due_at
            and ticket.sla_due_at < now
        ) else 0

    return sorted(
        departments.values(),
        key=lambda row: row["department"] or "",
    )


def _count_by(items, attr):
    counts = {}

    for item in items:
        key = getattr(item, attr) or "unknown"
        counts[key] = counts.get(key, 0) + 1

    return counts


def _safe_average(values):
    if not values:
        return 0

    return sum(values) / len(values)


def employee_dashboard(db):
    employees = (
        db.query(Employee)
        .order_by(Employee.department.asc(), Employee.current_workload.asc())
        .all()
    )
    tickets = db.query(Ticket).all()

    tickets_by_employee = {}
    unassigned_tickets = []

    for ticket in tickets:
        if ticket.assigned_employee_id is None:
            unassigned_tickets.append(ticket)
            continue

        tickets_by_employee.setdefault(ticket.assigned_employee_id, []).append(ticket)

    employee_rows = []
    departments = {}

    for employee in employees:
        employee_tickets = tickets_by_employee.get(employee.id, [])
        active_tickets = [
            ticket for ticket in employee_tickets
            if ticket.status in ACTIVE_STATUSES
        ]
        closed_tickets = [
            ticket for ticket in employee_tickets
            if ticket.status == "CLOSED"
        ]
        urgent_tickets = [
            ticket for ticket in active_tickets
            if ticket.priority == "URGENT"
        ]
        high_priority_tickets = [
            ticket for ticket in active_tickets
            if ticket.priority in {"HIGH", "URGENT"}
        ]
        recent_tickets = sorted(
            employee_tickets,
            key=lambda ticket: ticket.updated_at or ticket.created_at,
            reverse=True,
        )[:5]

        row = {
            "employee_id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "role": employee.role,
            "skills": employee.skills,
            "max_workload": employee.max_workload or 5,
            "is_available": employee.is_available,
            "is_active": employee.is_active,
            "current_workload": employee.current_workload,
            "capacity_remaining": max(
                (employee.max_workload or 5) - (employee.current_workload or 0),
                0,
            ),
            "total_assigned": len(employee_tickets),
            "active_tickets": len(active_tickets),
            "closed_tickets": len(closed_tickets),
            "urgent_tickets": len(urgent_tickets),
            "high_priority_tickets": len(high_priority_tickets),
            "recent_tickets": [
                {
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "customer_name": ticket.customer_name,
                    "updated_at": ticket.updated_at,
                    "created_at": ticket.created_at,
                }
                for ticket in recent_tickets
            ],
        }

        employee_rows.append(row)

        department = departments.setdefault(
            employee.department,
            {
                "department": employee.department,
                "employee_count": 0,
                "active_employee_count": 0,
                "current_workload": 0,
                "active_tickets": 0,
                "closed_tickets": 0,
                "urgent_tickets": 0,
            },
        )
        department["employee_count"] += 1
        department["active_employee_count"] += 1 if employee.is_active else 0
        department["available_employee_count"] = (
            department.get("available_employee_count", 0)
            + (1 if employee.is_available else 0)
        )
        department["total_capacity"] = (
            department.get("total_capacity", 0)
            + (employee.max_workload or 5)
        )
        department["current_workload"] += employee.current_workload or 0
        department["active_tickets"] += len(active_tickets)
        department["closed_tickets"] += len(closed_tickets)
        department["urgent_tickets"] += len(urgent_tickets)

    active_employees = [
        employee for employee in employees
        if employee.is_active
    ]
    active_ticket_count = sum(
        row["active_tickets"]
        for row in employee_rows
    )

    return {
        "summary": {
            "total_employees": len(employees),
            "active_employees": len(active_employees),
            "inactive_employees": len(employees) - len(active_employees),
            "total_current_workload": sum(
                employee.current_workload or 0
                for employee in employees
            ),
            "total_capacity": sum(
                employee.max_workload or 5
                for employee in employees
                if employee.is_active and employee.is_available
            ),
            "assigned_active_tickets": active_ticket_count,
            "unassigned_active_tickets": len([
                ticket for ticket in unassigned_tickets
                if ticket.status in ACTIVE_STATUSES
            ]),
            "closed_tickets": sum(
                row["closed_tickets"]
                for row in employee_rows
            ),
        },
        "departments": sorted(
            departments.values(),
            key=lambda department: department["department"],
        ),
        "employees": employee_rows,
    }


def individual_employee_dashboard(db, employee_id):
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        return None

    now = datetime.utcnow()
    employee_tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_employee_id == employee.id)
        .order_by(Ticket.updated_at.desc())
        .all()
    )

    active_tickets = [
        ticket for ticket in employee_tickets
        if ticket.status in ACTIVE_STATUSES
    ]
    closed_tickets = [
        ticket for ticket in employee_tickets
        if ticket.status == "CLOSED"
    ]
    breached_tickets = [
        ticket for ticket in active_tickets
        if ticket.sla_due_at and ticket.sla_due_at < now
    ]
    at_risk_tickets = [
        ticket for ticket in active_tickets
        if (
            ticket.sla_due_at
            and ticket.sla_due_at >= now
            and (ticket.sla_due_at - now).total_seconds() <= 4 * 60 * 60
        )
    ]

    by_status = {}
    by_priority = {}

    for ticket in employee_tickets:
        by_status[ticket.status] = by_status.get(ticket.status, 0) + 1
        by_priority[ticket.priority] = by_priority.get(ticket.priority, 0) + 1

    return {
        "employee": {
            "employee_id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "role": employee.role,
            "skills": employee.skills,
            "is_active": employee.is_active,
            "is_available": employee.is_available,
            "current_workload": employee.current_workload or 0,
            "max_workload": employee.max_workload or 5,
            "capacity_remaining": max(
                (employee.max_workload or 5) - (employee.current_workload or 0),
                0,
            ),
        },
        "summary": {
            "total_assigned": len(employee_tickets),
            "active_tickets": len(active_tickets),
            "closed_tickets": len(closed_tickets),
            "breached_tickets": len(breached_tickets),
            "at_risk_tickets": len(at_risk_tickets),
            "by_status": by_status,
            "by_priority": by_priority,
        },
        "active_tickets": [
            _employee_ticket_row(ticket, now)
            for ticket in active_tickets
        ],
        "breached_tickets": [
            _employee_ticket_row(ticket, now)
            for ticket in breached_tickets
        ],
        "at_risk_tickets": [
            _employee_ticket_row(ticket, now)
            for ticket in at_risk_tickets
        ],
        "recent_closed_tickets": [
            _employee_ticket_row(ticket, now)
            for ticket in closed_tickets[:10]
        ],
    }


def _employee_ticket_row(ticket, now):
    seconds_remaining = None

    if ticket.sla_due_at:
        seconds_remaining = int((ticket.sla_due_at - now).total_seconds())

    return {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "sender": ticket.sender,
        "customer_name": ticket.customer_name,
        "origin": ticket.origin,
        "destination": ticket.destination,
        "intent": ticket.intent,
        "department": ticket.department,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "assigned_at": ticket.assigned_at,
        "first_response_at": ticket.first_response_at,
        "closed_at": ticket.closed_at,
        "sla_due_at": ticket.sla_due_at,
        "seconds_remaining": seconds_remaining,
    }


def sla_dashboard(db):
    now = datetime.utcnow()
    tickets = db.query(Ticket).all()

    active_tickets = [
        ticket for ticket in tickets
        if ticket.status in ACTIVE_STATUSES
    ]
    breached = [
        ticket for ticket in active_tickets
        if ticket.sla_due_at and ticket.sla_due_at < now
    ]
    at_risk = [
        ticket for ticket in active_tickets
        if (
            ticket.sla_due_at
            and ticket.sla_due_at >= now
            and (ticket.sla_due_at - now).total_seconds() <= 4 * 60 * 60
        )
    ]

    by_department = {}
    for ticket in active_tickets:
        row = by_department.setdefault(
            ticket.department,
            {
                "department": ticket.department,
                "active_tickets": 0,
                "breached": 0,
                "at_risk": 0,
            },
        )
        row["active_tickets"] += 1

        if ticket in breached:
            row["breached"] += 1

        if ticket in at_risk:
            row["at_risk"] += 1

    return {
        "summary": {
            "active_tickets": len(active_tickets),
            "breached": len(breached),
            "at_risk": len(at_risk),
            "healthy": len(active_tickets) - len(breached) - len(at_risk),
        },
        "by_department": sorted(
            by_department.values(),
            key=lambda row: row["department"] or "",
        ),
        "breached_tickets": [_ticket_sla_row(ticket, now) for ticket in breached],
        "at_risk_tickets": [_ticket_sla_row(ticket, now) for ticket in at_risk],
    }


def _ticket_sla_row(ticket, now):
    seconds_remaining = None

    if ticket.sla_due_at:
        seconds_remaining = int((ticket.sla_due_at - now).total_seconds())

    return {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "department": ticket.department,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_employee_id": ticket.assigned_employee_id,
        "sla_due_at": ticket.sla_due_at,
        "seconds_remaining": seconds_remaining,
    }


def dashboard_metrics(db):
    tickets = db.query(Ticket).all()

    by_status = {}
    by_priority = {}
    by_department = {}

    for ticket in tickets:
        by_status[ticket.status] = by_status.get(ticket.status, 0) + 1
        by_priority[ticket.priority] = by_priority.get(ticket.priority, 0) + 1
        by_department[ticket.department] = by_department.get(ticket.department, 0) + 1

    active_tickets = [
        ticket for ticket in tickets
        if ticket.status in ACTIVE_STATUSES
    ]

    return {
        "total_tickets": len(tickets),
        "active_tickets": len(active_tickets),
        "closed_tickets": by_status.get("CLOSED", 0),
        "unassigned_tickets": len([
            ticket for ticket in tickets
            if ticket.assigned_employee_id is None
        ]),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_department": by_department
    }
