"""Orchestrate the extract -> transform -> quality-gate -> load pipeline."""
import sqlite3
from etl.extract import extract
from etl.transform import transform
from etl.data_quality import validate
from etl.load import load


def run() -> None:
    print("[1/4] Extract ...")
    sources = extract()
    print(f"      orders={len(sources['orders']):,}  customers={len(sources['customers']):,}")

    print("[2/4] Transform ...")
    models = transform(sources)
    print(f"      fact_orders={len(models['fact_orders']):,}")

    print("[3/4] Data-quality gate ...")
    for name, ok in validate(models["fact_orders"]):
        print(f"      {'PASS' if ok else 'FAIL'}  {name}")

    print("[4/4] Load ...")
    db = load(models)
    with sqlite3.connect(db) as con:
        rev = con.execute("SELECT ROUND(SUM(amount),2) FROM fact_orders").fetchone()[0]
        top = con.execute(
            "SELECT segment, ROUND(SUM(amount),2) r FROM fact_orders "
            "GROUP BY segment ORDER BY r DESC LIMIT 1").fetchone()
    print(f"\nLoaded -> {db}")
    print(f"Warehouse revenue: {rev:,}  | top segment: {top[0]} ({top[1]:,})")


if __name__ == "__main__":
    run()
