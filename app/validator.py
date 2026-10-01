"""Safety checks for LLM-generated SQL. Only read-only SELECT queries pass."""
import re

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "grant", "revoke", "rename", "call", "exec", "execute",
    "load", "load_file", "outfile", "dumpfile", "into", "handler", "lock", "set",
    "sleep", "benchmark",
}


class UnsafeSQLError(ValueError):
    pass


def clean_sql(raw: str) -> str:
    """Strip markdown fences and surrounding whitespace the model may add."""
    sql = raw.strip()
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()
    return sql.rstrip(";").strip()


_TOKEN = re.compile(
    r"""'(?:[^'\\]|\\.|'')*'"""          # single-quoted string
    r"""|"(?:[^"\\]|\\.)*\""""          # double-quoted string
    r"""|`[^`]*`"""                        # backtick identifier
    r"""|/\*.*?\*/"""                      # block comment
    r"""|--(?=[ \t\r\n]|$)[^\n]*"""        # -- comment (MySQL needs a space after --)
    r"""|\#[^\n]*""",                      # # comment
    re.DOTALL,
)


def _strip_strings_and_comments(sql: str) -> str:
    """Blank out strings and comments in ONE pass, so a '--' inside a string
    is not mistaken for a comment (and vice versa)."""
    def repl(m):
        t = m.group(0)
        return " " if t.startswith(("/*", "--", "#")) else t[0] + t[-1]
    return _TOKEN.sub(repl, sql)


def validate_sql(sql: str, max_rows: int = 500) -> str:
    """Return a safe version of the query (with a LIMIT) or raise UnsafeSQLError."""
    sql = clean_sql(sql)
    if not sql:
        raise UnsafeSQLError("The model returned an empty query.")

    if "/*!" in sql:
        raise UnsafeSQLError("MySQL executable comments are not allowed.")

    body = _strip_strings_and_comments(sql)
    if "'" in body.replace("''", "") or '"' in body.replace('""', "") or "`" in body.replace("``", ""):
        raise UnsafeSQLError("The query has unbalanced quotes.")

    if ";" in body:
        raise UnsafeSQLError("Only one SQL statement is allowed.")

    first_word = body.split(None, 1)[0].lower()
    if first_word not in ("select", "with"):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    words = set(re.findall(r"[a-z_]+", body.lower()))
    bad = words & FORBIDDEN
    if bad:
        raise UnsafeSQLError(f"Query contains a blocked keyword: {sorted(bad)[0].upper()}.")

    if not re.search(r"\blimit\s+\d+", body, flags=re.IGNORECASE):
        sql = f"{sql}\nLIMIT {max_rows}"
    return sql
