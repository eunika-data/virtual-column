import io

import pandas as pd
import pytest

import pipeline

RAW = """Order ID,Region,Product,Quantity ,Unit Price,Discount,Order Date
SO-1,North,Mouse,2,"29,50",,2026-01-01
SO-2, north ,Mouse,1 000,29.50,10.00,2026-01-02
SO-3,SOUTH,Mouse,4,,,2026-01-03
SO-3,SOUTH,Mouse,4,,,2026-01-03
Order ID,Region,Product,Quantity ,Unit Price,Discount,Order Date
SO-4,South,Mouse,-1,29.50,,2026-01-04
TOTAL,,,1006,,10.00,
"""


@pytest.fixture
def cleaned():
    return pipeline.clean(pipeline.read_raw(io.StringIO(RAW)))


def test_columns_are_renamed_to_valid_labels(cleaned):
    assert list(cleaned.columns) == [
        "order_id", "region", "product", "quantity", "unit_price", "discount", "order_date"
    ]


def test_header_total_and_duplicate_rows_are_removed(cleaned):
    assert cleaned["order_id"].tolist() == ["SO-1", "SO-2", "SO-3", "SO-4"]


def test_region_is_normalised(cleaned):
    assert cleaned["region"].tolist() == ["North", "North", "South", "South"]


def test_numbers_are_parsed(cleaned):
    assert cleaned["quantity"].tolist() == [2, 1000, 4, -1]
    assert cleaned["unit_price"].tolist() == [29.5] * 4  # comma decimal and missing price fixed
    assert cleaned["discount"].tolist() == [0.0, 10.0, 0.0, 0.0]
    assert pd.api.types.is_datetime64_any_dtype(cleaned["order_date"])


def test_revenue_and_totals(cleaned):
    sales = pipeline.add_revenue(cleaned)
    assert sales["revenue"].tolist() == [59.0, 29490.0, 118.0, -29.5]
    totals = pipeline.revenue_by_region(sales)
    assert totals.to_dict("records") == [
        {"region": "North", "revenue": 29549.0},
        {"region": "South", "revenue": 88.5},
    ]


def test_row_that_cannot_be_fixed_raises():
    raw = "Order ID,Region,Product,Quantity ,Unit Price,Discount,Order Date\nSO-1,Mars,Mouse,1,1,,2026-01-01\n"
    with pytest.raises(ValueError):
        pipeline.clean(pipeline.read_raw(io.StringIO(raw)))


def test_real_file(tmp_path):
    output = tmp_path / "out.csv"
    totals = pipeline.run(output_file=output)
    assert sorted(totals["region"]) == ["Central", "East", "North", "South", "West"]
    assert pd.read_csv(output).equals(totals)

    sales = pipeline.clean(pipeline.read_raw())
    assert len(sales) == 1500  # 1507 lines - header - total - 5 duplicates
    assert sales["order_id"].is_unique


def test_committed_output_is_up_to_date():
    committed = pd.read_csv(pipeline.OUTPUT_FILE)
    fresh = pipeline.revenue_by_region(pipeline.add_revenue(pipeline.clean(pipeline.read_raw())))
    pd.testing.assert_frame_equal(committed, fresh)
