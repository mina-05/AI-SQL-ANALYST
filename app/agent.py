"""Tool-calling analyst agent.

The model replies with one JSON action per step; we run the tool and feed the result back.
Tools: inspect_schema, search_docs, run_sql, final_answer.
Works with any Ollama model that can follow a JSON format (no native tool-calling API needed).
"""
import json
import re

from sqlalchemy.exc import SQLAlchemyError

from . import config, db, llm, rag
from .chart import suggest_chart
from .validator import UnsafeSQLError, validate_sql

AGENT_PROMPT = """You are a careful data analyst answering questions about a MySQL database.

Database schema:
{schema}

On each turn reply with exactly ONE JSON object and nothing else:
{{"thought": "short reasoning", "tool": "<tool name>", "args": {{...}}}}

Tools:
- inspect_schema: args {{}}. Shows the tables and columns again.
- search_docs: args {{"query": "..."}}. Looks up business definitions and rules.
- run_sql: args {{"sql": "SELECT ..."}}. Runs one read-only MySQL SELECT and returns the rows.
- final_answer: args {{"answer": "..."}}. Ends the task with your answer for the user.

Rules:
- Only SELECT queries. Use only tables and columns from the schema.
- Base every claim on query results or documents you actually retrieved. If the data cannot explain a "why" question, say what the data shows and what it cannot show.
- To explain a difference, compare numbers with queries (counts, averages, min/max) before answering.
- You have at most {max_steps} steps. Call final_answer by step {max_steps}.
{history}
User question: {question}

Work so far:
{scratchpad}
Your next JSON (step {step} of {max_steps}):"""

OBS_LIMIT = 1500


def _parse(raw: str):
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) and isinstance(obj.get("tool"), str) else None


def _scratchpad(steps: list) -> str:
    if not steps:
        return "(nothing yet)\n"
    lines = []
    for s in steps:
        lines.append(f"Step {s['step']}: {s['tool']} {json.dumps(s['args'])}")
        lines.append(f"Result: {s['observation']}")
    return "\n".join(lines) + "\n"


def _run_tool(tool: str, args: dict, schema_text: str):
    """Return (observation_text, dataframe_or_None, executed_sql_or_None)."""
    if tool == "inspect_schema":
        return schema_text, None, None
    if tool == "search_docs":
        hits = rag.search(str(args.get("query", "")))
        if not hits:
            return "No matching documents.", None, None
        return "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits), None, None
    if tool == "run_sql":
        try:
            sql = validate_sql(str(args.get("sql", "")), config.MAX_ROWS)
            df = db.run_query(sql)
        except UnsafeSQLError as e:
            return f"BLOCKED: {e}", None, None
        except SQLAlchemyError as e:
            return f"SQL ERROR: {getattr(e, 'orig', e)}", None, None
        text = f"{len(df)} row(s)\n" + (df.head(20).to_string(index=False) if len(df) else "")
        return text, df, sql
    return f"Unknown tool '{tool}'. Use inspect_schema, search_docs, run_sql or final_answer.", None, None


def run_agent(question: str, schema_text: str, history=None, max_steps: int | None = None) -> dict:
    max_steps = max_steps or config.AGENT_MAX_STEPS
    steps, queries = [], []
    last_df, answer = None, None

    for n in range(1, max_steps + 1):
        prompt = AGENT_PROMPT.format(
            schema=schema_text,
            history=llm.format_history(history),
            question=question,
            scratchpad=_scratchpad(steps),
            max_steps=max_steps,
            step=n,
        )
        action = _parse(llm._generate(prompt, json_mode=True))
        if action is None:
            steps.append({
                "step": n, "thought": "", "tool": "(invalid reply)", "args": {},
                "observation": "Your reply was not a JSON object with a 'tool' field. Reply with exactly one JSON object.",
            })
            continue

        tool = action["tool"]
        args = action.get("args") if isinstance(action.get("args"), dict) else {}
        thought = str(action.get("thought", ""))[:500]

        if tool == "final_answer":
            answer = str(args.get("answer", "")).strip() or "(The model gave an empty answer.)"
            steps.append({"step": n, "thought": thought, "tool": tool, "args": {}, "observation": ""})
            break

        observation, df, sql = _run_tool(tool, args, schema_text)
        if df is not None:
            last_df = df
            queries.append(sql)
        steps.append({
            "step": n, "thought": thought, "tool": tool, "args": args,
            "observation": observation[:OBS_LIMIT],
        })

    if answer is None:
        answer = (
            f"I could not reach a final answer within {max_steps} steps. "
            "The steps below show what I tried; try rephrasing or asking a narrower question."
        )

    result = {"answer": answer, "steps": steps, "queries": queries,
              "columns": [], "rows": [], "chart": None}
    if last_df is not None:
        result.update(columns=list(last_df.columns), rows=db.rows_of(last_df), chart=suggest_chart(last_df))
    return result
