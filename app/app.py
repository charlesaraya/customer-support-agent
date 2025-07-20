import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
load_dotenv()

from app.routes import router

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"])
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    return app
