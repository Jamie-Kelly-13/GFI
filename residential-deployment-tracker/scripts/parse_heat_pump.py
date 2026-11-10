"""Parse DESNZ heat pump deployment statistics (Table 1.1) into data/heat_pump.csv."""
import csv
import sys
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "heat_pump.csv"

COLUMNS = ["quarter", "air_source_installs", "ground_water_source_installs", "total_installs"]


def parse(xlsx_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb["Table 1.1"]

    rows = []
    for row in ws.iter_rows(min_row=7, max_col=4, values_only=True):
        quarter_label = row[0]
        if quarter_label is None:
            break
        # e.g. "2018 Q1: January to March" -> "2018 Q1"
        quarter = str(quarter_label).split(":")[0].strip()
        rows.append(
            {
                "quarter": quarter,
                "air_source_installs": row[1],
                "ground_water_source_installs": row[2],
                "total_installs": row[3],
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
        print("Usage: parse_heat_pump.py <path-to-xlsx>")
        sys.exit(1)
    rows = parse(Path(sys.argv[1]))
    write_csv(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
