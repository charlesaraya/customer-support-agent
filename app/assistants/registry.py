from app.tools import (
    ToOrderManagementAssistant,
    ToKnowledgeBaseAssistant,
    ToUserManagementAssistant
)

from app.assistants.prompts import (
    SUPERVISOR_AGENT_SYSTEM_PROMPT,
    ORDER_MANAGEMENT_ASSISTANT_SYSTEM_PROMPT,
    KNOWLEDGE_BASE_ASSISTANT_SYSTEM_PROMPT,
    USER_MANAGEMENT_ASSISTANT_SYSTEM_PROMPT,
)

SUPERVISOR = {
    "name": "supervisor",
    "system_prompt": SUPERVISOR_AGENT_SYSTEM_PROMPT,
    "tools": [ToOrderManagementAssistant, ToKnowledgeBaseAssistant, ToUserManagementAssistant],
}

def get_supervisor() -> dict:
    return SUPERVISOR

ASSISTANT_REGISTRY = {
    "order_management": {
        "name": "Order Management Assistant",
        "system_prompt": ORDER_MANAGEMENT_ASSISTANT_SYSTEM_PROMPT,
        "entry_tool": ToOrderManagementAssistant,
        "tool_tag": "order_management",
    },
    "knowledge_base": {
        "name": "Knowledge Base Assistant",
        "system_prompt": KNOWLEDGE_BASE_ASSISTANT_SYSTEM_PROMPT,
        "entry_tool": ToKnowledgeBaseAssistant,
        "tool_tag": "knowledge_base",
    },
    "user_management": {
        "name": "User Management Assistant",
        "system_prompt": USER_MANAGEMENT_ASSISTANT_SYSTEM_PROMPT,
        "entry_tool": ToUserManagementAssistant,
        "tool_tag": "user_management",
    },
}

def get_registry() -> dict:
    return ASSISTANT_REGISTRY