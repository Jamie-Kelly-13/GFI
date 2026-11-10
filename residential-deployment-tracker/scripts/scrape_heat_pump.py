"""Find and download the latest DESNZ heat pump deployment statistics tables.

Starts from the stable gov.uk *collection* page (not the per-release
statistics page, whose URL changes every quarter) and follows through to
the latest release's "tables" spreadsheet.
"""
from __future__ import annotations

from pathlib import Path

import parse_heat_pump
from scrape_common import NoCandidateFound, download, fetch_html, find_file_links

COLLECTION_URL = "https://www.gov.uk/government/collections/heat-pump-deployment-statistics"


def find_latest_release_url() -> str:
    soup = fetch_html(COLLECTION_URL)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/government/statistics/heat-pump-deployment-statistics" in href:
            from urllib.parse import urljoin

            return urljoin(COLLECTION_URL, href)
    raise NoCandidateFound(f"No release link found on collection page: {COLLECTION_URL}")


def find_and_parse() -> tuple[list[dict], str, str]:
    """Returns (rows, release_page_url, file_url) for the latest release that
    successfully parses (i.e. has a 'Table 1.1' sheet)."""
    release_url = find_latest_release_url()
    soup = fetch_html(release_url)
    candidates = find_file_links(soup, release_url, extensions=(".xlsx",))
    if not candidates:
        raise NoCandidateFound(f"No .xlsx attachments found on {release_url}")

    for file_url in candidates:
        try:
            path = download(file_url)
            rows = parse_heat_pump.parse(path)
            if rows:
                return rows, release_url, file_url
        except Exception:
            continue

    raise NoCandidateFound(
        f"Found {len(candidates)} .xlsx file(s) on {release_url} but none had a 'Table 1.1' sheet"
    )


if __name__ == "__main__":
    rows, release_url, file_url = find_and_parse()
    parse_heat_pump.write_csv(rows)
    print(f"Updated from {file_url}\n(release page: {release_url})")
    print(f"Wrote {len(rows)} rows to {parse_heat_pump.OUTPUT_CSV}")
