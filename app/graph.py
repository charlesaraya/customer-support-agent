from typing import Annotated, TypedDict

import sqlite3

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import get_llm
from app.tools import TOOLS
from app.config import get_agent_connection_string

class State(TypedDict):
    # reducer `add_messages` ensures messages are appended and not overwritten
    messages: Annotated[list, add_messages] 

llm = get_llm(tools=TOOLS)

sys_msg = SystemMessage(content="You are a helpful customer support assistant.")

def chatbot(state: State):
    response = llm.invoke([sys_msg] + state["messages"])
    # response.response_metadata (token_usage, finish_reason, etc.)
    return {"messages": [response]}

def build_graph():
    graph_builder = StateGraph(State)

    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(TOOLS))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")

    db_string = get_agent_connection_string()
    conn = sqlite3.connect(db_string, check_same_thread=False)
    memory = SqliteSaver(conn)
    return graph_builder.compile(name="Customer Support Graph", checkpointer=memory)

def graph_updates(graph, thread_id: str, user_input: str):
    config = {"configurable": {"thread_id": thread_id}}
    messages = [HumanMessage(content=user_input)]
    messages = graph.invoke({"messages": messages}, config)
    # print("Assistant:", messages["messages"][-1].content)
    return messages