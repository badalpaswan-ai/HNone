from fastmcp import FastMCP

mcp = FastMCP("freight-tools")

@mcp.tool()
def classify_department(intent: str):

    mapping = {
        "new_enquiry": "sales",
        "shipment_support": "operations",
        "invoice_issue": "finance"
    }

    return {
        "department": mapping.get(
            intent,
            "operations"
        )
    }

@mcp.tool()
def calculate_priority(priority: str):

    return {
        "priority": priority
    }

if __name__ == "__main__":
    mcp.run()