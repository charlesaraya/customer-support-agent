import uvicorn

from app.graph import build_graph
from app.app import create_app

app = create_app()
graph = build_graph()
app.state.graph = graph

def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == '__main__':
    main()