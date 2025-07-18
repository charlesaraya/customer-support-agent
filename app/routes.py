from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlmodel import Session

from app.database import db, models, queries
from app.auth import hash_password, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/signup")
def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/signup")
def signup(request: Request, name: str = Form(), email: str = Form(), password: str = Form(), session: Session = Depends(db.get_session)):
    user = queries.get_user_by_email(session, email)
    if user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Email already exists"})
    hashed_password = hash_password(password)
    user = models.User(name=name, email=email, password=hashed_password)
    queries.create_user(session, user)
    return RedirectResponse("/login", status_code=302)


@router.post("/login")
def login(request: Request, email: str = Form(), password: str = Form(), session: Session = Depends(db.get_session)):
    user = queries.get_user_by_email(session, email)
    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    request.session["user_id"] = user.id
    return RedirectResponse("/chat", status_code=302)


@router.get("/chat")
def chat_form(request: Request, session: Session = Depends(db.get_session)):
    user_id = request.session.get("user_id")
    user = queries.get_user_by_id(session, user_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user": user.name})