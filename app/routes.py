from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlmodel import Session

from app.database import db, models, queries
from app.auth import hash_password, verify_password
from app.graph import graph_updates

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
    if not user_id:
        return RedirectResponse("/login", status_code=401)
    user = queries.get_user_by_id(session, user_id)
    chats = queries.get_chats_by_user(session, user_id)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user": user,
        "chats": chats,
        "selected_chat": None,
    })


@router.post("/chat/new")
def new_chat(request: Request, session: Session = Depends(db.get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login")

    chat = models.Chat(user_id=user_id)
    chat = queries.create_chat(session, chat)
    return RedirectResponse(f"/chat/{chat.id}", status_code=302)


@router.get("/chat/{chat_id}")
def chat_page(request: Request, chat_id: str, session: Session = Depends(db.get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=401)

    user = queries.get_user_by_id(session, user_id)

    chats = queries.get_chats_by_user(session, user_id)
    selected_chat = queries.get_chat_by_id(session, chat_id)

    chat_messages = queries.get_messages_by_chat_id(session, chat_id)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user": user,
        "chats": chats,
        "selected_chat": selected_chat,
        "messages": chat_messages,
    })


@router.post("/chat/{chat_id}/send")
async def send_message(request: Request, chat_id: str, user_message: str = Form(...), session: Session = Depends(db.get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=401)

    human_message = models.Message(chat_id=chat_id, role='user', content=user_message)
    _ = queries.create_chat(session, human_message)

    # Access the graph instance stored in app state
    graph = request.app.state.graph

    # Process user message via LangGraph
    messages = graph_updates(graph, thread_id=chat_id, user_input=user_message)

    # Get assistant's reply (last message)
    reply = messages["messages"][-1].content

    ai_message = models.Message(chat_id=chat_id, role='ai', content=reply)
    _ = queries.create_chat(session, ai_message)

    return templates.TemplateResponse("partials/message.html", {
        "request": request,
        "user_message": user_message,
        "ai_message": reply,
    })


@router.delete("/chat/{chat_id}")
def delete_chat(request: Request, chat_id: str, session: Session = Depends(db.get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=401)

    result = queries.delete_chat_by_id(session, chat_id)
    if not result:
        raise HTTPException(status_code=404, detail="Chat not found")

    return HTMLResponse(content="", status_code=200)