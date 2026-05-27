from app.services.mock_gmail_service import MockGmailService

try:
    from app.services.gmail_service import GmailService
except Exception:
    GmailService = None


def resolve_gmail_service():
    if GmailService:
        try:
            return GmailService()
        except Exception:
            pass

    return MockGmailService()


def gmail_service_type(service) -> str:
    return "gmail" if service.__class__.__name__ == "GmailService" else "mock"
