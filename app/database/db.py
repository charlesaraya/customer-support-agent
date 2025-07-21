import os

from sqlmodel import create_engine, Session
from sqlalchemy import event

from dotenv import load_dotenv
load_dotenv()

sqlite_file = os.environ.get("SQLITE_DB_NAME")
engine = create_engine(f"sqlite:///{sqlite_file}", echo=True)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

def get_session():
    with Session(engine) as session:
        yield session