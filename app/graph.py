from typing import Annotated, TypedDict, Optional, Literal, Callable

import sqlite3

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AnyMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from langchain_core.runnables import RunnableConfig

from app.config import get_llm
import app.tools as tools
from app.config import get_agent_connection_string
from app.prompts import SUPERVISOR_AGENT_SYSTEM_PROMPT, ORDER_MANAGEMENT_ASSISTANT_SYSTEM_PROMPT, KNOWLEDGE_BASE_ASSISTANT_SYSTEM_PROMPT

SENSITIVE_NODE = "sensitive_tools"

def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop the state."""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    dialog_state: Annotated[
        list[
            Literal[
                "supervisor",
                "order_management",
                "knowledge_base",
            ]
        ],
        update_dialog_stack,
    ]

def user_info(state: State, config: RunnableConfig):
    tools.get_user_info.invoke(state)

supervisor_llm = get_llm(tools=[
    tools.ToOrderManagementAssistant,
    tools.ToKnowledgeBaseAssistant,
])

def supervisor(state: State):
    assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_AGENT_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
    ])
    assistant_runnable = assistant_prompt | supervisor_llm
    response = assistant_runnable.invoke(state)
    # response.response_metadata (token_usage, finish_reason, etc.)
    return {"messages": [response]}

order_management_tools = tools.tools_registry.get_tools_by_tag("order_management")
order_management_llm = get_llm(tools=order_management_tools + [tools.CompleteOrEscalate])

def order_management_assistant(state: State):
    assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", ORDER_MANAGEMENT_ASSISTANT_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
    ])
    assistant_runnable = assistant_prompt | order_management_llm
    response = assistant_runnable.invoke(state)
    return {"messages": [response]}

knowledge_base_tools = tools.tools_registry.get_tools_by_tag("order_management")
knowledge_base_llm = get_llm(tools=knowledge_base_tools + [tools.CompleteOrEscalate])

def knowledge_base_assistant(state: State):
    assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", KNOWLEDGE_BASE_ASSISTANT_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
    ])
    assistant_runnable = assistant_prompt | knowledge_base_llm
    response = assistant_runnable.invoke(state)
    return {"messages": [response]}

def create_entry_node(assistant_name: str, new_dialog_state: str) -> Callable:
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

def pop_dialog_state(state: State) -> dict:
    """Pop the dialog stack and return to the supervisor agent.

    This lets the full graph explicitly track the dialog flow and delegate control
    to specific sub-graphs.
    """

    messages = []
    if state["messages"][-1].tool_calls:
        # Note: Doesn't currently handle the edge case where the llm performs parallel tool calls
        messages.append(
            ToolMessage(
                content="Resuming dialog with the supervisor agent. Please reflect on the past conversation and assist the user as needed.",
                tool_call_id=state["messages"][-1].tool_calls[0]["id"],
            )
        )
    return {
        "dialog_state": "pop",
        "messages": messages,
    }

def route_order_management_tools(state: State):
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
    order_management_sensitive_tools = tools.tools_registry.get_tools_by_tags("order_management", "sensitive")
    sensitive_tools_names = [tool.name for tool in order_management_sensitive_tools]
    if any(tool_call["name"] in sensitive_tools_names for tool_call in tool_calls):
        return "sensitive_tools_order_management"
    return "safe_tools_order_management"

def route_knowledge_base_tools(state: State):
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
    knowledge_base_sensitive_tools = tools.tools_registry.get_tools_by_tags("knowledge_base", "sensitive")
    sensitive_tools_names = [tool.name for tool in knowledge_base_sensitive_tools]
    if any(tool_call["name"] in sensitive_tools_names for tool_call in tool_calls):
        return "sensitive_tools_knowledge_base"
    return "safe_tools_knowledge_base"

def route_supervisor(state: State):
    route = tools_condition(state)
    # No tools are invoked
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        if tool_calls[0]["name"] == tools.ToOrderManagementAssistant.__name__:
            return "enter_order_management"
        elif tool_calls[0]["name"] == tools.ToKnowledgeBaseAssistant.__name__:
            return "enter_knowledge_base"
        raise ValueError("Unknown tool")
    raise ValueError("Invalid route")

# Each delegated workflow can directly respond to the user
# When the user responds, we want to return to the currently active workflow
def route_to_workflow(state: State) -> Literal["supervisor", "order_management", "knowledge_base"]:
    """If we are in a delegated state, route directly to the appropriate assistant."""

    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return "supervisor"
    return dialog_state[-1]

def build_graph():
    graph_builder = StateGraph(State)

    # Nodes
    graph_builder.add_node("fetch_user_info", user_info)
    graph_builder.add_node("supervisor", supervisor)

    # Order Management Assistant Nodes
    graph_builder.add_node("enter_order_management", create_entry_node("Order Management Assistant", "order_management"))
    graph_builder.add_node("order_management", order_management_assistant)

    order_management_safe_tools = tools.tools_registry.get_tools_by_tags("order_management", "safe")
    graph_builder.add_node("safe_tools_order_management", ToolNode(order_management_safe_tools))

    order_management_sensitive = tools.tools_registry.get_tools_by_tags("order_management", "sensitive")
    graph_builder.add_node("sensitive_tools_order_management", ToolNode(order_management_sensitive))

    # Knowledge Base Assistant Nodes
    graph_builder.add_node("enter_knowledge_base", create_entry_node("Knowledge Base Assistant", "knowledge_base"))
    graph_builder.add_node("knowledge_base", knowledge_base_assistant)

    knowledge_base_safe_tools = tools.tools_registry.get_tools_by_tags("knowledge_base", "safe")
    graph_builder.add_node("safe_tools_knowledge_base", ToolNode(knowledge_base_safe_tools))

    knowledge_base_sensitive = tools.tools_registry.get_tools_by_tags("knowledge_base", "sensitive")
    graph_builder.add_node("sensitive_tools_knowledge_base", ToolNode(knowledge_base_sensitive))

    graph_builder.add_node("leave_skill", pop_dialog_state)

    # Edges
    graph_builder.add_edge(START, "fetch_user_info")
    graph_builder.add_conditional_edges("fetch_user_info", route_to_workflow)

    graph_builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        ["enter_order_management", "enter_knowledge_base", END],
    )
    graph_builder.add_edge("enter_order_management", "order_management")
    graph_builder.add_edge("enter_knowledge_base", "knowledge_base")

    graph_builder.add_conditional_edges(
        "order_management",
        route_order_management_tools,
        ["safe_tools_order_management", "sensitive_tools_order_management", "order_management", "leave_skill", END]
    )
    graph_builder.add_edge("safe_tools_order_management", "order_management")
    graph_builder.add_edge("sensitive_tools_order_management", "order_management")

    graph_builder.add_conditional_edges(
        "knowledge_base",
        route_knowledge_base_tools,
        ["safe_tools_knowledge_base", "sensitive_tools_knowledge_base", "knowledge_base", "leave_skill", END]
    )
    graph_builder.add_edge("safe_tools_knowledge_base", "knowledge_base")
    graph_builder.add_edge("sensitive_tools_knowledge_base", "knowledge_base")

    graph_builder.add_edge("leave_skill", "supervisor")

    # Short-term (within-thread) memory
    db_string = get_agent_connection_string()
    conn = sqlite3.connect(db_string, check_same_thread=False)
    memory = SqliteSaver(conn)

    # Long-term (cross-thread) memory
    in_memory_store = InMemoryStore()

    return graph_builder.compile(
        name = "Customer Support Graph",
        checkpointer = memory,
        store = in_memory_store,
        interrupt_before = [
            "sensitive_tools_order_management",
            "sensitive_tools_knowledge_base",
        ],
    )

def graph_updates(graph, thread_id: str, user_id: str, user_input: str | None = None):
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }
    messages = None
    if user_input:
        messages = {"messages": [HumanMessage(content=user_input)]}
    messages = graph.invoke(messages, config)
    return messages

def graph_reject_tool_call(graph, thread_id: str, user_id: str):
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }
    snapshot = graph.get_state(config)
    tool_id = snapshot.values["messages"][-1].tool_calls[0]["id"]
    messages = {
        "messages": [
            ToolMessage(
                tool_call_id = tool_id,
                content = f"The user rejected the tool call when asked for confirmation. Continue assisting the user, accounting for the user's input."
            )
        ]
    }
    messages = graph.invoke(messages, config)
    return messages
