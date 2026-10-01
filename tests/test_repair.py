import pandas as pd
import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import repair
from app.validator import UnsafeSQLError


def test_bad_sql_is_fixed_on_second_try(monkeypatch):
    calls = []

    def fake_run(sql):
        calls.append(sql)
        if "salry" in sql:
            raise SQLAlchemyError("Unknown column 'salry'")
        return pd.DataFrame({"x": [1]})

    monkeypatch.setattr(repair.db, "run_query", fake_run)
    monkeypatch.setattr(repair.llm, "fix_sql", lambda q, s, bad, err: "SELECT salary FROM employees")

    sql, df, attempts = repair.run_with_repair("q", "schema", "SELECT salry FROM employees")
    assert len(df) == 1
    assert len(attempts) == 1 and "salry" in attempts[0]["sql"]


def test_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(repair.db, "run_query", lambda sql: (_ for _ in ()).throw(SQLAlchemyError("boom")))
    monkeypatch.setattr(repair.llm, "fix_sql", lambda *a: "SELECT 1 FROM nope")
    with pytest.raises(repair.QueryFailed) as exc:
        repair.run_with_repair("q", "schema", "SELECT 1 FROM nope")
    assert len(exc.value.attempts) == repair.MAX_FIX_ATTEMPTS + 1


def test_unsafe_sql_is_never_retried(monkeypatch):
    monkeypatch.setattr(repair.llm, "fix_sql", lambda *a: pytest.fail("should not be called"))
    with pytest.raises(UnsafeSQLError):
        repair.run_with_repair("q", "schema", "DROP TABLE employees")
