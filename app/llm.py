import requests

from . import config
from .validator import clean_sql

SQL_PROMPT = """You are a MySQL expert. Convert the user's question into ONE MySQL SELECT query.

Database schema:
{schema}
{context}{history}
Rules:
- Use only the tables and columns listed above.
- If the question refers to earlier ones (for example "and for HR?" or "sort that by name"), use the conversation above to resolve it.
- Return only the SQL query. No explanation, no markdown.
- Never write INSERT, UPDATE, DELETE, DROP, or any statement that changes data.

Question: {question}
SQL:"""

INSIGHT_PROMPT = """A user asked: "{question}"
The SQL run was:
{sql}

The result (first rows):
{table}

In 2-3 plain sentences, explain what the result shows. Mention the key pattern or outlier.
Only use facts visible in the result. Do not guess at causes the data cannot show."""

FIX_PROMPT = """The MySQL query below failed. Fix it.

Database schema:
{schema}

User question: {question}

Failed query:
{sql}

MySQL error:
{error}

Return only the corrected single SELECT query. No explanation, no markdown."""

EXPLAIN_PROMPT = """Explain this MySQL query to a beginner in plain English.

{sql}

Walk through it clause by clause in a short numbered list (FROM, WHERE, GROUP BY, SELECT, ORDER BY, LIMIT - only the ones present).
End with one sentence saying what the query returns."""

OPTIMIZE_PROMPT = """You are a MySQL performance reviewer.

Schema:
{schema}

Query:
{sql}

MySQL EXPLAIN output:
{plan}

Give at most 4 concrete suggestions (indexes, rewriting, avoiding SELECT *, etc.).
If the query is already fine for its size, say so plainly. Use short bullet points.
If you suggest an index, include the CREATE INDEX statement."""


def _generate(prompt: str, json_mode: bool = False) -> str:
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    if json_mode:
        payload["format"] = "json"
    resp = requests.post(f"{config.OLLAMA_URL}/api/generate", json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()["response"]


def format_history(history) -> str:
    """Turn stored turns into a prompt block (this is the conversation memory)."""
    if not history:
        return ""
    lines = ["Earlier in this conversation (oldest first):"]
    for turn in history:
        lines.append(f"Q: {turn['question']}")
        if turn.get("sql"):
            lines.append(f"SQL: {turn['sql']}")
        if turn.get("answer"):
            lines.append(f"Summary: {turn['answer'][:300]}")
    return "\n".join(lines) + "\n"


def question_to_sql(question: str, schema_text: str, history=None, context: str = "") -> str:
    prompt = SQL_PROMPT.format(
        schema=schema_text, context=context, history=format_history(history), question=question
    )
    return clean_sql(_generate(prompt))


def explain_result(question: str, sql: str, table_text: str) -> str:
    return _generate(INSIGHT_PROMPT.format(question=question, sql=sql, table=table_text)).strip()


def fix_sql(question: str, schema_text: str, bad_sql: str, error: str) -> str:
    raw = _generate(FIX_PROMPT.format(schema=schema_text, question=question, sql=bad_sql, error=error))
    return clean_sql(raw)


def explain_query(sql: str) -> str:
    return _generate(EXPLAIN_PROMPT.format(sql=sql)).strip()


def optimize_query(sql: str, schema_text: str, plan: str) -> str:
    return _generate(OPTIMIZE_PROMPT.format(sql=sql, schema=schema_text, plan=plan)).strip()
