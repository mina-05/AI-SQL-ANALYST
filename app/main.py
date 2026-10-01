import logging
import re
import uuid
from pathlib import Path

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from . import agent, auth, config, db, llm, rag, store
from .chart import suggest_chart
from .repair import QueryFailed, run_with_repair
from .validator import UnsafeSQLError, validate_sql

log = logging.getLogger("uvicorn.error")
if config.SECRET_KEY_IS_RANDOM:
    log.warning("SECRET_KEY is not set: using a random key, so everyone is signed out on restart.")

app = FastAPI(title="AI SQL Analyst")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

OLLAMA_DOWN = "Could not reach Ollama. Check that it is running and the model is pulled."
MYSQL_DOWN = "Could not connect to MySQL. Check your .env settings."


class Credentials(BaseModel):
    username: str
    password: str


class AskBody(BaseModel):
    question: str
    conversation_id: str | None = None
    explain: bool = True


class SQLBody(BaseModel):
    sql: str


def _conversation_id(value) -> str:
    return value if value and re.fullmatch(r"[A-Za-z0-9-]{8,64}", value) else uuid.uuid4().hex


def _schema_text() -> str:
    try:
        return db.schema_as_text(db.get_schema())
    except SQLAlchemyError:
        raise HTTPException(503, MYSQL_DOWN)


# ------------------------------------------------------------------ auth
@app.get("/api/health")
def health():
    return {"status": "ok"}


def _check_credentials(c: Credentials):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", c.username):
        raise HTTPException(400, "Username must be 3-40 characters: letters, numbers, dot, dash or underscore.")
    if len(c.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")


@app.post("/api/auth/register")
def register(c: Credentials):
    if not config.ALLOW_REGISTRATION:
        raise HTTPException(403, "Registration is disabled.")
    _check_credentials(c)
    try:
        user_id = store.create_user(c.username, auth.hash_password(c.password))
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"token": auth.make_token(user_id), "username": c.username}


@app.post("/api/auth/login")
def login(c: Credentials):
    user = store.get_user_by_name(c.username.strip())
    ok = auth.verify_password(c.password, user["password_hash"] if user else auth.DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(401, "Wrong username or password.")
    return {"token": auth.make_token(user["id"]), "username": user["username"]}


@app.get("/api/auth/me")
def me(user: dict = Depends(auth.current_user)):
    return {"username": user["username"]}


# ------------------------------------------------------------------ analysis
@app.get("/api/schema")
def schema(user: dict = Depends(auth.current_user)):
    try:
        return db.get_schema()
    except SQLAlchemyError:
        raise HTTPException(503, MYSQL_DOWN)


@app.post("/api/ask")
def ask(body: AskBody, user: dict = Depends(auth.current_user)):
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Enter a question first.")
    conv = _conversation_id(body.conversation_id)
    schema_text = _schema_text()
    history = store.recent_turns(user["id"], conv, config.HISTORY_TURNS)
    context = rag.format_context(rag.search(question))

    try:
        raw_sql = llm.question_to_sql(question, schema_text, history, context)
        sql, df, attempts = run_with_repair(question, schema_text, raw_sql)
    except UnsafeSQLError as e:
        raise HTTPException(422, f"Query blocked: {e}")
    except QueryFailed as e:
        raise HTTPException(422, f"The SQL still failed after {len(e.attempts)} attempts. Last error: {e.error}")
    except requests.RequestException:
        raise HTTPException(503, OLLAMA_DOWN)

    insight = None
    if body.explain and not df.empty:
        try:
            insight = llm.explain_result(question, sql, df.head(20).to_string(index=False))
        except requests.RequestException:
            insight = None

    store.add_history(user["id"], conv, "quick", question, sql, len(df), insight)
    return {
        "conversation_id": conv,
        "sql": sql,
        "columns": list(df.columns),
        "rows": db.rows_of(df),
        "insight": insight,
        "chart": suggest_chart(df),
        "repairs": attempts,
    }


@app.post("/api/agent")
def run_agent(body: AskBody, user: dict = Depends(auth.current_user)):
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Enter a question first.")
    conv = _conversation_id(body.conversation_id)
    schema_text = _schema_text()
    history = store.recent_turns(user["id"], conv, config.HISTORY_TURNS)

    try:
        result = agent.run_agent(question, schema_text, history)
    except requests.RequestException:
        raise HTTPException(503, OLLAMA_DOWN)

    store.add_history(
        user["id"], conv, "agent", question,
        "\n\n".join(result["queries"]) or None, len(result["rows"]), result["answer"],
    )
    return {"conversation_id": conv, **result}


@app.post("/api/explain")
def explain(body: SQLBody, user: dict = Depends(auth.current_user)):
    try:
        return {"explanation": llm.explain_query(validate_sql(body.sql, config.MAX_ROWS))}
    except UnsafeSQLError as e:
        raise HTTPException(422, f"Query blocked: {e}")
    except requests.RequestException:
        raise HTTPException(503, OLLAMA_DOWN)


@app.post("/api/optimize")
def optimize(body: SQLBody, user: dict = Depends(auth.current_user)):
    try:
        sql = validate_sql(body.sql, config.MAX_ROWS)
        plan = db.explain_plan(sql)
        return {"plan": plan, "suggestions": llm.optimize_query(sql, db.schema_as_text(db.get_schema()), plan)}
    except UnsafeSQLError as e:
        raise HTTPException(422, f"Query blocked: {e}")
    except requests.RequestException:
        raise HTTPException(503, OLLAMA_DOWN)
    except SQLAlchemyError as e:
        raise HTTPException(422, f"MySQL could not analyze this query: {getattr(e, 'orig', e)}")


# ------------------------------------------------------------------ history
@app.get("/api/history")
def history(user: dict = Depends(auth.current_user)):
    return store.list_history(user["id"])


@app.delete("/api/history")
def clear_history(user: dict = Depends(auth.current_user)):
    store.clear_history(user["id"])
    return {"cleared": True}


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")
