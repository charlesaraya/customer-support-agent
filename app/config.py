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