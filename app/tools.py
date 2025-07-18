from langchain_core.tools import tool

@tool
def get_order_status(order_id: str) -> str:
    """Look up the status of a user order by ID."""
    # TODO: real lookup
    return f"Order {order_id} is 'processing'."

TOOLS = [get_order_status]