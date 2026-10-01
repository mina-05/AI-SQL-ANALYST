from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from . import config

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = (
            f"mysql+pymysql://{config.DB_USER}:{quote_plus(config.DB_PASSWORD)}"
            f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
        )
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_schema() -> dict:
    """Return {table: [{name, type}, ...]} for every table in the database."""
    insp = inspect(get_engine())
    return {
        table: [{"name": c["name"], "type": str(c["type"])} for c in insp.get_columns(table)]
        for table in insp.get_table_names()
    }


def schema_as_text(schema: dict) -> str:
    """Compact schema description to put into the LLM prompt."""
    lines = []
    for table, cols in schema.items():
        col_text = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        lines.append(f"{table}({col_text})")
    return "\n".join(lines)


def _to_df(result) -> pd.DataFrame:
    # Build the DataFrame ourselves: pd.read_sql wraps database errors in its own
    # exception type, which would hide SQLAlchemyError from the auto-repair loop.
    return pd.DataFrame.from_records(result.fetchall(), columns=list(result.keys()), coerce_float=True)


def run_query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return _to_df(conn.execute(text(sql)))


def explain_plan(sql: str) -> str:
    """Run EXPLAIN on an already-validated SELECT and return it as text."""
    with get_engine().connect() as conn:
        df = _to_df(conn.execute(text(f"EXPLAIN {sql}")))
    return df.to_string(index=False)


def rows_of(df: pd.DataFrame) -> list:
    """DataFrame -> JSON-friendly list of rows (NaN becomes None)."""
    return df.astype(object).where(df.notna(), None).values.tolist()
