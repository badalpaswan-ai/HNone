import os.path
import base64
from pathlib import Path
from email.message import EmailMessage
from email.utils import parseaddr

SERVICE_ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS_PATH = SERVICE_ROOT / "credentials.json"
TOKEN_PATH = SERVICE_ROOT / "token.json"

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _google_available = True
except Exception:
    _google_available = False

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
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

        if CREDENTIALS_PATH.exists() and TOKEN_PATH.exists():

            self.creds = Credentials.from_authorized_user_file(
                TOKEN_PATH,
                SCOPES
            )

            if not self.creds.has_scopes(SCOPES):
                self.creds = None

        if not self.creds or not self.creds.valid:

            if self.creds and self.creds.expired and self.creds.refresh_token:

                self.creds.refresh(Request())

            else:

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH,
                    SCOPES
                )

                self.creds = flow.run_local_server(
                    port=0
                )

            with open(TOKEN_PATH, "w") as token:

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

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ):
        _, address = parseaddr(to_email)
        recipient = address or to_email

        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        payload = {"raw": raw}

        if thread_id:
            payload["threadId"] = thread_id

        return (
            self.service.users()
            .messages()
            .send(
                userId="me",
                body=payload,
            )
            .execute()
        )

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

        query = self.build_query(from_email)

        results = (
            self.service.users()
            .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=max_results
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
                    id=msg["id"],
                    format="full"
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

            body = self._extract_body(payload)

            emails.append({
                "gmail_message_id": msg["id"],
                "gmail_thread_id": message.get("threadId"),
                "subject": subject,
                "sender": sender,
                "body": body,
                "snippet": message.get("snippet"),
                "internal_date": int(message.get("internalDate", 0))
            })

        return sorted(
            emails,
            key=lambda email: email.get("internal_date", 0),
            reverse=True
        )

    def _extract_body(self, payload):
        if payload.get("body", {}).get("data"):
            return self._decode_body(payload["body"]["data"])

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return self._decode_body(data)

            nested_body = self._extract_body(part)
            if nested_body:
                return nested_body

        return ""

    def _decode_body(self, data):
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
