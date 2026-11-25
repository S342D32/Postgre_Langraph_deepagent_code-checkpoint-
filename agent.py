import os
from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import get_current_time, calculate

load_dotenv()

SYSTEM_PROMPT = """You are a helpful assistant running in a terminal.
Use tools when they help. For multi-step tasks, plan first using your todo list.
Keep answers concise."""


def build_agent(checkpointer):
    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        temperature=0.3,
    )
    return create_deep_agent(
        model=model,
        tools=[get_current_time, calculate],
        system_prompt=SYSTEM_PROMPT,   # older deepagents versions call this `instructions`
        checkpointer=checkpointer,     # <- the Postgres integration point
    )