import json

from anthropic import Anthropic

from app.core.config import settings
from app.services.classification_service import (
    department_for_intent,
    is_freight_relevant,
    normalize_priority,
    rule_based_classification,
)

FREIGHT_DEPARTMENTS = {
    "sales",
    "operations",
    "finance",
    "customs",
    "support",
}

ALLOWED_INTENTS = {
    "new_enquiry",
    "shipment_support",
    "invoice_issue",
    "customs_issue",
    "escalation",
    "spam",
}

SYSTEM_PROMPT = """
You classify inbound email for a freight/logistics operations desk.

Return ONLY a JSON object with these keys:
- intent: one of new_enquiry, shipment_support, invoice_issue, customs_issue, escalation, spam
- department: one of sales, operations, finance, customs, support, other
- priority: one of LOW, MEDIUM, HIGH, URGENT
- confidence_score: number between 0 and 1
- customer_name: string or null
- origin: string or null
- destination: string or null

Routing rules:
- new_enquiry -> sales
- shipment_support -> operations
- invoice_issue -> finance
- customs_issue -> customs
- escalation -> operations
- spam/non-freight -> other

Treat newsletters, job/career messages, marketing, social-network messages,
discount offers, password/security notices, and unrelated business emails as
spam/non-freight unless they clearly mention freight, logistics, cargo,
shipment, customs, container, port, delivery, pickup, or a freight route.
"""

_client = None


def _anthropic_client():
    global _client

    if _client is None:
        _client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=8.0,
        )

    return _client


def is_freight_email(result: dict) -> bool:
    return result.get("department") in FREIGHT_DEPARTMENTS


def _classification_text(email_body: str, subject: str | None = None) -> str:
    if subject and subject.strip():
        return f"Subject: {subject.strip()}\n\n{email_body}"

    return email_body


def _should_use_rule_based() -> bool:
    if settings.AI_MODE == "mock":
        return True

    if settings.AI_MODE == "auto" and not settings.ANTHROPIC_API_KEY:
        return True

    return False


def _classify_with_anthropic(text: str) -> dict:
    response = _anthropic_client().messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": text,
            }
        ],
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    result = json.loads(raw)
    return _normalize_classification(result, text, "anthropic")


def _normalize_classification(result: dict, text: str, source: str) -> dict:
    if not is_freight_relevant(text):
        fallback = rule_based_classification(text)
        fallback["classification_source"] = source
        fallback["ai_note"] = "forced_non_freight_by_relevance_gate"
        return fallback

    intent = str(result.get("intent") or "shipment_support").strip().lower()
    if intent not in ALLOWED_INTENTS or intent == "spam":
        intent = "shipment_support"

    department = str(result.get("department") or "").strip().lower()
    expected_department = department_for_intent(intent)
    if department not in FREIGHT_DEPARTMENTS:
        department = expected_department

    if department != expected_department and intent != "spam":
        department = expected_department

    priority = normalize_priority(str(result.get("priority") or "MEDIUM"))

    entities = rule_based_classification(text)

    return {
        "intent": intent,
        "department": department,
        "priority": priority,
        "confidence_score": result.get("confidence_score", 0.75),
        "classification_source": source,
        "customer_name": result.get("customer_name") or entities.get("customer_name"),
        "origin": result.get("origin") or entities.get("origin"),
        "destination": result.get("destination") or entities.get("destination"),
    }


def rule_based_classification_for_email(
    email_body: str,
    subject: str | None = None,
) -> dict:
    return rule_based_classification(_classification_text(email_body, subject))


def classify_email(email_body: str, subject: str | None = None) -> dict:
    text = _classification_text(email_body, subject)

    if _should_use_rule_based():
        return rule_based_classification(text)

    try:
        return _classify_with_anthropic(text)
    except Exception:
        if settings.AI_MODE == "auto":
            return rule_based_classification(text)

        raise
