from typing import Callable

from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import tools_condition
from langgraph.graph import END

from app.tools import tools_registry, CompleteOrEscalate
from app.config import get_llm
from app.state import State
from app.assistants.registry import get_registry, get_supervisor

def create_supervisor(system_prompt: str, tools: list) -> Runnable:
    """Creates the supervisor LLM chain using a system prompt and a fixed list of tools."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])
    llm = get_llm()
    chain = prompt | llm.bind_tools(tools=tools)
    return chain

def create_entry_node(assistant_name: str, new_dialog_state: str) -> Callable:
    """Handoff between the supervisor and one of the delegated workflows
    so that the assistant is clear about the current scope."""
    def entry_node(state: State) -> dict:
        tool_call_id = state["messages"][-1].tool_calls[0]["id"]
        return {
            "messages": [
                ToolMessage(
                    content=f"""The assistant is now the {assistant_name}. 
Reflect on the above conversation between the supervisor agent and the user.
The user's intent is unsatisfied. Use the provided tools to assist the user.
The task is not complete until you have successfully invoked the appropriate tool.
If the user changes their mind, or needs help with other tasks, 
call the 'CompleteOrEscalate' tool call to let the supervisor agent take control.
Do not mention who you are - just act as a proxy assistant for the supervisor.
Remember, you are {assistant_name}.
""",
                    tool_call_id=tool_call_id,
                )
            ],
            "dialog_state": new_dialog_state,
        }

    return entry_node

def create_assistant(system_prompt: str, tool_tag: str = None) -> Runnable:
    """Creates a delegated assistant LLM chain, optionally loading tools by tag."""
    tools = tools_registry.get_tools_by_tag(tool_tag) + [CompleteOrEscalate]

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])
    llm = get_llm()
    chain = prompt | llm.bind_tools(tools=tools)
    return chain

def create_node(runnable: Runnable) -> Callable:
    """Creates a runnable assistant graph node."""
    def node(state: State):
        response = runnable.invoke(state)
        return {"messages": [response]}
    return node

def route_to_workflow(state: State) -> str:
    """Routes to the last active assistant/workflow in the dialog_state stack."""
    supervisor = get_supervisor()
    dialog_state = state.get("dialog_state")

    # return to supervisor when in no state
    if not dialog_state:
        return supervisor["name"]

    # Validate against known assistant names
    last_assistant = dialog_state[-1]
    valid_assistants = list(get_registry().keys()) + supervisor["name"]
    if last_assistant not in valid_assistants:
        # gracefully return to supervisor
        return supervisor["name"]
    return last_assistant

def route_supervisor(state: State):
    """Determines the next node after the supervisor runs, based on the tool call."""
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        assistant_registry = get_registry()
        for assistant_name, cfg in assistant_registry.items():
            if tool_calls[0]["name"] == cfg["entry_tool"].__name__:
                return f"enter_{assistant_name}"
        raise ValueError("Unknown tool")
    raise ValueError("Invalid route")

def create_assistant_route_tools(assistant_name: str):
    """Creates a route function for a delegated assistant. 
    
    Decides where to send control based on tool call results: safe tool node, 
    sensitive tool node, or back to supervisor.
    """
    def route_node(state: State):
        next_node = tools_condition(state)
        # No tools are invoked
        if next_node == END:
            return END
        # Control flow should be passed back to the supervisor agent.
        tool_calls = state["messages"][-1].tool_calls
        did_cancel = any(tool_call["name"] == "CompleteOrEscalate" for tool_call in tool_calls)
        if did_cancel:
            return "leave_skill"
        # control flow should be passed to a tool.
        user_management_sensitive_tools = tools_registry.get_tools_by_tags(assistant_name, "sensitive")
        sensitive_tools_names = [tool.name for tool in user_management_sensitive_tools]
        if any(tool_call["name"] in sensitive_tools_names for tool_call in tool_calls):
            return f"sensitive_tools_{assistant_name}"
        return f"safe_tools_{assistant_name}"
    return route_node
