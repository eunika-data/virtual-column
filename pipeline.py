"""Part 2: clean sales.csv, add revenue and write revenue by region."""

import logging
from pathlib import Path

import pandas as pd

from solution import add_virtual_column

log = logging.getLogger("pipeline")

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "sales.csv"
OUTPUT_FILE = BASE_DIR / "revenue_by_region.csv"

# Raw header -> clean label. Labels use only letters and underscores,
# because add_virtual_column accepts nothing else.
COLUMN_NAMES = {
    "Order ID": "order_id",
    "Region": "region",
    "Product": "product",
    "Quantity": "quantity",
    "Unit Price": "unit_price",
    "Discount": "discount",
    "Order Date": "order_date",
}
VALID_REGIONS = {"North", "South", "East", "West", "Central"}


def read_raw(path=INPUT_FILE) -> pd.DataFrame:
    """Read everything as text, so no value is converted or lost silently."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _to_number(series: pd.Series) -> pd.Series:
    """Parse numbers written with a decimal comma or a space as thousands separator."""
    text = (
        series.str.strip()
        .str.replace(r"[\s ]", "", regex=True)  # "1 762" -> "1762"
        .str.replace(",", ".", regex=False)  # "39,90" -> "39.90"
    )
    return pd.to_numeric(text, errors="coerce")


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    # 1. Header: strip spaces ("Quantity " -> "Quantity") and rename.
    df.columns = df.columns.str.strip()
    df = df.rename(columns=COLUMN_NAMES)
    for column in df.columns:
        df[column] = df[column].str.strip()

    # 2. Rows that are not order lines: a repeated header and a TOTAL row.
    is_header = df["order_id"].str.lower() == "order id"
    is_total = df["order_id"].str.upper() == "TOTAL"
    log.info("Removed %d repeated header row(s) and %d total row(s)", is_header.sum(), is_total.sum())
    df = df[~is_header & ~is_total]

    # 3. Exact duplicate lines (same order ID and same values everywhere).
    duplicates = df.duplicated()
    log.info("Removed %d duplicated row(s)", duplicates.sum())
    df = df[~duplicates]

    # 4. Region: the same region is written with different case/spaces.
    df["region"] = df["region"].str.title()

    # 5. Numbers.
    df["quantity"] = _to_number(df["quantity"])
    df["unit_price"] = _to_number(df["unit_price"])
    df["discount"] = _to_number(df["discount"]).fillna(0.0)  # empty = no discount

    # 6. Missing unit price: every product has one fixed price in the data,
    #    so the price is taken from the other lines of the same product.
    catalog = df.dropna(subset=["unit_price"]).groupby("product")["unit_price"].agg(
        lambda prices: prices.mode().iloc[0]
    )
    missing_price = df["unit_price"].isna()
    log.info("Filled %d missing unit price(s) from the product price", missing_price.sum())
    df.loc[missing_price, "unit_price"] = df.loc[missing_price, "product"].map(catalog)

    # 7. Dates.
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")

    # 8. Safety net: anything that is still unusable cannot be fixed, so stop loudly
    #    instead of producing wrong totals.
    unusable = (
        df["quantity"].isna()
        | df["unit_price"].isna()
        | ~df["region"].isin(VALID_REGIONS)
    )
    if unusable.any():
        raise ValueError(f"{unusable.sum()} row(s) could not be cleaned:\n{df[unusable]}")

    df["quantity"] = df["quantity"].astype("int64")
    # Negative quantities are kept: they are treated as returns (see README).
    return df.reset_index(drop=True)


def add_revenue(df: pd.DataFrame) -> pd.DataFrame:
    result = add_virtual_column(df, "quantity * unit_price - discount", "revenue")
    if result.empty:
        raise ValueError("Could not compute the revenue column")
    result["revenue"] = result["revenue"].round(2)
    return result


def revenue_by_region(df: pd.DataFrame) -> pd.DataFrame:
    totals = df.groupby("region", as_index=False)["revenue"].sum()
    totals["revenue"] = totals["revenue"].round(2)
    return totals.sort_values("region").reset_index(drop=True)


def run(input_file=INPUT_FILE, output_file=OUTPUT_FILE) -> pd.DataFrame:
    sales = add_revenue(clean(read_raw(input_file)))
    totals = revenue_by_region(sales)
    totals.to_csv(output_file, index=False)
    log.info("Wrote %s", output_file)
    return totals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(run().to_string(index=False))
