"""Transform stage: clean, enrich, and model into a star schema."""
import pandas as pd


def transform(sources: dict) -> dict:
    orders = sources["orders"].copy()
    customers = sources["customers"]

    # cleaning: drop rows with no amount, remove dupes
    orders = orders.dropna(subset=["amount"]).drop_duplicates("order_id")
    orders["amount"] = orders["amount"].astype(float)

    # enrich with customer attributes
    fact = orders.merge(customers, on="customer_id", how="left")
    fact["order_month"] = fact["order_date"].dt.to_period("M").astype(str)

    dim_customer = customers.set_index("customer_id")
    fact_orders = fact[["order_id", "order_date", "order_month",
                        "customer_id", "segment", "country", "amount"]]
    return {"fact_orders": fact_orders, "dim_customer": dim_customer}
