from sqlmodel import Session, select, delete
from ..models import Chat

def create_chat(session: Session, chat: Chat):
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat

def get_chats_by_user(session: Session, user_id: str):
    return session.exec(select(Chat).where(Chat.user_id == user_id)).all()

def get_chat_by_id(session: Session, id: str):
    return session.exec(select(Chat).where(Chat.id == id)).first()

def delete_chat_by_id(session: Session, id: str):
    result = session.exec(delete(Chat).where(Chat.id == id))
    session.commit()
    return result