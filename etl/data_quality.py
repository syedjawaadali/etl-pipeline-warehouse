"""Lightweight data-quality gate run before load."""
import pandas as pd


class DQError(Exception):
    pass


def validate(fact: pd.DataFrame) -> list:
    checks = []

    def check(name, condition):
        checks.append((name, bool(condition)))

    check("fact_not_empty", len(fact) > 0)
    check("no_null_order_id", fact["order_id"].notna().all())
    check("amount_non_negative", (fact["amount"] >= 0).all())
    check("customer_id_present", fact["customer_id"].notna().all())

    failed = [n for n, ok in checks if not ok]
    if failed:
        raise DQError(f"Data-quality checks failed: {failed}")
    return checks
