from enum import Enum
from pydantic import BaseModel, Field

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
    """Transfers work to a specialized assistant to handle tasks that require accessing internal knowledge base of the company."""
    request: str = Field(
        description="Any necessary followup questions the knowledge base assistant should clarify before proceeding."
    )


class ToUserManagementAssistant(BaseModel):
    """Transfers work to a specialized assistant to handle tasks that require accessing the user's email and calendar tools."""
    request: str = Field(
        description="Any necessary followup questions the knowledge base assistant should clarify before proceeding."
    )

__all__ = ["CompleteOrEscalate", "ToOrderManagementAssistant", "ToKnowledgeBaseAssistant", "ToUserManagementAssistant"] 