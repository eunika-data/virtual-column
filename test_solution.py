import pandas as pd
import pytest

from solution import add_virtual_column


@pytest.fixture
def fruits():
    return pd.DataFrame({"name": ["banana", "apple"], "quantity": [10, 3], "price": [10, 1]})


def test_example_from_task(fruits):
    result = add_virtual_column(fruits, "quantity * price", "total")
    assert list(result.columns) == ["name", "quantity", "price", "total"]
    assert result["total"].tolist() == [100, 3]


def test_input_is_not_modified(fruits):
    before = fruits.copy()
    add_virtual_column(fruits, "quantity * price", "total")
    assert fruits.equals(before)


def test_multiplication_before_addition_and_subtraction():
    df = pd.DataFrame({"a": [2], "b": [3], "c": [4]})
    assert add_virtual_column(df, "a + b * c", "x")["x"].tolist() == [14]
    assert add_virtual_column(df, "a * b - c", "x")["x"].tolist() == [2]
    assert add_virtual_column(df, "a - b - c", "x")["x"].tolist() == [-5]  # left to right


def test_same_column_twice_and_no_spaces():
    df = pd.DataFrame({"a": [3]})
    assert add_virtual_column(df, "a*a-a", "x")["x"].tolist() == [6]


def test_single_column_copies_values():
    df = pd.DataFrame({"a": [1, 2]})
    assert add_virtual_column(df, "a", "b")["b"].tolist() == [1, 2]


def test_works_with_floats():
    df = pd.DataFrame({"q": [3], "p": [1.5], "d": [0.5]})
    assert add_virtual_column(df, "q * p - d", "r")["r"].tolist() == [4.0]


@pytest.mark.parametrize(
    "role",
    [
        "",
        "   ",
        "a +",
        "+ a",
        "a + + b",
        "a b",
        "a / b",
        "a ** b",
        "(a + b)",
        "a + 2",
        "a1 + b",
        "a + missing",
        "__import__",
    ],
)
def test_invalid_role_returns_empty(role):
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, role, "c").empty


@pytest.mark.parametrize("new_column", ["", "with space", "col1", "a-b", None, 5])
def test_invalid_new_column_returns_empty(new_column):
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, "a + b", new_column).empty


def test_invalid_column_label_used_in_role_returns_empty():
    df = pd.DataFrame({"a1": [1], "b": [2]})
    assert add_virtual_column(df, "a1 + b", "c").empty


def test_text_columns_that_cannot_be_subtracted_return_empty():
    df = pd.DataFrame({"a": ["x"], "b": ["y"]})
    assert add_virtual_column(df, "a - b", "c").empty


def test_existing_column_is_overwritten_in_the_copy():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = add_virtual_column(df, "a + b", "a")
    assert result["a"].tolist() == [3]
    assert df["a"].tolist() == [1]


def test_empty_dataframe_with_columns():
    df = pd.DataFrame({"a": pd.Series([], dtype="int64"), "b": pd.Series([], dtype="int64")})
    result = add_virtual_column(df, "a + b", "c")
    assert list(result.columns) == ["a", "b", "c"]
