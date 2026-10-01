import json

import pandas as pd

from app import agent, db, llm, rag
from tests.conftest import register


def script(*actions):
    """Fake LLM that replies with the given actions (dicts or raw strings), one per call."""
    items = iter(actions)

    def fake(prompt, json_mode=False):
        a = next(items)
        return a if isinstance(a, str) else json.dumps(a)
    return fake


def act(tool, thought="", **args):
    return {"thought": thought, "tool": tool, "args": args}


def test_agent_runs_queries_then_answers(prompts, monkeypatch):
    ran = []
    monkeypatch.setattr(db, "run_query", lambda sql: ran.append(sql) or pd.DataFrame({"department": ["IT", "HR"], "avg": [102000.0, 63000.0]}))
    monkeypatch.setattr(llm, "_generate", script(
        act("search_docs", "check definitions", query="salary meaning"),
        act("run_sql", "compare departments", sql="SELECT department, AVG(salary) AS avg FROM employees GROUP BY department"),
        act("final_answer", "done", answer="IT averages 102000 vs HR 63000."),
    ))
    out = agent.run_agent("Why is IT higher?", "employees(id, department, salary)")
    assert out["answer"] == "IT averages 102000 vs HR 63000."
    assert [s["tool"] for s in out["steps"]] == ["search_docs", "run_sql", "final_answer"]
    assert "rupees" in out["steps"][0]["observation"]  # RAG tool really searched the docs
    assert len(ran) == 1 and out["queries"][0].startswith("SELECT department")
    assert out["columns"] == ["department", "avg"] and out["chart"]["type"] == "bar"


def test_agent_blocks_unsafe_sql_and_recovers(prompts, monkeypatch):
    ran = []
    monkeypatch.setattr(db, "run_query", lambda sql: ran.append(sql) or pd.DataFrame({"n": [1]}))
    monkeypatch.setattr(llm, "_generate", script(
        act("run_sql", sql="DELETE FROM employees"),
        act("final_answer", answer="I only run read-only queries."),
    ))
    out = agent.run_agent("delete everyone", "schema")
    assert ran == []
    assert out["steps"][0]["observation"].startswith("BLOCKED")
    assert out["rows"] == []


def test_agent_recovers_from_bad_json_and_unknown_tool(prompts, monkeypatch):
    monkeypatch.setattr(llm, "_generate", script(
        "I think we should look at salaries",          # not JSON
        act("make_coffee"),                            # unknown tool
        act("final_answer", answer="Done."),
    ))
    out = agent.run_agent("q", "schema")
    assert out["answer"] == "Done."
    assert "not a JSON object" in out["steps"][0]["observation"]
    assert "Unknown tool" in out["steps"][1]["observation"]


def test_agent_stops_at_step_limit(prompts, monkeypatch):
    monkeypatch.setattr(llm, "_generate", script(*[act("inspect_schema")] * 3))
    out = agent.run_agent("q", "schema", max_steps=3)
    assert "could not reach a final answer" in out["answer"]
    assert len(out["steps"]) == 3


def test_agent_sql_error_is_shown_to_model(prompts, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    def bad(sql):
        raise SQLAlchemyError("Unknown column 'nope'")
    monkeypatch.setattr(db, "run_query", bad)
    monkeypatch.setattr(llm, "_generate", script(act("run_sql", sql="SELECT nope FROM employees"), act("final_answer", answer="x")))
    out = agent.run_agent("q", "schema")
    assert out["steps"][0]["observation"].startswith("SQL ERROR")


def test_agent_endpoint_saves_history_and_uses_memory(client, alice, monkeypatch, prompts):
    monkeypatch.setattr(llm, "_generate", script(
        act("run_sql", sql="SELECT department, AVG(salary) AS avg_salary FROM employees GROUP BY department"),
        act("final_answer", answer="IT is higher."),
    ))
    r = client.post("/api/agent", headers=alice, json={"question": "Why is IT higher?"})
    assert r.status_code == 200
    d = r.json()
    assert d["answer"] == "IT is higher." and d["rows"]
    hist = client.get("/api/history", headers=alice).json()
    assert hist[0]["mode"] == "agent" and hist[0]["question"] == "Why is IT higher?"
