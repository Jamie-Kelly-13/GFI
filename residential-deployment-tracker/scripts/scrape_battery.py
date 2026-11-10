"""Find and download the latest MCS domestic battery installation statistics."""
from __future__ import annotations

import parse_battery
from scrape_common import NoCandidateFound, download, fetch_html, find_file_links

PAGE_URL = "https://www.gov.uk/government/statistics/mcs-certified-domestic-battery-installation-statistics"


def find_and_parse() -> tuple[list[dict], str]:
    soup = fetch_html(PAGE_URL)
    candidates = find_file_links(soup, PAGE_URL, extensions=(".xlsx",))
    if not candidates:
        raise NoCandidateFound(f"No .xlsx attachments found on {PAGE_URL}")

    for file_url in candidates:
        try:
            path = download(file_url)
            rows = parse_battery.parse(path)
            if rows:
                return rows, file_url
        except Exception:
            continue

    raise NoCandidateFound(
        f"Found {len(candidates)} .xlsx file(s) on {PAGE_URL} but none had a 'Monthly' sheet"
    )


if __name__ == "__main__":
    rows, file_url = find_and_parse()
    parse_battery.write_csv(rows)
    print(f"Updated from {file_url}")
    print(f"Wrote {len(rows)} rows to {parse_battery.OUTPUT_CSV}")
