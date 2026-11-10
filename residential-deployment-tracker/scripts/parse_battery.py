"""Parse MCS domestic retrofit battery installation statistics (Monthly) into data/battery.csv."""
import csv
import sys
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "battery.csv"

COLUMNS = ["year_month", "financial_year", "installs", "sample_installs", "sample_capacity_kwh"]

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def parse(xlsx_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb["Monthly"]

    rows = []
    for row in ws.iter_rows(min_row=5, max_col=6, values_only=True):
        financial_year, calendar_year, month_name = row[0], row[1], row[2]
        if financial_year is None or month_name is None:
            break
        month_num = MONTHS.get(str(month_name).strip())
        if month_num is None:
            continue
        year_month = f"{int(calendar_year)}-{month_num:02d}"
        rows.append(
            {
                "year_month": year_month,
                "financial_year": financial_year,
                "installs": row[3],
                "sample_installs": row[4],
                "sample_capacity_kwh": row[5],
            }
        )
    return rows


def write_csv(rows: list[dict]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: parse_battery.py <path-to-xlsx>")
        sys.exit(1)
    rows = parse(Path(sys.argv[1]))
    write_csv(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
