from enum import Enum
from pydantic import BaseModel, Field
import base64

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.database import db, queries
from app.caching import get_cached_gmail_token

@tool
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

# Order Management Tools

@tool
def get_order_status(order_id: str) -> str:
    """Look up the status of a user order by ID."""
    # TODO: real lookup
    if int(order_id) % 2 == 0:
        return f"status: shipped"
    return  f"status: processing"

@tool
def cancel_order(order_id: str) -> str:
    """
    Cancels a user order by ID.

    Only use this tool if you have already verified that the order is eligible for cancellation.
    An order is eligible if it has not yet been shipped or received.

    If you have not checked the order status, use `get_order_status` first.
    """
    # TODO: real order cancel
    return f"Order {order_id} has been cancelled successfully."

@tool
def get_order_ETA(order_id: str) -> str:
    """Look up the order's ETA (estimated time of arrival) of a user order by ID."""
    # TODO: real lookup
    return f"The order {order_id} will arrive tomorrow between 9am and 1pm."

@tool
def get_refund_status(order_id: str) -> str:
    """Look up the status of an order refund by order ID."""
    # TODO: real lookup
    return f"Order {order_id} has a refund status of 'processing'."

# Knowledge Base Tools

@tool
def faq_lookup(query: str) -> str:
    """Search internal FAQ knowledge base."""
    # TODO: search index / db
    faq = """We understand that there are occasions when orders will need to be canceled. 
Once an order has been placed, buyers have the option to request an order cancellation up until the order has shipped."""
    return f"FAQ result for '{query}': {faq}"

@tool
def private_info_lookup(query: str) -> str:
    """Search private data from internal knowledge base."""
    # TODO: search index / db
    private_data = """Name: Emily Johnson\nEmail: emily.johnson87@examplemail.com\nPhone: +1-415-555-9473\nAddress: 2934 Winding Oak Drive, San Mateo, CA 94402\nSSN: 498-27-9310"""
    return f"Product specs result for '{query}': {private_data}"

@tool
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

def get_user_tools():
    return [get_user_info]

def get_order_management_tools():
    return [get_order_status, cancel_order, get_order_ETA, get_refund_status]

def get_knowledge_base_tools():
    return [faq_lookup, private_info_lookup, get_recent_emails]

def get_safe_tools():
    return [get_order_status, get_order_ETA, faq_lookup, get_refund_status, get_recent_emails]

def get_sensitive_tools():
    return [cancel_order, private_info_lookup]

def get_safe_tools_names():
    return [tool.name for tool in get_safe_tools()]

def get_sensitive_tools_names():
    return [tool.name for tool in get_sensitive_tools()]

def get_tools():
    return [*get_safe_tools(), *get_sensitive_tools()]

def get_safe_order_management_tools():
    safe_tools = get_safe_tools()
    safe_tools_names = [tool.name for tool in safe_tools]
    order_tools = get_order_management_tools()
    safe_order_tools = list(filter(lambda x: x.name in safe_tools_names, order_tools))
    return safe_order_tools

def get_sensitive_order_management_tools():
    sensitive_tools = get_sensitive_tools()
    sensitive_tools_names = [tool.name for tool in sensitive_tools]
    order_tools = get_order_management_tools()
    sensitive_order_tools = list(filter(lambda x: x.name in sensitive_tools_names, order_tools))
    return sensitive_order_tools

def get_safe_knowledge_base_tools():
    safe_tools = get_safe_tools()
    safe_tools_names = [tool.name for tool in safe_tools]
    knowledge_tools = get_knowledge_base_tools()
    safe_knowledge_tools = list(filter(lambda x: x.name in safe_tools_names, knowledge_tools))
    return safe_knowledge_tools

def get_sensitive_knowledge_base_tools():
    sensitive_tools = get_sensitive_tools()
    sensitive_tools_names = [tool.name for tool in sensitive_tools]
    knowledge_tools = get_knowledge_base_tools()
    sensitive_knowledge_tools = list(filter(lambda x: x.name in sensitive_tools_names, knowledge_tools))
    return sensitive_knowledge_tools

class CompletionStatus(str, Enum):
    COMPLETED = "completed"
    USER_CHANGED_MIND = "user_changed_mind"
    NEED_MORE_INFO = "need_more_info"
    OUT_OF_SCOPE = "out_of_scope"

class CompleteOrEscalate(BaseModel):
    """Indicates that the control flow should be passed back to the supervisor agent.

    This happens if the assistant completed the task, needs more input, or the task is no longer relevant.
    """

    status: CompletionStatus
    detail: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "detail": "The task was successfully completed.",
            },
            "example 2": {
                "status": "user_changed_mind",
                "detail": "User changed their mind and no longer wants to proceed.",
            },
            "example 2": {
                "status": "need_more_info",
                "detail": "More input is needed from the user to proceed.",
            },
            "example 3": {
                "status": "out_of_scope",
                "detail": "The task is outside the scope of this assistant.",
            },
        }

class ToOrderManagementAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle order management tasks."""
    request: str = Field(
        description="Any necessary followup questions the order management assistant should clarify before proceeding."
    )


class ToKnowledgeBaseAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle tasks that require accessing knowledge base or answer user management queries."""
    request: str = Field(
        description="Any necessary followup questions the knowledge base assistant should clarify before proceeding."
    )