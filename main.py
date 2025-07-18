from langchain_core.messages import HumanMessage

from app.graph import build_graph

def graph_updates(graph, thread_id: str, user_input: str):
    config = {"configurable": {"thread_id": thread_id}}
    messages = [HumanMessage(content=user_input)]
    messages = graph.invoke({"messages": messages}, config)
    print("Assistant:", messages["messages"][-1].content)

def main():
    graph = build_graph()
    thread_id = "1"
    print("Type 'exit' to quit.")
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
            graph_updates(graph, thread_id, user_input)
        except Exception as e:
            print(f"error: {e}")
            break

if __name__ == '__main__':
    main()