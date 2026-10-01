import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import config, db, llm, rag
from app.main import app

FAKE_SCHEMA = {
    "employees": [
        {"name": "id", "type": "INTEGER"},
        {"name": "department", "type": "VARCHAR(50)"},
        {"name": "salary", "type": "DECIMAL(10, 2)"},
    ]
}


@pytest.fixture
def prompts(tmp_path, monkeypatch):
    """Isolated app DB, fake MySQL, fake LLM. Returns the list of prompts the LLM received."""
    monkeypatch.setattr(config, "APP_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setattr(config, "ALLOW_REGISTRATION", True)
    rag.reset()
    monkeypatch.setattr(db, "get_schema", lambda: FAKE_SCHEMA)
    monkeypatch.setattr(
        db, "run_query",
        lambda sql: pd.DataFrame({"department": ["IT", "HR"], "avg_salary": [102000.0, 63000.0]}),
    )

    seen = []

    def fake_generate(prompt, json_mode=False):
        seen.append(prompt)
        if "MySQL expert" in prompt:
            return "SELECT department, AVG(salary) AS avg_salary FROM employees GROUP BY department"
        return "Fake insight."

    monkeypatch.setattr(llm, "_generate", fake_generate)
    yield seen
    rag.reset()


@pytest.fixture
def client(prompts):
    return TestClient(app)


def register(client, name="alice", password="correct-horse"):
    r = client.post("/api/auth/register", json={"username": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def alice(client):
    return register(client, "alice")
