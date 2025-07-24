from .tools_registry import tagged_tool

@tagged_tool("knowledge_base", "safe")
def faq_lookup(query: str) -> str:
    """Search internal FAQ knowledge base."""
    # TODO: search index / db
    faq = """We understand that there are occasions when orders will need to be canceled. 
Once an order has been placed, buyers have the option to request an order cancellation up until the order has shipped."""
    return f"FAQ result for '{query}': {faq}"


@tagged_tool("knowledge_base", "sensitive")
def private_info_lookup(query: str) -> str:
    """Search private data from internal knowledge base."""
    # TODO: search index / db
    private_data = """Name: Emily Johnson\nEmail: emily.johnson87@examplemail.com\nPhone: +1-415-555-9473\nAddress: 2934 Winding Oak Drive, San Mateo, CA 94402\nSSN: 498-27-9310"""
    return f"Product specs result for '{query}': {private_data}"

__all__ = ["faq_lookup", "private_info_lookup"]