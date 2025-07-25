import base64

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_store

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.database import db, queries
from app.caching import get_cached_gmail_token
from .tools_registry import tagged_tool

@tagged_tool("user_management", "safe")
def get_user_info(config: RunnableConfig) -> list[dict]:
    """Fetch user information."""

    session = next(db.get_session())
    try:
        user_id = config.get("configurable").get("user_id")
        if not user_id:
            return ValueError("failed to retrieve user_id from configuration")

        # Retrieve existing memory from the store
        namespace = ("memory", user_id)
        store = get_store()
        existing_memory = store.get(namespace, "user_memory")
        # Extract the memory
        if existing_memory:
            existing_memory_content = existing_memory.value.get('memory')
        else:
            user = queries.get_user_by_id(session, user_id)
            new_memory = f"The user's id is '{user.id}'. The user's name is {user.name}, with email: {user.email}"
            # Write value as a dictionary with a memory key
            store.put(namespace, "user_memory", {"memory": new_memory})
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