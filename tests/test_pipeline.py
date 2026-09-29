"""Invariant tests for the ETL pipeline stages.

These guard the contracts that make the warehouse trustworthy: the transform
cleans and models correctly, the data-quality gate actually fails on bad data,
the load round-trips through SQLite, and the reconciled summary balances.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from etl.extract import extract  # noqa: E402
from etl.transform import transform  # noqa: E402
from etl.data_quality import validate, DQError  # noqa: E402
from etl.load import load  # noqa: E402
from etl.report import warehouse_summary  # noqa: E402

FACT_COLS = {"order_id", "order_date", "order_month", "customer_id",
             "segment", "country", "amount"}


@pytest.fixture(scope="module")
def sources():
    return extract()


@pytest.fixture(scope="module")
def models(sources):
    return transform(sources)


def test_extract_shapes(sources):
    assert len(sources["orders"]) > 0
    assert {"order_id", "amount", "customer_id"}.issubset(sources["orders"].columns)
    assert {"customer_id", "segment", "country"}.issubset(sources["customers"].columns)


def test_transform_star_schema(models):
    fact = models["fact_orders"]
    assert FACT_COLS.issubset(fact.columns)
    assert fact["amount"].notna().all()               # nulls dropped
    assert fact["order_id"].is_unique                 # deduped -> valid PK
    assert (fact["amount"] >= 0).all()


def test_transform_rejects_dirty_rows(sources, models):
    # 2% of amounts are seeded null upstream; they must not survive.
    assert len(models["fact_orders"]) < len(sources["orders"])


def test_dq_gate_passes_on_clean(models):
    checks = validate(models["fact_orders"])
    assert all(ok for _, ok in checks)


def test_dq_gate_fails_on_bad_data(models):
    bad = models["fact_orders"].copy()
    bad.loc[bad.index[0], "amount"] = -10          # negative money
    with pytest.raises(DQError):
        validate(bad)


def test_load_roundtrips(models):
    db = load(models)
    with sqlite3.connect(db) as con:
        n = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    assert n == len(models["fact_orders"])
    assert {"fact_orders", "dim_customer"}.issubset(tables)


def test_summary_reconciles(sources, models):
    db = load(models)
    run_stats = {
        "orders_extracted": len(sources["orders"]),
        "customers_extracted": len(sources["customers"]),
        "dq_passed": 4,
    }
    s = warehouse_summary(db, run_stats)
    # extracted = loaded + rejected, and revenue is positive & finite
    assert s["fact_rows_loaded"] + s["rows_rejected_by_dq"] == s["rows_extracted"]
    assert s["total_revenue"] > 0
    assert s["top_segment"] in s["revenue_by_segment"]
    # segment revenues sum to the warehouse total (within rounding)
    assert abs(sum(s["revenue_by_segment"].values()) - s["total_revenue"]) < 1.0
