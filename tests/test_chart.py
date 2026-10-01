import pandas as pd

from app.chart import suggest_chart


def test_category_and_number_gives_bar():
    df = pd.DataFrame({"department": ["IT", "HR", "Sales"], "avg_salary": [100, 60, 70]})
    assert suggest_chart(df) == {"type": "bar", "x": "department", "y": "avg_salary"}


def test_date_column_gives_line():
    df = pd.DataFrame({"joining_year": ["2019", "2020", "2021"], "hires": [3, 5, 4]})
    assert suggest_chart(df)["type"] == "line"


def test_single_row_has_no_chart():
    assert suggest_chart(pd.DataFrame({"a": ["x"], "b": [1]})) is None


def test_text_only_has_no_chart():
    assert suggest_chart(pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]})) is None
