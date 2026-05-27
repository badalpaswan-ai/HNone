# Freight AI Operations POC

FastAPI proof of concept for freight operations email triage, ticket assignment, SLA tracking, and operational dashboards.

## Capabilities

- Classifies inbound freight emails into intent, department, priority, customer, origin, and destination.
- Uses Anthropic when available and automatically falls back to deterministic local classification for demos.
- Assigns tickets to the active employee with the lowest workload in the right department.
- Keeps follow-up mail from the same sender with the employee who already opened the conversation when possible.
- Tracks ticket lifecycle events, first response time, close time, and employee workload.
- Provides dashboard, ticket list/detail, employee list/create, and employee metrics endpoints.
- Includes an MCP tool server (`freight-tools`) for classification, tickets, dashboard, and Gmail batch processing.

## Run

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

Open the API docs at `http://127.0.0.1:8000/docs`.

## Streamlit Frontend

From `frontend/`:

```bash
../.venv/bin/streamlit run app.py
```

If Streamlit is not installed in the virtualenv:

```bash
../.venv/bin/pip install -r requirements.txt
```

## Backend Structure

The backend follows a standard FastAPI layout:

```text
backend/app/
  api/
    deps.py                 # shared FastAPI dependencies
    v1/
      router.py             # versioned API router composition
      endpoints/            # HTTP route handlers grouped by feature
  core/
    config.py               # environment-backed settings
    openapi.py              # Swagger/OpenAPI tags and security metadata
    security.py             # auth, JWT, and RBAC helpers
  db/
    session.py              # SQLAlchemy engine, session, Base, init
    seed.py                 # startup seed data
  models/                   # SQLAlchemy ORM models
  schemas/                  # Pydantic request/response schemas
  services/                 # business logic
  agents/                   # AI classification agent wrappers
  mcp/                      # MCP helper implementation
  main.py                   # FastAPI app factory
```

Legacy modules such as `app.auth`, `app.config`, `app.database`, and
`app.routes.*` remain as thin compatibility shims while new code should import
from `app.core`, `app.db`, and `app.api.v1`.

## RBAC

Protected endpoints require a JWT bearer token:

```bash
Authorization: Bearer <token>
```

Supported roles:

- `system`
- `manager`
- `employee`

Data access is scoped by role:

- `system`: full access to endpoint data.
- `manager`: department-level access.
- `employee`: only data assigned or linked to that employee.

Role metadata and grouped endpoint access are available at:

```bash
GET /rbac/endpoints
```

Demo login users:

- `system` / `system123`
- `manager` / `manager123`
- `employee` / `employee123`

Login example:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"manager","password":"manager123"}'
```

Authenticated request example:

```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/dashboard
```

In Swagger's **Authorize** dialog, paste only the token value. Do not include the
`Bearer` prefix there.

## MCP Server

From `backend/`:

```bash
../.venv/bin/python -m app.mcp_server
```

Legacy entrypoint (same server): `../.venv/bin/python mcp/mcp_server.py`

### MCP tools

- `classify_freight_email`, `classify_department`, `calculate_priority`
- `process_email`, `list_tickets`, `get_ticket`, `update_ticket_status`
- `get_dashboard`, `get_employee_metrics`, `list_employees`, `smart_assign_preview`
- `fetch_gmail_unread`, `process_gmail_unread`

### MCP resources

- `freight://routing-rules`
- `freight://ticket-statuses`

### Cursor MCP config (example)

```json
{
  "mcpServers": {
    "freight-tools": {
      "command": "/Users/bkp/Documents/HNone_POC/.venv/bin/python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/Users/bkp/Documents/HNone_POC/backend"
    }
  }
}
```

## Key Endpoints

- `POST /process-email`
- `GET /tickets`
- `GET /tickets/{ticket_id}`
- `PUT /tickets/{ticket_id}/opened`
- `PUT /tickets/{ticket_id}/status`
- `GET /dashboard`
- `POST /auth/login`
- `GET /auth/me`
- `GET /system/dashboard`
- `GET /admin/dashboard`
- `GET /employee-metrics`
- `GET /employees/dashboard`
- `GET /employees/{employee_id}/dashboard`
- `GET /employees`
- `POST /employees`
- `GET /gmail/processed`
- `GET /notifications`
- `POST /notifications/check-due`
- `POST /notifications/check-mail-open`
- `POST /notifications/check-mail-resolve`
- `PUT /notifications/{notification_id}/read`

## Configuration

The backend reads `backend/.env`.

- `DATABASE_URL`: defaults to `sqlite:///backend/freight_ai.db` when not set.
- `MAIL_OPEN_NOTIFICATION_SECONDS`: defaults to `20`.
- `MAIL_RESOLVE_NOTIFICATION_SECONDS`: defaults to `60`.
- `GMAIL_AUTO_CHECK_ENABLED`: defaults to `true`.
- `GMAIL_AUTO_CHECK_INTERVAL_SECONDS`: defaults to `900` (15 minutes).
- `WELCOME_EMAIL_SUBJECT`: defaults to `Welcome to HNOne`.
- `WELCOME_EMAIL_BODY`: defaults to `Welcome to HNOne, we will reach out to you with a response within 30 mins.`
- `ANTHROPIC_API_KEY`: optional for live AI classification.
- `ANTHROPIC_MODEL`: defaults to `claude-3-5-sonnet-20241022`.
- `AI_MODE`: `auto`, `mock`, or live-only behavior by setting any non-`auto` value with a key.
- `RESET_INCOMPATIBLE_SQLITE_SCHEMA`: defaults to `true` for POC schema repair.

## Demo Request

```json
{
  "subject": "Urgent shipment delay from Mumbai to Dubai",
  "sender": "customer@example.com",
  "body": "Customer: Acme Logistics\nOrigin: Mumbai\nDestination: Dubai\nOur container shipment is delayed and critical. Please escalate asap."
}
```
