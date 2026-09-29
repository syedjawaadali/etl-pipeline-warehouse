"""Reporting stage: read the loaded warehouse and produce the artefacts that
prove the pipeline landed clean, modeled data — a run summary (JSON), a
star-schema diagram, and a one-page warehouse dashboard.

Called at the end of ``pipeline.py``. Committed copies live in ``docs/``.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"

# ---- House style -----------------------------------------------------------
INK = "#0f172a"
GRID = "#e2e8f0"
ACCENT = "#1E90FF"
ACCENT_2 = "#00C2A8"
PALETTE = ["#1E90FF", "#00C2A8", "#F5A524", "#7C5CFF", "#F2647C"]

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": GRID,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
})

_MONEY = FuncFormatter(lambda x, _: f"${x/1e3:.0f}K" if abs(x) >= 1e3 else f"${x:.0f}")


def warehouse_summary(db: Path, run_stats: dict) -> dict:
    """Reconcile the loaded warehouse via SQL — the numbers the README cites."""
    with sqlite3.connect(db) as con:
        rev, n_orders, n_cust, aov = con.execute(
            "SELECT ROUND(SUM(amount),2), COUNT(*), COUNT(DISTINCT customer_id), "
            "ROUND(AVG(amount),2) FROM fact_orders").fetchone()
        by_segment = dict(con.execute(
            "SELECT segment, ROUND(SUM(amount),2) FROM fact_orders "
            "GROUP BY segment ORDER BY 2 DESC").fetchall())
        by_country = dict(con.execute(
            "SELECT country, ROUND(SUM(amount),2) FROM fact_orders "
            "GROUP BY country ORDER BY 2 DESC").fetchall())
        by_month = dict(con.execute(
            "SELECT order_month, ROUND(SUM(amount),2) FROM fact_orders "
            "GROUP BY order_month ORDER BY 1").fetchall())
    rejected = run_stats["orders_extracted"] - n_orders
    return {
        "rows_extracted": run_stats["orders_extracted"],
        "rows_rejected_by_dq": int(rejected),
        "reject_rate_pct": round(100 * rejected / run_stats["orders_extracted"], 2),
        "fact_rows_loaded": int(n_orders),
        "dim_customer_rows": run_stats["customers_extracted"],
        "distinct_customers_with_orders": int(n_cust),
        "total_revenue": float(rev),
        "avg_order_value": float(aov),
        "dq_checks_passed": run_stats["dq_passed"],
        "top_segment": max(by_segment, key=by_segment.get),
        "revenue_by_segment": by_segment,
        "revenue_by_country": by_country,
        "revenue_by_month": by_month,
    }


def star_schema_diagram() -> None:
    """Draw the fact/dim star schema so the data model reads at a glance."""
    OUT.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
    ax.set_title("Warehouse Star Schema", fontsize=15, fontweight="bold", color=INK)

    def table(x, y, w, h, title, cols, header):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=1.6, edgecolor=header, facecolor="white", zorder=3))
        ax.add_patch(FancyBboxPatch((x, y + h - 0.55), w, 0.55,
                                    boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=0, facecolor=header, zorder=4))
        ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="center",
                color="white", fontweight="bold", fontsize=11, zorder=5)
        for i, c in enumerate(cols):
            ax.text(x + 0.2, y + h - 0.95 - i * 0.42, c, ha="left", va="center",
                    fontsize=9, color=INK, zorder=5)

    # fact in centre
    table(3.7, 1.4, 2.6, 3.2, "fact_orders",
          ["order_id  (PK)", "order_date", "order_month", "customer_id (FK)",
           "segment", "country", "amount"], ACCENT)
    # dimension
    table(0.4, 2.6, 2.4, 2.0, "dim_customer",
          ["customer_id (PK)", "segment", "country"], ACCENT_2)

    arrow = FancyArrowPatch((2.8, 3.6), (3.7, 3.2), arrowstyle="-|>",
                            mutation_scale=18, color="#64748b", lw=1.8, zorder=2)
    ax.add_patch(arrow)
    ax.text(3.25, 3.62, "1 : N", ha="center", fontsize=9, color="#64748b")
    ax.text(6.8, 3.0, "grain: one row per order\nsource: CSV (orders) + JSON (customers)",
            ha="left", va="center", fontsize=9.5, color="#475569")

    fig.tight_layout()
    for t in (OUT / "star_schema.png", DOCS / "star_schema.png"):
        fig.savefig(t, dpi=130)
    plt.close(fig)


def dashboard(s: dict) -> None:
    """One-page warehouse dashboard from the reconciled SQL aggregates."""
    OUT.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle("ETL Warehouse — Load Summary", fontsize=16, fontweight="bold",
                 color=INK, x=0.5, y=0.99)

    # 1) monthly revenue trend
    ax = axes[0, 0]
    months = list(s["revenue_by_month"])
    vals = list(s["revenue_by_month"].values())
    ax.plot(range(len(months)), vals, marker="o", color=ACCENT, lw=2.2)
    ax.fill_between(range(len(months)), vals, alpha=0.12, color=ACCENT)
    ax.set_title("Revenue by Month")
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45, ha="right", fontsize=8)
    ax.yaxis.set_major_formatter(_MONEY)

    # 2) revenue by segment
    ax = axes[0, 1]
    seg = s["revenue_by_segment"]
    ax.bar(list(seg), list(seg.values()), color=PALETTE[:len(seg)])
    ax.set_title("Revenue by Segment")
    ax.yaxis.set_major_formatter(_MONEY)

    # 3) revenue by country
    ax = axes[1, 0]
    cty = s["revenue_by_country"]
    ax.barh(list(cty)[::-1], list(cty.values())[::-1], color=ACCENT_2)
    ax.set_title("Revenue by Country")
    ax.xaxis.set_major_formatter(_MONEY)
    ax.grid(axis="y", visible=False)

    # 4) pipeline funnel: extracted -> loaded
    ax = axes[1, 1]
    stages = ["Extracted", "Loaded (post-DQ)"]
    counts = [s["rows_extracted"], s["fact_rows_loaded"]]
    bars = ax.bar(stages, counts, color=[PALETTE[3], ACCENT])
    ax.set_title(f"DQ Gate — {s['rows_rejected_by_dq']} rows rejected "
                 f"({s['reject_rate_pct']}%)")
    ax.grid(axis="x", visible=False)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c, f"{c:,}",
                ha="center", va="bottom", fontweight="bold")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    for t in (OUT / "dashboard.png", DOCS / "dashboard.png"):
        fig.savefig(t, dpi=130)
    plt.close(fig)


def write_reports(db: Path, run_stats: dict, fact: pd.DataFrame) -> dict:
    OUT.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True)
    summary = warehouse_summary(db, run_stats)
    star_schema_diagram()
    dashboard(summary)
    for t in (OUT / "warehouse_summary.json", DOCS / "warehouse_summary.json"):
        t.write_text(json.dumps(summary, indent=2))
    fact.head(8).to_csv(DOCS / "sample_fact_orders.csv", index=False)
    return summary
