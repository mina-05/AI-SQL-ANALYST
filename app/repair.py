"""Run a query; if MySQL rejects it, ask the LLM to fix it and try again."""
from sqlalchemy.exc import SQLAlchemyError

from . import config, db, llm
from .validator import validate_sql

MAX_FIX_ATTEMPTS = 2


class QueryFailed(Exception):
    def __init__(self, error: str, attempts: list):
        super().__init__(error)
        self.error = error
        self.attempts = attempts


def run_with_repair(question: str, schema_text: str, sql: str):
    """Return (final_sql, DataFrame, failed_attempts).

    UnsafeSQLError is NOT retried - a blocked query stays blocked.
    Raises QueryFailed if every attempt errors.
    """
    attempts = []
    for i in range(MAX_FIX_ATTEMPTS + 1):
        safe_sql = validate_sql(sql, config.MAX_ROWS)
        try:
            return safe_sql, db.run_query(safe_sql), attempts
        except SQLAlchemyError as e:
            error = str(getattr(e, "orig", e))
            attempts.append({"sql": safe_sql, "error": error})
            if i == MAX_FIX_ATTEMPTS:
                raise QueryFailed(error, attempts)
            sql = llm.fix_sql(question, schema_text, safe_sql, error)
