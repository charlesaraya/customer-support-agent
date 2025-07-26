from typing import Annotated, TypedDict, Optional

from langgraph.graph import MessagesState

class UserProfile(TypedDict):
    """User profile schema with typed fields"""
    name: str
    email: str
    user_id: str

def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop the state."""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]

class State(MessagesState):
    user_profile: UserProfile
    dialog_state: Annotated[list[str], update_dialog_stack]
