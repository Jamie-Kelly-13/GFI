"""Parse DESNZ Energy Trends 6.3 solar PV domestic-by-constituency sheet into data/solar.csv.

Uses the "All constituencies" / "All countries" row, which is the true
domestic-only UK total (not the 0-4kW capacity-band proxy).
"""
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "solar.csv"

COLUMNS = ["release_month", "cumulative_capacity_mw", "cumulative_installs"]

MONTH_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})"
)


def parse(xlsx_path: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb["Table_3_dom_by_PC"]

    rows = list(ws.iter_rows(min_row=1, max_col=5, values_only=True))

    title = rows[0][0]
    match = MONTH_RE.search(str(title))
    if not match:
        raise ValueError(f"Could not find release month in title: {title!r}")
    release_month = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%B %Y").strftime("%Y-%m")

    for row in rows:
        constituency_code, country_region = row[0], row[1]
        if constituency_code == "All constituencies" and country_region == "All countries":
            return {
                "release_month": release_month,
                "cumulative_capacity_mw": round(row[3], 2),
                "cumulative_installs": row[4],
            }

    raise ValueError("Could not find 'All constituencies' / 'All countries' total row")


def append_csv(row: dict) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    existing_rows = []
    if OUTPUT_CSV.exists():
        with OUTPUT_CSV.open(newline="") as f:
            existing_rows = list(csv.DictReader(f))

    existing_rows = [r for r in existing_rows if r["release_month"] != row["release_month"]]
    existing_rows.append(row)
    existing_rows.sort(key=lambda r: r["release_month"])

    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(existing_rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: parse_solar.py <path-to-xlsx>")
        sys.exit(1)
    row = parse(Path(sys.argv[1]))
    append_csv(row)
    print(f"Wrote/updated {row['release_month']} in {OUTPUT_CSV}")
