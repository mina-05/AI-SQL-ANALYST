import pytest

from app.validator import UnsafeSQLError, validate_sql


def test_select_gets_limit():
    out = validate_sql("SELECT * FROM employees;", 100)
    assert out.endswith("LIMIT 100")


def test_existing_limit_kept():
    assert validate_sql("SELECT * FROM employees LIMIT 5").count("LIMIT") == 1


def test_markdown_fences_removed():
    assert validate_sql("```sql\nSELECT 1\n```").startswith("SELECT 1")


@pytest.mark.parametrize("sql", [
    "DROP TABLE employees",
    "DELETE FROM employees",
    "SELECT 1; DROP TABLE employees",
    "UPDATE employees SET salary = 0",
    "SELECT * FROM employees INTO OUTFILE '/tmp/x'",
    "SELECT '--' ; DROP TABLE employees",
    "SELECT * FROM employees WHERE name='a#b'; DROP TABLE x",
    "SELECT /*!50000 1; DROP TABLE x */ 1",
    "SELECT 'unterminated; DROP TABLE x",
    "SELECT SLEEP(100)",
    "SELECT LOAD_FILE('/etc/passwd')",
    "",
])
def test_unsafe_blocked(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_keyword_inside_string_is_allowed():
    validate_sql("SELECT * FROM employees WHERE name = 'drop table'")


def test_replace_function_allowed():
    validate_sql("SELECT REPLACE(name, 'a', 'b') FROM employees")


def test_dash_dash_inside_string_allowed():
    validate_sql("SELECT * FROM employees WHERE name = 'a -- b'")
