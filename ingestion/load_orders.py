import argparse
from pathlib import Path

import duckdb


parser = argparse.ArgumentParser(
    description="Load local orders dataset into DuckDB"
)

parser.add_argument(
    "--dataset",
    choices=["good", "broken"],
    required=True,
)

args = parser.parse_args()

project_root = Path(__file__).resolve().parent.parent

csv_path = project_root / "data" / args.dataset / "orders.csv"
db_path = project_root / "warehouse" / "lab.duckdb"

if not csv_path.exists():
    raise FileNotFoundError(f"Dataset not found: {csv_path}")

con = duckdb.connect(str(db_path))

con.execute(
    """
    CREATE OR REPLACE TABLE raw_orders AS
    SELECT
        row_number() OVER () + 1 AS source_row_number,
        ? AS source_dataset,
        ? AS source_file,
        *
    FROM read_csv_auto(?)
    """,
    [
        args.dataset,
        csv_path.name,
        str(csv_path),
    ],
)

row_count = con.execute(
    "SELECT COUNT(*) FROM raw_orders"
).fetchone()[0]

print(f"Dataset: {args.dataset}")
print(f"Source: {csv_path}")
print(f"Records loaded: {row_count}")
print(f"Database: {db_path}")
print("Status: SUCCESS")

con.close()