# LangGraph Deep Agent Chatbot with PostgreSQL Checkpoints

A terminal chatbot built with [LangGraph](https://langchain-ai.github.io/langgraph/) and [`deepagents`](https://github.com/langchain-ai/deepagents), powered by Google Gemini. Every step of every conversation is saved to PostgreSQL, so you can quit the app, come back later, and continue exactly where you left off.

---

## Why this project exists

Most simple chatbots lose their memory the moment the script stops. This project solves that and doubles as a learning project for:

- **Checkpointing**: how LangGraph saves agent state after every graph step.
- **Postgres integration**: using `PostgresSaver` as a durable checkpoint store instead of in-memory state.
- **Deep agents**: an agent that can plan, use tools, and delegate to sub-agents.
- **Tool calling**: giving Gemini real functions (time lookup, calculator) it can call.
- **Time travel**: replaying or branching a conversation from any earlier checkpoint.

---

## How it works

```
 Terminal (chat.py)
        |
        v
 Deep Agent (agent.py)  <---->  Gemini (langchain-google-genai)
        |      \
        |       +--> Tools (tools.py): get_current_time, calculate
        v
 PostgresSaver  --->  PostgreSQL (Docker, port 5433)
                      tables: checkpoints, checkpoint_blobs,
                              checkpoint_writes, checkpoint_migrations
```

Key concepts:

| Concept | Meaning |
|---|---|
| `thread_id` | The conversation key. Same ID = same memory. New ID = fresh conversation. |
| Checkpoint | A snapshot of agent state, saved after every graph step (user message, model call, tool result, final answer). |
| `parent_checkpoint_id` | Links each checkpoint to the previous one, which makes time travel possible. |
| `checkpointer.setup()` | Creates the Postgres tables on first run. Safe to call every time. |

---

## Project structure

```
deepagent-chat/
├── .env                  # secrets and config (never commit this)
├── .gitignore
├── docker-compose.yml    # PostgreSQL (and optional pgAdmin)
├── requirements.txt
├── tools.py              # tools the agent can call
├── agent.py              # builds the deep agent + attaches the checkpointer
├── chat.py               # terminal chat loop
└── README.md
```

---

## Prerequisites

- Python 3.11 or newer
- Docker Desktop (running)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- Optional: pgAdmin 4 to browse the database

---

## Setup

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Start PostgreSQL

Make sure `docker-compose.yml` looks like this. Port **5433** on your machine maps to 5432 inside the container, which avoids clashing with a local Postgres install:

```yaml
services:
  postgres:
    image: postgres:16
    container_name: deepagent-pg
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: deepagent
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```bash
docker compose up -d
docker ps
```

You should see `deepagent-pg` with `0.0.0.0:5433->5432/tcp`.

### 3. Configure environment variables

Create `.env` in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
DB_URI=postgresql://postgres:postgres@localhost:5433/deepagent?sslmode=disable
```

Then create `.gitignore` so secrets are never committed:

```
.env
.venv/
__pycache__/
```

### 4. Run the chatbot

Start a new conversation:

```bash
python chat.py
```

The app prints a thread ID. Resume that conversation later:

```bash
python chat.py <thread_id>
```

Type `exit` to quit.

Try prompts like:

- `What time is it in Tokyo?`
- `What is 15% of 2480?`
- `What time is it in London, and what is 18 * 24?` (uses both tools)

---

## Inspecting the database

### With psql

```bash
docker exec -it deepagent-pg psql -U postgres -d deepagent
```

```sql
\dt

SELECT thread_id, count(*) AS checkpoints
FROM checkpoints
GROUP BY thread_id;

SELECT thread_id, checkpoint_id, parent_checkpoint_id
FROM checkpoints
ORDER BY checkpoint_id DESC
LIMIT 10;
```

### With pgAdmin

Right-click **Servers -> Register -> Server...** and use:

| Field | Value |
|---|---|
| Host name/address | `localhost` |
| Port | `5433` |
| Maintenance database | `postgres` |
| Username | `postgres` |
| Password | `postgres` |

Then browse to **deepagent -> Schemas -> public -> Tables**. Right-click **Tables -> Refresh** if nothing appears (tables are created on the first run of `chat.py`).

If pgAdmin itself runs in Docker, use the service name `postgres` as host and port `5432` instead.

---

## Experiments for learning

**1. View checkpoint history of a thread**

```python
for snap in agent.get_state_history(config):
    print(snap.config["configurable"]["checkpoint_id"], snap.next)
```

**2. Time travel (branch from an older checkpoint)**

```python
old = {"configurable": {"thread_id": thread_id, "checkpoint_id": "<id from history>"}}
agent.invoke({"messages": [{"role": "user", "content": "Try a different answer"}]}, old)
```

**3. Crash test**: stop the script mid-conversation with `Ctrl+C`, restart with the same thread ID, and confirm nothing was lost.

---

## Troubleshooting

### Docker and Postgres

| Problem | Cause | Fix |
|---|---|---|
| `password authentication failed for user "postgres"` in pgAdmin or Python | Another Postgres (for example a local PostgreSQL 17 install) is using the same port, so you are not reaching the container | Use port `5433` for the container as shown above. Check with `netstat -ano \| findstr :5432` (Windows) or `lsof -i :5432` (macOS/Linux). |
| `password authentication failed` even on the right port | The `POSTGRES_*` variables only apply the first time the volume is created | Run `docker compose down -v` (**deletes all data**), then `docker compose up -d` |
| `connection refused` / timeout | Container is not running | `docker ps`, then `docker compose logs postgres`, then `docker compose up -d` |
| `port is already allocated` | Port clash with another service | Change the left side of the mapping, for example `"5434:5432"`, and update `DB_URI` |
| `docker: command not found` or daemon errors | Docker Desktop is not running | Start Docker Desktop and wait until it says it is running |
| Tables missing in pgAdmin | `setup()` has not run yet, or the tree is stale | Run `python chat.py`, send one message, then refresh the Tables node |

### Python and dependencies

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Virtual environment not active or dependencies not installed | Activate `.venv`, then `pip install -r requirements.txt` |
| `KeyError: 'DB_URI'` | `.env` missing or not in the folder you run from | Create `.env` in the project root and run `python chat.py` from there |
| `create_deep_agent() got an unexpected keyword argument 'system_prompt'` | Your `deepagents` version uses a different parameter name | Run `pip show deepagents`. Try `instructions=` instead of `system_prompt=` in `agent.py`. |
| `psycopg` import or `libpq` errors | Postgres driver missing | `pip install "psycopg[binary,pool]"` |
| Output printed as a list or dict instead of text | Gemini returned content blocks | Keep the `text_of()` helper in `chat.py` |

### Gemini

| Problem | Cause | Fix |
|---|---|---|
| `404 model not found` | Model name changed or retired | Set `GEMINI_MODEL` in `.env` to a currently available model listed in Google AI Studio |
| `API key not valid` / 400 or 403 | Wrong, deleted, or restricted key | Generate a new key in AI Studio, update `.env`, and restart the script |
| `429 quota exceeded` / `RESOURCE_EXHAUSTED` | Free-tier rate limit | Wait a minute, use a lighter model, or enable billing |
| Tool is never called | Weak tool docstring | Make each tool's docstring clear. Gemini uses it to decide when to call the tool. |

### Conversation memory

| Problem | Cause | Fix |
|---|---|---|
| The agent forgot the earlier conversation | You started `chat.py` without a thread ID, which creates a new thread | Pass the old ID: `python chat.py <thread_id>`. List IDs with the SQL query above. |
| Errors after changing the agent, tools, or state schema | Old checkpoints no longer match | Start a new thread, or clear data with `TRUNCATE checkpoints, checkpoint_blobs, checkpoint_writes;` |

### Reset everything

```bash
docker compose down -v
docker compose up -d
```

This deletes all saved conversations. Tables are recreated on the next run.

---

## Security notes

- Never commit `.env` or paste your API key into screenshots, chats, or issues. If a key is exposed, delete it in Google AI Studio and create a new one.
- The default `postgres`/`postgres` credentials are for local development only. Use strong credentials before exposing the database anywhere.
- The `calculate` tool uses a restricted `eval`. For production, replace it with a proper math parser such as `numexpr` or `sympy`.

---

## Next steps

- Stream responses with `agent.stream(..., stream_mode="messages")`
- Switch to `AsyncPostgresSaver` for async apps
- Add `PostgresStore` for long-term memory across threads
- Add a web search tool
- Wrap the agent in a FastAPI or Express endpoint and build a React chat UI

---

## Tech stack

Python, LangGraph, deepagents, LangChain, Google Gemini, PostgreSQL 16, Docker, psycopg 3
