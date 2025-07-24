from .tools_registry import tagged_tool

@tagged_tool("order_management", "safe")
def get_order_status(order_id: str) -> str:
    """Look up the status of a user order by ID."""
    # TODO: real lookup
    if int(order_id) % 2 == 0:
        return f"status: shipped"
    return  f"status: processing"

@tagged_tool("order_management", "sensitive")
def cancel_order(order_id: str) -> str:
    """
    Cancels a user order by ID.

    Only use this tool if you have already verified that the order is eligible for cancellation.
    An order is eligible if it has not yet been shipped or received.

    If you have not checked the order status, use `get_order_status` first.
    """
    # TODO: real order cancel
    return f"Order {order_id} has been cancelled successfully."

@tagged_tool("order_management", "safe")
def get_order_ETA(order_id: str) -> str:
    """Look up the order's ETA (estimated time of arrival) of a user order by ID."""
    # TODO: real lookup
    return f"The order {order_id} will arrive tomorrow between 9am and 1pm."

@tagged_tool("order_management", "safe")
def get_refund_status(order_id: str) -> str:
    """Look up the status of an order refund by order ID."""
    # TODO: real lookup
    return f"Order {order_id} has a refund status of 'processing'."


__all__ = ["get_order_status", "cancel_order", "get_order_ETA", "get_refund_status"]