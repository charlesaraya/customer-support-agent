from typing import Optional, Literal
from datetime import datetime
import uuid
from enum import Enum

from sqlmodel import SQLModel, Field

def generate_id():
    return str(uuid.uuid4())

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=generate_id, primary_key=True)
    name: str
    email: str
    password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Chat(SQLModel, table=True):
    __tablename__ = "chats"
    id: str = Field(default_factory=generate_id, primary_key=True)
    user_id: str
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class RoleEnum(str, Enum):
    user = "user"
    ai = "ai"

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: str = Field(foreign_key="chats.id")
    role: RoleEnum
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
