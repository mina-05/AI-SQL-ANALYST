"""Pick a sensible chart for a result table. Plain rules, no LLM needed."""
import pandas as pd

MAX_POINTS = 30


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def suggest_chart(df: pd.DataFrame):
    """Return {"type", "x", "y"} or None when a chart would not help."""
    if df.empty or len(df) < 2 or len(df) > MAX_POINTS or df.shape[1] < 2:
        return None

    numeric_cols = [c for c in df.columns if _numeric(df[c]).notna().all()]
    label_cols = [c for c in df.columns if c not in numeric_cols]

    # Label column (text/date) + numeric column
    if label_cols and numeric_cols:
        x = label_cols[0]
        y = numeric_cols[-1]
        looks_like_time = (
            pd.api.types.is_datetime64_any_dtype(df[x])
            or any(k in str(x).lower() for k in ("date", "month", "year", "day"))
        )
        kind = "line" if looks_like_time else "bar"
        return {"type": kind, "x": x, "y": y}

    # Year/month stored as a number + another numeric column
    if len(numeric_cols) >= 2 and any(k in str(numeric_cols[0]).lower() for k in ("year", "month")):
        return {"type": "line", "x": numeric_cols[0], "y": numeric_cols[1]}

    return None
