"""Orchestrate the extract -> transform -> quality-gate -> load -> report pipeline."""
from etl.extract import extract
from etl.transform import transform
from etl.data_quality import validate
from etl.load import load
from etl.report import write_reports


def run() -> dict:
    print("[1/5] Extract ...")
    sources = extract()
    n_orders_raw = len(sources["orders"])
    n_customers = len(sources["customers"])
    print(f"      orders={n_orders_raw:,}  customers={n_customers:,}")

    print("[2/5] Transform ...")
    models = transform(sources)
    print(f"      fact_orders={len(models['fact_orders']):,}")

    print("[3/5] Data-quality gate ...")
    checks = validate(models["fact_orders"])
    for name, ok in checks:
        print(f"      {'PASS' if ok else 'FAIL'}  {name}")

    print("[4/5] Load ...")
    db = load(models)

    print("[5/5] Report ...")
    run_stats = {
        "orders_extracted": n_orders_raw,
        "customers_extracted": n_customers,
        "dq_passed": sum(1 for _, ok in checks if ok),
    }
    summary = write_reports(db, run_stats, models["fact_orders"])

    print(f"\nLoaded -> {db}")
    print(f"Warehouse revenue: {summary['total_revenue']:,.2f}  "
          f"| AOV: {summary['avg_order_value']:,.2f}  "
          f"| top segment: {summary['top_segment']} "
          f"({summary['revenue_by_segment'][summary['top_segment']]:,.2f})")
    print(f"DQ: {summary['rows_rejected_by_dq']} of {summary['rows_extracted']} "
          f"rows rejected ({summary['reject_rate_pct']}%); "
          f"{summary['fact_rows_loaded']:,} loaded.")
    print("Reports + star-schema diagram + dashboard written to outputs/ and docs/.")
    return summary


if __name__ == "__main__":
    run()
