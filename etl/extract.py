"""Extract stage: simulate pulling from CSV + JSON API sources."""
import json
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(11)
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def seed_sources() -> None:
    """Create raw source files as if landed from upstream systems."""
    RAW.mkdir(parents=True, exist_ok=True)
    dates = pd.date_range("2025-01-01", periods=180, freq="D")
    orders = pd.DataFrame({
        "order_id": range(1, len(dates) * 5 + 1),
        "order_date": np.repeat(dates.astype(str), 5),
        "amount": RNG.gamma(3, 40, len(dates) * 5).round(2),
        "customer_id": RNG.integers(1, 400, len(dates) * 5),
    })
    orders.loc[orders.sample(frac=0.02, random_state=1).index, "amount"] = None
    orders.to_csv(RAW / "orders.csv", index=False)

    customers = [{"customer_id": i,
                  "segment": RNG.choice(["SMB", "Enterprise", "Consumer"]).item(),
                  "country": RNG.choice(["PK", "AE", "UK", "US"]).item()}
                 for i in range(1, 400)]
    (RAW / "customers.json").write_text(json.dumps(customers, indent=2))


def extract() -> dict:
    if not (RAW / "orders.csv").exists():
        seed_sources()
    orders = pd.read_csv(RAW / "orders.csv", parse_dates=["order_date"])
    customers = pd.DataFrame(json.loads((RAW / "customers.json").read_text()))
    return {"orders": orders, "customers": customers}
