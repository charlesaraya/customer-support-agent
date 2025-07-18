from langchain_core.tools import tool

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

TOOLS = [get_order_status, cancel_order, get_order_ETA]