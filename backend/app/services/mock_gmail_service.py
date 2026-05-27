class MockGmailService:

    def __init__(self):
        self.sent_emails = []

    def build_query(self, from_email: str | None = None):
        query = "is:unread"

        if from_email:
            query = f"{query} from:{from_email.strip()}"

        return query

    def fetch_unread_emails_filtered(
        self,
        from_email: str | None = None,
        max_results: int = 10,
    ):
        samples = [
            {
                "gmail_message_id": "mock-1",
                "gmail_thread_id": "mock-thread-1",
                "subject": "Mock: Delay in shipment #1001",
                "sender": "customer1@example.com",
                "body": "My shipment is delayed. Please advise ETA.",
                "internal_date": 3000
            },
            {
                "gmail_message_id": "mock-2",
                "gmail_thread_id": "mock-thread-2",
                "subject": "Mock: Invoice issue",
                "sender": "billing@example.com",
                "body": "There is an error in the invoice for shipment #1002.",
                "internal_date": 2000
            },
            {
                "gmail_message_id": "mock-3",
                "gmail_thread_id": "mock-thread-3",
                "subject": "Mock: Job transition tips",
                "sender": "newsletter@example.com",
                "body": "Tips for navigating finances during your job transition.",
                "internal_date": 1000
            }
        ]

        if from_email:
            samples = [e for e in samples if from_email.lower() in e["sender"].lower()]

        return sorted(
            samples,
            key=lambda email: email.get("internal_date", 0),
            reverse=True
        )[:max_results]

    # keep a compat shim for previous method name
    def fetch_unread_emails(self):
        return self.fetch_unread_emails_filtered()

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ):
        sent = {
            "id": f"mock-sent-{len(self.sent_emails) + 1}",
            "to": to_email,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
        }
        self.sent_emails.append(sent)
        return sent
