import base64

from langchain_core.runnables import RunnableConfig

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.database import db, queries
from app.caching import get_cached_gmail_token
from .tools_registry import tagged_tool

@tagged_tool("user_management", "safe")
def get_user_info(config: RunnableConfig) -> list[dict]:
    """Fetch user information."""
    configuration = config.get("configurable", {})
    chat_id = configuration.get("thread_id", None)
    if not chat_id:
        raise ValueError("No chat ID configured.")

    session = next(db.get_session())
    try:
        chat = queries.get_chat_by_id(session, chat_id)
        user = queries.get_user_by_id(session, chat.user_id)

        return {
            "id": {user.id},
            "name": {user.name},
            "email": {user.email}
        }
    except:
        return {
            "id": "unknown",
            "name": "unknown",
            "email": "unknown",
        }
    finally:
        session.close()


@tagged_tool("user_management", "safe")
def get_recent_emails(user_id: str):
    """Look up the user's most recent emails."""
    user_credentials = get_cached_gmail_token(user_id)
    creds = Credentials.from_authorized_user_info(user_credentials)
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", maxResults=5).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        full = service.users().messages().get(userId="me", id=msg["id"]).execute()
        snippet = full.get("snippet", "")
        subject = next(
            (h["value"] for h in full["payload"]["headers"] if h["name"].lower() == "subject"),
            None
        )
        sender = next(
            (h["value"] for h in full["payload"]["headers"] if h["name"].lower() == "from"),
            None
        )

        body_data = extract_body(full["payload"])

        emails.append({
            "id": msg["id"],
            "snippet": snippet,
            "sender": sender,
            "subject": subject,
            "body": body_data,
        })
    return emails

# Helper Functions

def extract_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") in ["text/plain", "text/html"]:
                data = part["body"].get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")
            # Recursively check nested parts
            if "parts" in part:
                return extract_body(part)
    return None

__all__ = ["get_user_info", "get_recent_emails"]