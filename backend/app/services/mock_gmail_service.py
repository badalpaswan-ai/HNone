class MockGmailService:

    def __init__(self):
        pass

    def fetch_unread_emails_filtered(self, from_email: str | None = None):
        samples = [
            {
                "gmail_message_id": "mock-1",
                "subject": "Mock: Delay in shipment #1001",
                "sender": "customer1@example.com",
                "body": "My shipment is delayed. Please advise ETA."
            },
            {
                "gmail_message_id": "mock-2",
                "subject": "Mock: Invoice issue",
                "sender": "billing@example.com",
                "body": "There is an error in the invoice attached."
            }
        ]

        if from_email:
            return [e for e in samples if from_email.lower() in e["sender"].lower()]

        return samples

    # keep a compat shim for previous method name
    def fetch_unread_emails(self):
        return self.fetch_unread_emails_filtered()
