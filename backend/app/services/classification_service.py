import re

INTENT_KEYWORDS = [
    ("customs_issue", ("customs", "clearance", "duty", "import license", "hs code")),
    ("invoice_issue", ("invoice", "billing", "payment", "receipt", "credit note")),
    (
        "new_enquiry",
        (
            "quote",
            "quotation",
            "enquiry",
            "inquiry",
            "pricing",
            "rate request",
            "freight rate",
            "shipping rate",
        ),
    ),
    (
        "shipment_support",
        (
            "delay",
            "delayed",
            "shipment",
            "container",
            "tracking",
            "eta",
            "delivery",
            "cargo",
            "pickup",
            "pod",
            "bill of lading",
            "bl number",
            "booking",
        ),
    ),
    ("escalation", ("escalate", "escalation")),
]

NON_FREIGHT_KEYWORDS = (
    "unsubscribe",
    "newsletter",
    "job application",
    "job transition",
    "career",
    "resume",
    "interview",
    "linkedin",
    "marketing",
    "sale offer",
    "discount",
    "promotion",
    "webinar",
    "subscription",
    "password reset",
    "verification code",
)

FREIGHT_CONTEXT_KEYWORDS = (
    "freight",
    "shipment",
    "shipping",
    "container",
    "cargo",
    "logistics",
    "customs",
    "clearance",
    "port",
    "vessel",
    "airway bill",
    "bill of lading",
    "bl number",
    "booking",
    "pickup",
    "delivery",
    "eta",
    "pod",
    "consignee",
    "shipper",
    "origin:",
    "destination:",
)

URGENT_KEYWORDS = ("urgent", "critical", "asap", "immediately", "emergency")
HIGH_KEYWORDS = ("delay", "problem", "issue", "error", "stuck", "held")

INTENT_TO_DEPARTMENT = {
    "new_enquiry": "sales",
    "shipment_support": "operations",
    "invoice_issue": "finance",
    "customs_issue": "customs",
    "escalation": "operations",
    "spam": "support",
}


def department_for_intent(intent: str) -> str:
    return INTENT_TO_DEPARTMENT.get(intent, "support")


def is_freight_relevant(text: str) -> bool:
    lower = text.lower()

    if any(keyword in lower for keyword in NON_FREIGHT_KEYWORDS):
        return False

    if any(keyword in lower for keyword in FREIGHT_CONTEXT_KEYWORDS):
        return True

    route_match = re.search(
        r"\bfrom\s+[A-Za-z][A-Za-z\s]{1,40}?\s+to\s+[A-Za-z][A-Za-z\s]{1,40}?\b",
        text,
        re.IGNORECASE,
    )
    if route_match and any(
        keyword in lower
        for keyword in ("quote", "rate", "move", "send", "transport", "ship")
    ):
        return True

    return False


def extract_entities(text: str) -> dict[str, str | None]:
    customer_name = None
    origin = None
    destination = None

    customer_match = re.search(
        r"customer\s*:\s*(.+)",
        text,
        re.IGNORECASE,
    )
    if customer_match:
        customer_name = customer_match.group(1).strip().split("\n")[0][:120]

    origin_match = re.search(
        r"origin\s*:\s*(.+)",
        text,
        re.IGNORECASE,
    )
    if origin_match:
        origin = origin_match.group(1).strip().split("\n")[0][:120]

    destination_match = re.search(
        r"destination\s*:\s*(.+)",
        text,
        re.IGNORECASE,
    )
    if destination_match:
        destination = destination_match.group(1).strip().split("\n")[0][:120]

    route_match = re.search(
        r"from\s+([A-Za-z][A-Za-z\s]{1,40}?)\s+to\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\s+for\b|[.,\n]|$)",
        text,
        re.IGNORECASE,
    )
    if route_match:
        origin = origin or route_match.group(1).strip()
        destination = destination or route_match.group(2).strip()

    return {
        "customer_name": customer_name,
        "origin": origin,
        "destination": destination,
    }


def detect_intent(text: str) -> str:
    lower = text.lower()

    for intent, keywords in INTENT_KEYWORDS:
        if any(keyword in lower for keyword in keywords):
            return intent

    return "other"


def detect_priority(text: str) -> str:
    lower = text.lower()

    if any(keyword in lower for keyword in URGENT_KEYWORDS):
        return "URGENT"

    if any(keyword in lower for keyword in HIGH_KEYWORDS):
        return "HIGH"

    if any(keyword in lower for keyword in ("please", "advise", "question", "update")):
        return "MEDIUM"

    return "LOW"


def rule_based_classification(text: str) -> dict:
    lower = text.lower()
    entities = extract_entities(text)

    if not is_freight_relevant(text):
        return {
            "intent": "spam",
            "department": "other",
            "priority": "LOW",
            "confidence_score": 0.85,
            "classification_source": "rule_based",
            **entities,
        }

    intent = detect_intent(text)
    department = department_for_intent(intent)
    priority = detect_priority(text)

    return {
        "intent": intent,
        "department": department,
        "priority": priority,
        "confidence_score": 0.75,
        "classification_source": "rule_based",
        **entities,
    }


def normalize_priority(priority: str) -> str:
    normalized = priority.strip().upper()
    allowed = {"LOW", "MEDIUM", "HIGH", "URGENT"}

    if normalized in allowed:
        return normalized

    return "MEDIUM"
