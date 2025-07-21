from typing import Annotated, TypedDict

import sqlite3

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import get_llm
from app.tools import get_tools, get_safe_tools, get_sensitive_tools, get_sensitive_tools_names
from app.config import get_agent_connection_string

SENSITIVE_NODE = "sensitive_tools"

class State(TypedDict):
    # reducer `add_messages` ensures messages are appended and not overwritten
    messages: Annotated[list, add_messages] 

llm = get_llm(tools=get_tools())

sys_msg = SystemMessage(content="You are a helpful customer support assistant.")

def chatbot(state: State):
    response = llm.invoke([sys_msg] + state["messages"])
    # response.response_metadata (token_usage, finish_reason, etc.)
    return {"messages": [response]}

def route_tools(state: State):
    next_node = tools_condition(state)
    # No tools are invoked
    if next_node == END:
        return END
    ai_message = state["messages"][-1]
    first_tool_call = ai_message.tool_calls[0]
    if first_tool_call["name"] in get_sensitive_tools_names():
        return "sensitive_tools"
    return "safe_tools"

def build_graph():
    graph_builder = StateGraph(State)

    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("safe_tools", ToolNode(get_safe_tools()))
    graph_builder.add_node("sensitive_tools", ToolNode(get_sensitive_tools()))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", route_tools, ["safe_tools", "sensitive_tools", END])
    graph_builder.add_edge("safe_tools", "chatbot")
    graph_builder.add_edge("sensitive_tools", "chatbot")

    db_string = get_agent_connection_string()
    conn = sqlite3.connect(db_string, check_same_thread=False)
    memory = SqliteSaver(conn)

    return graph_builder.compile(
        name="Customer Support Graph",
        checkpointer=memory,
        interrupt_before=["sensitive_tools"],
    )

def graph_updates(graph, thread_id: str, user_input: str | None = None):
    config = {"configurable": {"thread_id": thread_id}}
    messages = None
    if user_input:
        messages = {"messages": [HumanMessage(content=user_input)]}
    messages = graph.invoke(messages, config)
    return messages

def graph_reject_tool_call(graph, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
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
