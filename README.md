# Virtual columns in a pandas DataFrame

- `solution.py` – `add_virtual_column(df, role, new_column)` (Part 1)
- `pipeline.py` – cleans `sales.csv`, adds `revenue`, writes `revenue_by_region.csv` (Part 2)
- `revenue_by_region.csv` – output of the pipeline
- `test_virtual_column.py` – sample tests provided with the task (unchanged)
- `tests/` – my tests for Part 1 (`test_solution.py`) and Part 2 (`test_pipeline.py`)

## Setup

Requires Python 3.9+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the pipeline

```bash
python pipeline.py
```

It prints the totals and (re)writes `revenue_by_region.csv`:

| region  | revenue   |
|---------|-----------|
| Central | 515824.67 |
| East    | 442219.91 |
| North   | 665897.52 |
| South   | 504036.04 |
| West    | 442268.89 |

## Run the tests

```bash
pytest
```

One command runs the sample tests and my own tests (`pytest.ini` sets the paths).

## Part 1: how `add_virtual_column` works

The role is not passed to `eval` or `DataFrame.eval`. It is split into tokens with a
regular expression, and the tokens must alternate *label, operator, label, …*.
Labels are letters and underscores only; operators are `+`, `-`, `*`. The expression is
evaluated on whole columns (vectorised), with `*` before `+`/`-` and left to right
otherwise. On any invalid input the function returns `pandas.DataFrame([])`.

### Assumptions (Part 1)

- **New column name.** The example in the task shows the column as `price_total` while the
  call passes `"total"`. I treat that as a typo: the new column is called exactly
  `new_column` (this is also what the sample tests expect).
- **Which labels are validated.** The labels used in `role` and `new_column` must be
  letters/underscores only, and the labels in `role` must exist in `df`. Other columns of
  `df` that are not used are not checked, so a frame with e.g. an `id2` column still works.
- **Operator precedence.** Normal maths rules: `a + b * c` = `a + (b * c)`.
- **Not supported → empty result:** numbers in the role (`a + 2`), parentheses, unary minus
  (`-a`), `/`, `**`, and any other character.
- **Spaces** are allowed anywhere around labels and operators, and at the start/end.
- **Existing column.** If `new_column` already exists, it is overwritten in the returned copy.
- **The input is never modified**; the function returns a new DataFrame.
- If the operation itself fails (e.g. subtracting text columns) the result is empty.

## Part 2: problems found in `sales.csv`

The file has 1,507 data lines (plus the header). I read all columns as text first, so
nothing is converted or lost silently, and then fix each problem in code. After cleaning
there are **1,500 order lines**.

| # | Problem | Rows | How it is handled |
|---|---------|-----:|-------------------|
| 1 | Header `Quantity ` has a trailing space; headers have spaces/capitals, which `add_virtual_column` does not accept | header | Strip headers and rename to `order_id, region, product, quantity, unit_price, discount, order_date` |
| 2 | The header line is repeated in the middle of the file (line 753) | 1 | Removed (not an order line) |
| 3 | A `TOTAL` summary line at the end | 1 | Removed (not an order line, and it would double the totals) |
| 4 | Exact duplicate lines (same order ID and all values): SO-10305, SO-10822, SO-10966, SO-11240, SO-11405 | 5 | One copy kept, the duplicate removed |
| 5 | Region written with different case and/or extra spaces (`EAST`, ` South`, `west  `, `north`, …) | 15 | Strip and title-case → one of North, South, East, West, Central |
| 6 | Unit price with a decimal comma (`39,90`) | 7 | Comma replaced with a dot |
| 7 | Missing unit price | 4 | Filled with the product's price: every product has exactly one price in the file (e.g. Keyboard is always 89.00) |
| 8 | Quantity with a space as thousands separator (`1 762`, `1 745`, `1 371`, `1 427`) | 4 | Space removed → 1762, 1745, 1371, 1427 |
| 9 | Negative quantity (-2 … -5) | 6 | Kept as returns: they give negative revenue and reduce the region total |
| 10 | Empty discount | 963 | Means "no discount" (as the task says) → 0 |
| 11 | Whitespace around values in general | – | All text values are stripped |

Checked and found clean: all order dates are valid ISO dates (2026-01-02 … 2026-09-29),
all discounts are ≥ 0 and never larger than quantity × unit price, order IDs are unique
after removing duplicates.

As a last safety net, `clean()` raises an error if any row still has a missing quantity
or price, or an unknown region, instead of silently producing wrong totals. No row of
`sales.csv` hits it, so **no fixable row is dropped**.

### Decisions (Part 2)

- **Thousands separator, not a typo.** The four quantities like `1 762` are much larger than
  the rest (normally 1–40). I read them as 1,762 etc. The `TOTAL` line confirms this: its
  quantity (37,150) and discount (65,924.67) equal the sum of all raw lines only when these
  values are read as thousands. They are large orders but there is no evidence they are wrong,
  so they are kept as they are.
- **Negative quantities are returns.** Lines with a negative quantity have no discount and look
  like returned goods. I keep them with negative revenue. If they should be treated as sign
  errors instead, the change is one line (`abs()`) in `clean()`.
- **Duplicates.** Lines that are identical in every column, including the order ID, are export
  duplicates; I keep one copy. Lines with the same ID but different values would be kept
  (there are none).
- **Revenue** = `quantity * unit_price - discount`, rounded to 2 decimal places. The discount is
  an amount for the whole line, so it is not multiplied by quantity.
- `revenue_by_region.csv` has two columns, `region` and `revenue`, sorted by region.
