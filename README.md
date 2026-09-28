# ETL Pipeline → SQLite Warehouse

A clean, modular **extract → transform → data-quality gate → load** pipeline
that lands raw CSV/JSON sources into a modeled star schema in a SQLite
warehouse. This mirrors the medallion / gold-layer modeling and reconciliation
work I do on production BI platforms.

## Architecture
```
sources (CSV + JSON)  ->  extract  ->  transform (clean + star schema)
                                          -> data-quality gate -> load (SQLite)
```

## Modules
| File | Role |
|------|------|
| `etl/extract.py` | Seeds & reads raw order/customer sources |
| `etl/transform.py` | Cleans, dedupes, builds `fact_orders` + `dim_customer` |
| `etl/data_quality.py` | Validation gate (fails the run on bad data) |
| `etl/load.py` | Writes tables to `data/warehouse.db` |
| `pipeline.py` | Orchestrates the full run |

## Run it
```bash
pip install -r requirements.txt
python pipeline.py
```

## Stack
`pandas` · `sqlite3` · modular ETL design

---
Part of my data engineering portfolio — [github.com/syedjawaadali](https://github.com/syedjawaadali)
