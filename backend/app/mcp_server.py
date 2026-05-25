from fastmcp import FastMCP

from app.agents.freight_agent import rule_based_classification

mcp = FastMCP("freight-tools")


@mcp.tool()
def classify_department(intent: str):
    mapping = {
        "new_enquiry": "sales",
        "shipment_support": "operations",
        "invoice_issue": "finance",
        "customs_issue": "customs",
        "escalation": "operations",
        "spam": "support"
    }

    return {
        "department": mapping.get(intent, "support")
    }


@mcp.tool()
def calculate_priority(priority: str):
    normalized = priority.upper()
    allowed = {"LOW", "MEDIUM", "HIGH", "URGENT"}

    return {
        "priority": normalized if normalized in allowed else "MEDIUM"
    }


@mcp.tool()
def classify_freight_email(email_body: str):
    return rule_based_classification(email_body)


if __name__ == "__main__":
    mcp.run()
