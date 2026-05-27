from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
import streamlit as st


DEFAULT_API_BASE = "http://127.0.0.1:8000"
TICKET_STATUSES = [
    "NEW",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_CUSTOMER",
    "ESCALATED",
    "CLOSED",
]
DEPARTMENTS = ["sales", "operations", "finance", "customs", "support"]


st.set_page_config(
    page_title="HNOne Operations",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state() -> None:
    defaults = {
        "api_base": DEFAULT_API_BASE,
        "token": None,
        "user": None,
        "me": None,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def api_headers() -> dict[str, str]:
    token = st.session_state.get("token")

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def request_api(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    auth: bool = True,
) -> Any:
    base = st.session_state["api_base"].rstrip("/")
    headers = api_headers() if auth else {}
    response = requests.request(
        method,
        f"{base}{path}",
        json=json,
        params=_clean_params(params or {}),
        headers=headers,
        timeout=30,
    )

    if response.status_code >= 400:
        detail = _response_detail(response)
        raise RuntimeError(f"{response.status_code}: {detail}")

    if not response.content:
        return None

    return response.json()


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if value not in (None, "", "All")
    }


def _response_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    return payload.get("detail", payload)


def login(username: str, password: str) -> None:
    payload = request_api(
        "POST",
        "/auth/login",
        json={"username": username, "password": password},
        auth=False,
    )
    st.session_state["token"] = payload["access_token"]
    st.session_state["user"] = {
        "username": payload["username"],
        "role": payload["role"],
    }
    st.session_state["me"] = request_api("GET", "/auth/me")


def logout() -> None:
    st.session_state["token"] = None
    st.session_state["user"] = None
    st.session_state["me"] = None


def current_role() -> str | None:
    user = st.session_state.get("user") or {}
    return user.get("role")


def current_employee_id() -> int | None:
    me = st.session_state.get("me") or {}
    employee = me.get("employee") or {}
    return employee.get("employee_id")


def render_login() -> None:
    st.title("HNOne Operations")
    st.caption("Internal freight email triage, assignment, and SLA workspace.")

    with st.sidebar:
        st.session_state["api_base"] = st.text_input(
            "API base URL",
            value=st.session_state["api_base"],
        )

    col1, col2 = st.columns([0.9, 1.1])

    with col1:
        with st.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username", value="system")
            password = st.text_input("Password", type="password", value="system123")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            try:
                login(username, password)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    with col2:
        st.subheader("Demo users")
        st.dataframe(
            [
                {"role": "system", "username": "system", "password": "system123"},
                {"role": "manager", "username": "manager", "password": "manager123"},
                {"role": "employee", "username": "employee", "password": "employee123"},
            ],
            hide_index=True,
            use_container_width=True,
        )
        st.info(
            "Data is scoped by backend role: system sees all data, managers see "
            "department data, and employees see their assigned work."
        )


def render_shell() -> None:
    role = current_role()
    me = st.session_state.get("me") or {}

    with st.sidebar:
        st.title("HNOne")
        st.caption(st.session_state["api_base"])

        profile = me.get("employee") or {}
        st.write(f"Signed in as `{st.session_state['user']['username']}`")
        st.write(f"Role: `{role}`")

        if profile:
            st.write(f"Employee: `{profile.get('name')}`")
            st.write(f"Department: `{profile.get('department')}`")

        nav_items = ["Overview", "Tickets", "Notifications"]

        if role in {"system", "manager"}:
            nav_items.extend(["Employees", "Gmail", "Process Email"])

        if role == "system":
            nav_items.append("System")

        selected = st.radio("Navigation", nav_items, label_visibility="collapsed")

        if st.button("Sign out", use_container_width=True):
            logout()
            st.rerun()

    if selected == "Overview":
        render_overview()
    elif selected == "Tickets":
        render_tickets()
    elif selected == "Notifications":
        render_notifications()
    elif selected == "Employees":
        render_employees()
    elif selected == "Gmail":
        render_gmail()
    elif selected == "Process Email":
        render_process_email()
    elif selected == "System":
        render_system()


def render_overview() -> None:
    st.title("Operations Overview")

    try:
        dashboard = request_api("GET", "/dashboard")
        sla = request_api("GET", "/sla-dashboard")
        metrics = request_api("GET", "/employee-metrics")
    except Exception as exc:
        st.error(str(exc))
        return

    summary = dashboard.get("summary", {}) if isinstance(dashboard, dict) else {}
    cols = st.columns(4)
    metric_items = [
        ("Total tickets", summary.get("total_tickets", summary.get("total_mail_received", 0))),
        ("Active", summary.get("active_tickets", summary.get("active_mail_tickets", 0))),
        ("Closed", summary.get("closed_tickets", 0)),
        ("Assigned", summary.get("assigned_tickets", summary.get("assigned_mail_tickets", 0))),
    ]

    for col, (label, value) in zip(cols, metric_items):
        col.metric(label, value)

    left, right = st.columns([1.2, 0.8])

    with left:
        st.subheader("Recent tickets")
        st.dataframe(
            _ticket_rows(dashboard.get("recent_tickets", [])),
            hide_index=True,
            use_container_width=True,
        )

    with right:
        st.subheader("SLA")
        st.json(sla.get("summary", sla), expanded=False)

    st.subheader("Employee metrics")
    st.dataframe(metrics, hide_index=True, use_container_width=True)


def render_tickets() -> None:
    st.title("Tickets")

    filters = st.columns([1, 1, 2])
    status_filter = filters[0].selectbox("Status", ["All", *TICKET_STATUSES])
    department = filters[1].selectbox("Department", ["All", *DEPARTMENTS])

    try:
        tickets = request_api(
            "GET",
            "/tickets",
            params={
                "status_filter": status_filter,
                "department": department,
            },
        )
    except Exception as exc:
        st.error(str(exc))
        return

    st.dataframe(_ticket_rows(tickets), hide_index=True, use_container_width=True)

    if not tickets:
        st.info("No tickets found for the selected filters.")
        return

    ticket_options = {
        f"#{ticket['id']} - {ticket.get('subject', 'No subject')}": ticket["id"]
        for ticket in tickets
    }
    selected_label = st.selectbox("Open ticket", list(ticket_options.keys()))
    ticket_id = ticket_options[selected_label]

    try:
        detail = request_api("GET", f"/tickets/{ticket_id}")
    except Exception as exc:
        st.error(str(exc))
        return

    ticket = detail.get("ticket", {})
    events = detail.get("events", [])

    left, right = st.columns([1.2, 0.8])

    with left:
        st.subheader(ticket.get("subject", "Ticket detail"))
        st.markdown("**Email message**")
        st.text_area(
            "Email message",
            value=ticket.get("body") or "No email message available.",
            height=220,
            label_visibility="collapsed",
            disabled=True,
        )
        st.json(
            {
                "sender": ticket.get("sender"),
                "department": ticket.get("department"),
                "intent": ticket.get("intent"),
                "priority": ticket.get("priority"),
                "status": ticket.get("status"),
                "assigned_employee_id": ticket.get("assigned_employee_id"),
                "opened_at": ticket.get("opened_at"),
                "sla_due_at": ticket.get("sla_due_at"),
            },
            expanded=False,
        )

    with right:
        st.subheader("Actions")
        employee_id = current_employee_id() or ticket.get("assigned_employee_id")

        with st.form(f"open_ticket_{ticket_id}"):
            open_employee_id = st.number_input(
                "Employee ID",
                min_value=1,
                step=1,
                value=int(employee_id or 1),
            )
            open_submitted = st.form_submit_button("Mark opened", use_container_width=True)

        if open_submitted:
            try:
                request_api(
                    "PUT",
                    f"/tickets/{ticket_id}/opened",
                    json={"employee_id": int(open_employee_id)},
                )
                st.success("Ticket marked opened.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        with st.form(f"status_ticket_{ticket_id}"):
            status_value = st.selectbox("New status", TICKET_STATUSES)
            status_employee_id = st.number_input(
                "Updated by employee ID",
                min_value=1,
                step=1,
                value=int(employee_id or 1),
            )
            note = st.text_area("Note", height=80)
            status_submitted = st.form_submit_button("Update status", use_container_width=True)

        if status_submitted:
            try:
                request_api(
                    "PUT",
                    f"/tickets/{ticket_id}/status",
                    json={
                        "employee_id": int(status_employee_id),
                        "status": status_value,
                        "note": note or None,
                    },
                )
                st.success("Ticket status updated.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.subheader("Event history")
    st.dataframe(events, hide_index=True, use_container_width=True)


def render_notifications() -> None:
    st.title("Notifications")

    role = current_role()
    col1, col2, col3 = st.columns([1, 1, 1])
    unread_only = col1.toggle("Unread only", value=True)
    recipient_role = col2.selectbox("Recipient", ["All", "employee", "manager"])

    if role in {"system", "manager"} and col3.button("Run due checks", use_container_width=True):
        try:
            request_api("POST", "/notifications/check-due")
            st.success("Notification checks completed.")
        except Exception as exc:
            st.error(str(exc))

    try:
        notifications = request_api(
            "GET",
            "/notifications",
            params={
                "unread_only": unread_only,
                "recipient_role": recipient_role,
            },
        )
    except Exception as exc:
        st.error(str(exc))
        return

    st.dataframe(notifications, hide_index=True, use_container_width=True)

    if not notifications:
        return

    notification_ids = [item["id"] for item in notifications]
    notification_id = st.selectbox("Mark notification read", notification_ids)

    if st.button("Mark read", use_container_width=False):
        try:
            request_api("PUT", f"/notifications/{notification_id}/read")
            st.success("Notification marked read.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_employees() -> None:
    st.title("Employees")

    try:
        employees = request_api("GET", "/employees")
        dashboard = request_api("GET", "/employees/dashboard")
    except Exception as exc:
        st.error(str(exc))
        return

    st.subheader("Workforce summary")
    st.json(dashboard.get("summary", dashboard), expanded=False)

    st.subheader("Directory")
    st.dataframe(employees, hide_index=True, use_container_width=True)

    if not employees:
        return

    st.subheader("Update tracking")
    employee_map = {
        f"{employee['id']} - {employee['name']} ({employee['department']})": employee
        for employee in employees
    }
    selected = st.selectbox("Employee", list(employee_map.keys()))
    employee = employee_map[selected]

    with st.form("employee_tracking"):
        skills = st.text_input("Skills", value=employee.get("skills") or "")
        max_workload = st.number_input(
            "Max workload",
            min_value=1,
            max_value=100,
            value=int(employee.get("max_workload") or 5),
        )
        is_available = st.checkbox("Available", value=bool(employee.get("is_available")))
        is_active = st.checkbox("Active", value=bool(employee.get("is_active")))
        submitted = st.form_submit_button("Update employee", use_container_width=True)

    if submitted:
        try:
            request_api(
                "PUT",
                f"/employees/{employee['id']}/tracking",
                json={
                    "skills": skills or None,
                    "max_workload": int(max_workload),
                    "is_available": is_available,
                    "is_active": is_active,
                },
            )
            st.success("Employee updated.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_gmail() -> None:
    st.title("Gmail")

    with st.form("gmail_preview"):
        from_email = st.text_input("Filter sender")
        max_results = st.number_input("Max results", min_value=1, max_value=100, value=10)
        preview = st.form_submit_button("Preview unread")

    if preview:
        try:
            data = request_api(
                "GET",
                "/gmail/unread",
                params={"from_email": from_email, "max_results": int(max_results)},
            )
            st.session_state["gmail_preview"] = data
        except Exception as exc:
            st.error(str(exc))

    if st.session_state.get("gmail_preview"):
        data = st.session_state["gmail_preview"]
        st.metric("Unread", data.get("count", 0))
        st.metric("Previously processed", data.get("ignored_count", 0))
        st.dataframe(data.get("emails", []), hide_index=True, use_container_width=True)

    col1, col2 = st.columns(2)

    if col1.button("Process unread mail", use_container_width=True):
        try:
            processed = request_api(
                "POST",
                "/gmail/process-unread",
                params={"from_email": from_email, "max_results": int(max_results)},
            )
            st.session_state["gmail_processed"] = processed
            st.success("Unread processing completed.")
        except Exception as exc:
            st.error(str(exc))

    if col2.button("Load processed audit", use_container_width=True):
        try:
            st.session_state["gmail_audit"] = request_api("GET", "/gmail/processed")
        except Exception as exc:
            st.error(str(exc))

    if st.session_state.get("gmail_processed"):
        st.subheader("Processing results")
        st.dataframe(st.session_state["gmail_processed"], hide_index=True, use_container_width=True)

    if st.session_state.get("gmail_audit"):
        st.subheader("Processed audit")
        st.dataframe(st.session_state["gmail_audit"], hide_index=True, use_container_width=True)


def render_process_email() -> None:
    st.title("Process Email")

    with st.form("process_email"):
        subject = st.text_input("Subject")
        sender = st.text_input("Sender email")
        body = st.text_area("Body", height=180)
        submitted = st.form_submit_button("Classify and create ticket", use_container_width=True)

    if submitted:
        try:
            result = request_api(
                "POST",
                "/process-email",
                json={"subject": subject, "sender": sender, "body": body},
            )
            st.success(f"Ticket #{result['ticket_id']} created.")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))


def render_system() -> None:
    st.title("System")

    col1, col2 = st.columns(2)

    try:
        health = request_api("GET", "/", auth=False)
        rbac = request_api("GET", "/rbac/endpoints", auth=False)
        system_dashboard = request_api("GET", "/system/dashboard")
    except Exception as exc:
        st.error(str(exc))
        return

    with col1:
        st.subheader("Health")
        st.json(health)
        st.subheader("RBAC")
        st.json(rbac, expanded=False)

    with col2:
        st.subheader("System dashboard")
        st.json(system_dashboard, expanded=False)


def _ticket_rows(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for ticket in tickets or []:
        rows.append({
            "id": ticket.get("id"),
            "subject": ticket.get("subject"),
            "sender": ticket.get("sender"),
            "department": ticket.get("department"),
            "priority": ticket.get("priority"),
            "status": ticket.get("status"),
            "assigned_employee_id": ticket.get("assigned_employee_id"),
            "created_at": _format_datetime(ticket.get("created_at")),
            "opened_at": _format_datetime(ticket.get("opened_at")),
            "sla_due_at": _format_datetime(ticket.get("sla_due_at")),
        })

    return rows


def _format_datetime(value: Any) -> Any:
    if not value or not isinstance(value, str):
        return value

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def main() -> None:
    init_state()

    if not st.session_state.get("token"):
        render_login()
        return

    render_shell()


if __name__ == "__main__":
    main()
