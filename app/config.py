import os

from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model

def get_llm(tools: list):
    llm_name = os.environ.get("LLM_NAME")
    llm_provider = os.environ.get("LLM_PROVIDER")

    if not llm_name:
        raise ValueError("failed to load LLM_NAME env")
    if not llm_provider:
        raise ValueError("failed to load LLM_PROVIDER env")

    llm = init_chat_model(model=llm_name, model_provider=llm_provider)
    if tools:
     llm = llm.bind_tools(tools)
    return llm

def get_agent_connection_string():
   return os.environ.get("AGENT_STATE_DB_NAME")

def get_authorised_redirect_uris() -> list:
   return ["http://localhost:8000/auth/callback"]

OAUTHLIB_RELAX_TOKEN_SCOPE = os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE")

def get_google_client_config():
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": get_authorised_redirect_uris(),
        }
    }

def get_google_client_scopes() -> list:
    return [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar",
        "openid",
        "email",
        "profile",
    ]