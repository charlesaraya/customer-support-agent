from typing import Optional, Literal, Callable

import sqlite3

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from langchain_core.runnables import RunnableConfig

import app.tools as tools
from app.config import get_agent_connection_string

from app.state import State
from app.assistants import factory, registry

SENSITIVE_NODE = "sensitive_tools"

def user_info(state: State, config: RunnableConfig):
    user_profile = tools.get_user_info.invoke(state)
    return user_profile


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

def build_graph():
    graph_builder = StateGraph(State)

    supervisor_registry = registry.get_supervisor()
    assistant_registry = registry.get_assistants()

    # Nodes
    graph_builder.add_node("fetch_user_info", user_info)
    graph_builder.add_edge(START, "fetch_user_info")
    graph_builder.add_conditional_edges(
        "fetch_user_info",
        factory.route_to_workflow,
        [name for name in assistant_registry] + [supervisor_registry["name"]]
    )

    # Supervisor node
    supervisor = factory.create_supervisor(registry.SUPERVISOR["system_prompt"], registry.SUPERVISOR["tools"])
    graph_builder.add_node(registry.SUPERVISOR["name"], factory.create_node(supervisor))

    # Assistant nodes
    interrupt_before_node = []
    for assistant_name, cfg in assistant_registry.items():
        # Entry Nodes
        entry_node_name = f"enter_{assistant_name}"
        entry_node = factory.create_entry_node(cfg["name"], assistant_name)
        graph_builder.add_node(entry_node_name, entry_node)

        # Assistant Nodes
        assistant = factory.create_assistant(
            system_prompt=cfg["system_prompt"],
            tool_tag=cfg.get("tool_tag"),
        )
        assistant_node = factory.create_node(assistant)
        graph_builder.add_node(assistant_name, assistant_node)

        # Tools
        safe_tools = tools.tools_registry.get_tools_by_tags(assistant_name, "safe")
        graph_builder.add_node(f"safe_tools_{assistant_name}", ToolNode(safe_tools))

        sensitive_tools = tools.tools_registry.get_tools_by_tags(assistant_name, "sensitive")
        graph_builder.add_node(f"sensitive_tools_{assistant_name}", ToolNode(sensitive_tools))

        # Routing
        graph_builder.add_edge(entry_node_name, assistant_name)
        routing_node = factory.create_assistant_route_tools(assistant_name)
        graph_builder.add_conditional_edges(
            assistant_name,
            routing_node,
            [
                f"safe_tools_{assistant_name}",
                f"sensitive_tools_{assistant_name}",
                assistant_name,
                "leave_skill",
                END,
            ],
        )
        graph_builder.add_edge(f"safe_tools_{assistant_name}", assistant_name)
        graph_builder.add_edge(f"sensitive_tools_{assistant_name}", assistant_name)

        interrupt_before_node.append(f"sensitive_tools_{assistant_name}")

    graph_builder.add_node("leave_skill", pop_dialog_state)

    # Conditional edge from supervisor to all entry nodes + END
    graph_builder.add_conditional_edges(
        supervisor_registry["name"],
        factory.route_supervisor,
        [f"enter_{name}" for name in assistant_registry] + [END],
    )

    graph_builder.add_edge("leave_skill", supervisor_registry["name"])

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
        interrupt_before = interrupt_before_node,
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
