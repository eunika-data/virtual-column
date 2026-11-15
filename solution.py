"""Part 1: add a calculated ("virtual") column to a pandas DataFrame."""

import re

import pandas

# A column label: only letters and underscores, at least one character.
LABEL_PATTERN = re.compile(r"[A-Za-z_]+")
# One token of a role: a label or one of the supported operators.
TOKEN_PATTERN = re.compile(r"\s*([A-Za-z_]+|[+\-*])\s*")
OPERATORS = {"+", "-", "*"}


def _is_valid_label(label) -> bool:
    return isinstance(label, str) and LABEL_PATTERN.fullmatch(label) is not None


def _tokenize(role: str):
    """Split a role into labels and operators. Return None if the role is malformed."""
    tokens = []
    position = 0
    role = role.strip()
    while position < len(role):
        match = TOKEN_PATTERN.match(role, position)
        if match is None:
            return None  # a character that is neither a label character nor an operator
        tokens.append(match.group(1))
        position = match.end()

    # The role must alternate: label, operator, label, ..., label.
    if not tokens or len(tokens) % 2 == 0:
        return None
    for index, token in enumerate(tokens):
        expects_label = index % 2 == 0
        if expects_label != (token not in OPERATORS):
            return None
    return tokens


def _evaluate(df: pandas.DataFrame, tokens):
    """Evaluate the tokens with the usual precedence: '*' before '+' and '-'."""
    labels = tokens[0::2]
    operators = tokens[1::2]

    # First pass: collapse multiplications into terms.
    terms = [df[labels[0]]]
    signs = []
    for operator, label in zip(operators, labels[1:]):
        if operator == "*":
            terms[-1] = terms[-1] * df[label]
        else:
            signs.append(operator)
            terms.append(df[label])

    # Second pass: add and subtract the terms from left to right.
    result = terms[0]
    for sign, term in zip(signs, terms[1:]):
        result = result + term if sign == "+" else result - term
    return result


def add_virtual_column(df: pandas.DataFrame, role: str, new_column: str) -> pandas.DataFrame:
    """Return a copy of ``df`` with ``new_column`` computed from ``role``.

    ``role`` is an expression made of column labels and the operators
    ``+``, ``-`` and ``*`` (for example ``"quantity * price"``). Spaces around
    labels and operators are allowed. If the role, a label used in it or
    ``new_column`` is invalid, an empty DataFrame is returned.
    """
    if not isinstance(df, pandas.DataFrame) or not isinstance(role, str):
        return pandas.DataFrame([])
    if not _is_valid_label(new_column):
        return pandas.DataFrame([])

    tokens = _tokenize(role)
    if tokens is None:
        return pandas.DataFrame([])

    labels = tokens[0::2]
    if any(label not in df.columns for label in labels):
        return pandas.DataFrame([])

    try:
        values = _evaluate(df, tokens)
    except TypeError:
        # For example, subtracting a text column.
        return pandas.DataFrame([])

    result = df.copy()
    result[new_column] = values
    return result
