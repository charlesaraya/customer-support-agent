from sqlmodel import Session, select
from ..models import Message

def create_message(session: Session, message: Message):
    session.add(message)
    session.commit()
    session.refresh(message)
    return message

def get_messages_by_chat_id(session: Session, chat_id: str):
    return session.exec(select(Message).where(Message.chat_id == chat_id)).all()
