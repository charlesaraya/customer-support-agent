from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.config import get_llm

class State(TypedDict):
    # reducer `add_messages` ensures messages are appended and not overwritten
    messages: Annotated[list, add_messages] 

llm = get_llm()

def chatbot(state: State):
    response = llm.invoke(state["messages"])
    # response.response_metadata (token_usage, finish_reason, etc.)
    return {"messages": [response]}

def build_graph():
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()