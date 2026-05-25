import json
import re

from app.config import settings


SYSTEM_PROMPT = """
You are a freight operations AI assistant.

Classify freight emails.

Possible intents:
- new_enquiry
- shipment_support
- invoice_issue
- customs_issue
- escalation
- spam

Return ONLY valid JSON.

Extract:
- intent
- department
- priority
- customer_name
- origin
- destination
"""

def classify_email(email_body: str):
    if settings.AI_MODE == "mock" or not settings.ANTHROPIC_API_KEY:
        return rule_based_classification(email_body)

    try:
        from anthropic import Anthropic

        client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": email_body
                }
            ]
        )
    except Exception as exc:
        if settings.AI_MODE == "auto":
            return rule_based_classification(email_body)

        raise RuntimeError(f"AI request failed: {exc}")

    # extract text and parse JSON
    text = None
    try:
        text = response.content[0].text
    except Exception:
        raise ValueError("AI response missing text")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse AI JSON: {exc}\n{text}")


def rule_based_classification(email_body: str):
    text = email_body.lower()

    if any(word in text for word in ["invoice", "payment", "billing"]):
        intent = "invoice_issue"
        department = "finance"
    elif any(word in text for word in ["customs", "clearance", "hs code"]):
        intent = "customs_issue"
        department = "customs"
    elif any(word in text for word in ["delay", "tracking", "shipment", "container"]):
        intent = "shipment_support"
        department = "operations"
    elif any(word in text for word in ["urgent", "escalate", "critical"]):
        intent = "escalation"
        department = "operations"
    elif any(word in text for word in ["quote", "rate", "enquiry", "inquiry"]):
        intent = "new_enquiry"
        department = "sales"
    else:
        intent = "shipment_support"
        department = "support"

    if any(word in text for word in ["urgent", "critical", "asap", "escalate"]):
        priority = "URGENT"
    elif any(word in text for word in ["delay", "stuck", "blocked"]):
        priority = "HIGH"
    elif any(word in text for word in ["quote", "rate"]):
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return {
        "intent": intent,
        "department": department,
        "priority": priority,
        "customer_name": _extract_customer_name(email_body),
        "origin": _extract_lane_value(email_body, "origin"),
        "destination": _extract_lane_value(email_body, "destination")
    }


def _extract_customer_name(email_body: str):
    match = re.search(
        r"(customer|client)\s*:\s*([A-Za-z0-9 .&-]+)",
        email_body,
        re.IGNORECASE
    )
    return match.group(2).strip() if match else None


def _extract_lane_value(email_body: str, label: str):
    match = re.search(
        rf"{label}\s*:\s*([A-Za-z0-9 .,-]+)",
        email_body,
        re.IGNORECASE
    )
    return match.group(1).strip() if match else None
