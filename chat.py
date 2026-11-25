import os
import sys
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver


from agent import build_agent

load_dotenv()
DB_URI = os.environ["DB_URI"]

def text_of(content) -> str:
    """Gemini may return a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    return "".join(
        b.get("text", "") if isinstance(b, dict) else str(b) for b in content
    )
def main():
    # Resume a thread: python chat.py <thread_id>   |   new thread: python chat.py
    thread_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        checkpointer.setup()          # creates the tables on first run (idempotent)
        agent = build_agent(checkpointer)

        print(f"Thread: {thread_id}")
        print("Type 'exit' to quit. Resume later with: python chat.py", thread_id, "\n")

        # Show prior history if resuming
        state = agent.get_state(config)
        for m in state.values.get("messages", []) if state.values else []:
            if m.type in ("human", "ai") and text_of(m.content).strip():
                who = "You" if m.type == "human" else "Agent"
                print(f"{who}: {text_of(m.content)}\n")

        while True:
            try:
                user = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user.lower() in {"exit", "quit"}:
                break
            if not user:
                continue

            result = agent.invoke(
                {"messages": [{"role": "user", "content": user}]},
                config,
            )
            print(f"\nAgent: {text_of(result['messages'][-1].content)}\n")


if __name__ == "__main__":
    main()