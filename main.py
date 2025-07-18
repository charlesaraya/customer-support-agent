from langchain_core.messages import HumanMessage

from app.graph import build_graph

def stream_graph_updates(graph, user_input: str):
    messages = [HumanMessage(content=user_input)]
    messages = graph.invoke({"messages": messages})
    print("Assistant:", messages["messages"][-1].content)

def main():
    graph = build_graph()
    print("Type 'exit' to quit.")
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
            stream_graph_updates(graph, user_input)
        except Exception as e:
            print(f"error: {e}")
            break

if __name__ == '__main__':
    main()