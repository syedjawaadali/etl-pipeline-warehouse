"""Load stage: write modeled tables into a SQLite warehouse."""
import sqlite3
from pathlib import Path

WAREHOUSE = Path(__file__).resolve().parents[1] / "data" / "warehouse.db"


def load(models: dict) -> Path:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(WAREHOUSE) as con:
        models["fact_orders"].to_sql("fact_orders", con,
                                     if_exists="replace", index=False)
        models["dim_customer"].to_sql("dim_customer", con,
                                      if_exists="replace")
    return WAREHOUSE
