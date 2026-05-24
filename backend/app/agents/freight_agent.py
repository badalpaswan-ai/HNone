from anthropic import Anthropic
from app.config import settings

import json

client = Anthropic(
    api_key=settings.ANTHROPIC_API_KEY
)

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
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
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