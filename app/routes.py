from urllib.parse import urlencode
from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from google_auth_oauthlib.flow import Flow

from sqlmodel import Session

from app.database import db, models, queries
from app.auth import hash_password, verify_password
from app.graph import graph_updates, graph_reject_tool_call, SENSITIVE_NODE
from app.config import get_google_client_config, get_google_client_scopes, get_authorised_redirect_uris
from app.caching import cache_gmail_token, get_cached_gmail_token

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
        "google_credentials": bool(get_cached_gmail_token(user_id)),
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
        "google_credentials": bool(get_cached_gmail_token(user_id)),
    })


@router.post("/chat/{chat_id}/send")
async def send_message(request: Request, chat_id: str, user_message: str = Form(...), tool_confirmation: str = Form(None), session: Session = Depends(db.get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=401)

    # Access the graph instance stored in app state
    graph = request.app.state.graph

    # flow was interrupted by a sensitive tool
    if tool_confirmation:
        return _handle_tool_confirmation(request, chat_id, tool_confirmation, graph, session)

    queries.create_message(session, chat_id=chat_id, role='user', content=user_message)

    messages = graph_updates(graph, thread_id=chat_id, user_input=user_message)

     # Check for sensitive tool interruption
    snapshot = graph.get_state({"configurable": {"thread_id": chat_id}})
    if snapshot.next and SENSITIVE_NODE in snapshot.next[0]:
        confirmation_prompt = "This action requires permission to use a sensitive tool. Do you wish to proceed?"
        message = queries.create_message(session, chat_id=chat_id, role='ai', content=confirmation_prompt)

        return templates.TemplateResponse("partials/confirmation_message.html", {
            "request": request,
            "chat_id": chat_id,
            "message": message,
        })

    # Get assistant's reply (last message)
    reply = messages["messages"][-1].content

    queries.create_message(session, chat_id=chat_id, role='ai', content=reply)

    return templates.TemplateResponse("partials/message.html", {
        "request": request,
        "user_message": user_message,
        "ai_message": reply,
    })

def _handle_tool_confirmation(request, chat_id, tool_confirmation, graph, session):
    match tool_confirmation:
        case "accepted":
            # continue the graph execution
            messages = graph_updates(graph, thread_id=chat_id)
            content = "Confirmed ✅"
        case "rejected":
            messages = graph_reject_tool_call(graph, thread_id=chat_id)
            content = "Rejected ❌"
        case _:
            raise HTTPException(status_code=400, detail="invalid confirmation value")

    message = queries.create_message(session, chat_id=chat_id, role='user', content=content)
    reply = messages["messages"][-1].content
    message = queries.create_message(session, chat_id=chat_id, role='ai', content=reply)

    return templates.TemplateResponse("partials/confirmation_message_processed.html", {
        "request": request,
        "chat_id": chat_id,
        "message": message,
        "confirmation": tool_confirmation,
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

@router.get("/auth/gmail")
def auth_gmail(request: Request):
    flow = Flow.from_client_config(get_google_client_config(), scopes=get_google_client_scopes())
    flow.redirect_uri = get_authorised_redirect_uris()[0]

    referer_url = urlparse(request.headers.get("referer"))

    state_data = {"return_to": referer_url.path}
    state_str = urlencode(state_data)

    auth_url, _ = flow.authorization_url(
        access_type = "offline",  # get refresh token
        include_granted_scopes = "true",
        prompt = "consent",  # always show consent screen
        state=state_str,
    )
    #return RedirectResponse(auth_url)
    return HTMLResponse(f"""<script>window.location.href = "{auth_url}";</script>""")


@router.get("/auth/callback")
def auth_callback(request: Request):
    state = request.query_params.get("state")
    code = request.query_params.get("code")

    flow = Flow.from_client_config(get_google_client_config(), scopes=get_google_client_scopes())
    flow.redirect_uri = get_authorised_redirect_uris()[0]
    flow.fetch_token(code=code)

    credentials = flow.credentials

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=401)
    cache_gmail_token(user_id, {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }, credentials.expiry)

    state_data = parse_qs(state)
    return_to = state_data.get("return_to", ["/"])[0]

    return RedirectResponse(return_to, status_code=302)