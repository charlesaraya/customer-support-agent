import os

from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
load_dotenv()

sqlite_file = os.environ.get("SQLITE_DB_NAME")
engine = create_engine(f"sqlite:///{sqlite_file}", echo=True)

def get_session():
    with Session(engine) as session:
        yield session