from sqlmodel import Session, select
from ..models import User

def create_user(session: Session, user: User):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()

def get_user_by_id(session: Session, id: str):
    return session.exec(select(User).where(User.id == id)).first()