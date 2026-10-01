import requests

from app import db, llm
from tests.conftest import register


def ask(client, headers, question, conv=None, **extra):
    return client.post("/api/ask", headers=headers, json={"question": question, "conversation_id": conv, **extra})


def test_ask_returns_sql_rows_chart_and_conversation(client, alice):
    r = ask(client, alice, "avg salary by department")
    assert r.status_code == 200
    d = r.json()
    assert d["sql"].startswith("SELECT department")
    assert d["columns"] == ["department", "avg_salary"]
    assert d["chart"]["type"] == "bar"
    assert d["insight"] == "Fake insight."
    assert len(d["conversation_id"]) >= 8


def test_empty_question_rejected(client, alice):
    assert ask(client, alice, "   ").status_code == 400


def test_follow_up_sees_earlier_turns(client, alice, prompts):
    first = ask(client, alice, "average salary by department").json()
    ask(client, alice, "and only for IT?", conv=first["conversation_id"])
    sql_prompts = [p for p in prompts if "MySQL expert" in p]
    assert "Earlier in this conversation" not in sql_prompts[0]
    assert "Earlier in this conversation" in sql_prompts[1]  # memory block added
    assert "Q: average salary by department" in sql_prompts[1]
    assert "SQL: SELECT department" in sql_prompts[1]


def test_new_conversation_starts_clean(client, alice, prompts):
    ask(client, alice, "average salary by department")
    ask(client, alice, "a brand new topic")
    sql_prompts = [p for p in prompts if "MySQL expert" in p]
    assert "Earlier in this conversation" not in sql_prompts[1]


def test_business_docs_are_added_to_prompt(client, alice, prompts):
    ask(client, alice, "what currency is the salary in")
    sql_prompt = [p for p in prompts if "MySQL expert" in p][0]
    assert "Indian rupees" in sql_prompt


def test_history_is_saved_and_private(client, alice):
    ask(client, alice, "average salary by department")
    bob = register(client, "bob")
    assert [h["question"] for h in client.get("/api/history", headers=alice).json()] == ["average salary by department"]
    assert client.get("/api/history", headers=bob).json() == []
    # bob cannot read alice's conversation through the memory either
    assert client.delete("/api/history", headers=bob).status_code == 200
    assert len(client.get("/api/history", headers=alice).json()) == 1


def test_clear_history(client, alice):
    ask(client, alice, "q one")
    client.delete("/api/history", headers=alice)
    assert client.get("/api/history", headers=alice).json() == []


def test_unsafe_sql_from_model_is_blocked_and_never_run(client, alice, monkeypatch):
    calls = []
    monkeypatch.setattr(db, "run_query", lambda sql: calls.append(sql))
    monkeypatch.setattr(llm, "_generate", lambda p, json_mode=False: "SELECT '--' ; DROP TABLE employees")
    r = ask(client, alice, "x")
    assert r.status_code == 422 and "blocked" in r.json()["detail"].lower()
    assert calls == []


def test_ollama_down_gives_503(client, alice, monkeypatch):
    def boom(p, json_mode=False):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(llm, "_generate", boom)
    assert ask(client, alice, "x").status_code == 503


def test_explain_and_blocked_explain(client, alice):
    assert client.post("/api/explain", headers=alice, json={"sql": "SELECT * FROM employees"}).status_code == 200
    assert client.post("/api/explain", headers=alice, json={"sql": "DROP TABLE employees"}).status_code == 422
