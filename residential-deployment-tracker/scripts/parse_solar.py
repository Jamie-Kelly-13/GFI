"""Parse DESNZ Energy Trends 6.3 solar PV workbook into data/solar.csv.

Uses the UK "of which: domestic" rows in Table_1_by_Capacity - one under
the CUMULATIVE CAPACITY (MW) table, one under the CUMULATIVE COUNT table.
Both carry the full monthly history since Jan 2010, not just the current
release's snapshot, so (like heat pump/battery) this file is rewritten in
full on every parse rather than appended to.
"""
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "solar.csv"
SHEET_NAME = "Table_1_by_Capacity"

COLUMNS = ["year_month", "cumulative_capacity_mw", "cumulative_installs"]

MONTH_HEADER_RE = re.compile(r"([A-Za-z]{3})\s*\n?\s*(\d{4})")
MONTH_ABBR = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_month_headers(header_row: tuple) -> list[str]:
    year_months = []
    for cell in header_row[1:]:
        if cell is None:
            break
        match = MONTH_HEADER_RE.search(str(cell))
        if not match:
            break
        month = MONTH_ABBR[match.group(1)]
        year = int(match.group(2))
        year_months.append(f"{year}-{month:02d}")
    return year_months


def parse(xlsx_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb[SHEET_NAME]

    rows = list(ws.iter_rows(values_only=True))

    capacity_header_idx = next(
        i for i, r in enumerate(rows) if r and r[0] == "CUMULATIVE CAPACITY (MW) [note 1]"
    )
    count_header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "CUMULATIVE COUNT")

    capacity_months = _parse_month_headers(rows[capacity_header_idx])
    count_months = _parse_month_headers(rows[count_header_idx])

    def find_uk_domestic_row(start_idx: int) -> tuple:
        # "of which: domestic" appears once, in the UK block, after the
        # GB and NI blocks within this table.
        for r in rows[start_idx:]:
            if r and r[0] is None:
                break
            if r and str(r[0]).startswith("of which: domestic"):
                return r
        raise ValueError(f"Could not find 'of which: domestic' row after row {start_idx}")

    capacity_row = find_uk_domestic_row(capacity_header_idx)
    count_row = find_uk_domestic_row(count_header_idx)

    capacity_by_month = dict(zip(capacity_months, capacity_row[1:]))
    count_by_month = dict(zip(count_months, count_row[1:]))

    all_months = sorted(set(capacity_by_month) | set(count_by_month))
    out_rows = []
    for ym in all_months:
        cap = capacity_by_month.get(ym)
        cnt = count_by_month.get(ym)
        out_rows.append(
            {
                "year_month": ym,
                "cumulative_capacity_mw": round(cap, 2) if cap is not None else "",
                "cumulative_installs": cnt if cnt is not None else "",
            }
        )
    return out_rows


def write_csv(rows: list[dict]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: parse_solar.py <path-to-xlsx>")
        sys.exit(1)
    rows = parse(Path(sys.argv[1]))
    write_csv(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
