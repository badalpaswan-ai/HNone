import os.path
import base64

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _google_available = True
except Exception:
    _google_available = False

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]

class GmailService:

    def __init__(self):

        if not _google_available:
            raise ImportError(
                "google API libraries are not installed. Install requirements or mock GmailService."
            )

        self.creds = None

        self.authenticate()

    def authenticate(self):

        if os.path.exists("token.json"):

            self.creds = Credentials.from_authorized_user_file(
                "token.json",
                SCOPES
            )

        if not self.creds or not self.creds.valid:

            if self.creds and self.creds.expired and self.creds.refresh_token:

                self.creds.refresh(Request())

            else:

                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    SCOPES
                )

                self.creds = flow.run_local_server(
                    port=0
                )

            with open("token.json", "w") as token:

                token.write(
                    self.creds.to_json()
                )

        self.service = build(
            "gmail",
            "v1",
            credentials=self.creds
        )

    def fetch_unread_emails(self):

        return self.fetch_unread_emails_filtered()

    def fetch_unread_emails_filtered(self, from_email: str | None = None):

        query = "is:unread"

        if from_email:
            query = f"{query} from:{from_email}"

        results = (
            self.service.users()
            .messages()
            .list(
                userId="me",
                q=query
            )
            .execute()
        )

        messages = results.get(
            "messages",
            []
        )

        emails = []

        for msg in messages:

            message = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"]
                )
                .execute()
            )

            payload = message["payload"]

            headers = payload["headers"]

            subject = ""
            sender = ""

            for header in headers:

                if header["name"] == "Subject":
                    subject = header["value"]

                if header["name"] == "From":
                    sender = header["value"]

            body = ""

            if "parts" in payload:

                for part in payload["parts"]:

                    if part["mimeType"] == "text/plain":

                        data = part["body"].get("data")

                        if data:

                            body = base64.urlsafe_b64decode(
                                data
                            ).decode("utf-8")

            emails.append({
                "gmail_message_id": msg["id"],
                "subject": subject,
                "sender": sender,
                "body": body
            })

        return emails