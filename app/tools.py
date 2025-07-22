from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.database import db, models, queries

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
    finally:
        session.close()

@tool
def get_order_status(order_id: str) -> str:
    """Look up the status of a user order by ID."""
    # TODO: real lookup
    return f"status: shipped."

@tool
def cancel_order(order_id: str) -> str:
    """Cancels the order of a user order by ID."""
    # TODO: real order cancel
    return f"Order {order_id} has been cancelled successfully."

@tool
def get_order_ETA(order_id: str) -> str:
    """Look up the order's ETA (estimated time of arrival) of a user order by ID."""
    # TODO: real lookup
    return f"The order {order_id} will arrive tomorrow between 9am and 1pm."

def get_user_tools():
    return [get_user_info]

def get_safe_tools():
    return [get_order_status, get_order_ETA]

def get_sensitive_tools():
    return [cancel_order]

def get_safe_tools_names():
    return [tool.name for tool in get_safe_tools()]

def get_sensitive_tools_names():
    return [tool.name for tool in get_sensitive_tools()]

def get_tools():
    return [*get_safe_tools(), *get_sensitive_tools()]
