# Freight AI Operations POC

FastAPI proof of concept for freight operations email triage, ticket assignment, SLA tracking, and operational dashboards.

## Capabilities

- Classifies inbound freight emails into intent, department, priority, customer, origin, and destination.
- Uses Anthropic when available and automatically falls back to deterministic local classification for demos.
- Assigns tickets to the active employee with the lowest workload in the right department.
- Tracks ticket lifecycle events, first response time, close time, and employee workload.
- Provides dashboard, ticket list/detail, employee list/create, and employee metrics endpoints.
- Includes an MCP tool server for freight classification helpers.

## Run

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

Open the API docs at `http://127.0.0.1:8000/docs`.

## Key Endpoints

- `POST /process-email`
- `GET /tickets`
- `GET /tickets/{ticket_id}`
- `PUT /tickets/{ticket_id}/status`
- `GET /dashboard`
- `GET /employee-metrics`
- `GET /employees`
- `POST /employees`

## Configuration

The backend reads `backend/.env`.

- `DATABASE_URL`: defaults to `sqlite:///backend/freight_ai.db` when not set.
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
