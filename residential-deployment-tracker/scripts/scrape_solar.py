"""Find and download the latest Energy Trends 6.3 (solar PV deployment) workbook."""
from __future__ import annotations

from urllib.parse import urljoin

import parse_solar
from scrape_common import NoCandidateFound, download, fetch_html, find_file_links, find_links_by_text

PAGE_URL = "https://www.gov.uk/government/statistics/energy-trends-section-6-renewables"


def find_and_parse() -> tuple[list[dict], str]:
    soup = fetch_html(PAGE_URL)

    # ET 6.3 is one of several tables on this page (6.1, 6.2, 6.3, ...) -
    # narrow to links whose text references "6.3" and "solar" before
    # falling back to scanning every attachment on the page.
    candidates = find_links_by_text(soup, PAGE_URL, must_contain=["6.3"])
    if not candidates:
        candidates = find_file_links(soup, PAGE_URL, extensions=(".xlsx", ".ods"))
    if not candidates:
        raise NoCandidateFound(f"No candidate links found on {PAGE_URL}")

    file_urls = []
    for link in candidates:
        if link.lower().endswith((".xlsx", ".ods")):
            file_urls.append(link)
        else:
            # Link goes to an intermediate page - follow it for attachments.
            try:
                sub_soup = fetch_html(link)
                file_urls.extend(find_file_links(sub_soup, link, extensions=(".xlsx",)))
            except Exception:
                continue

    for file_url in file_urls:
        try:
            path = download(file_url)
            rows = parse_solar.parse(path)
            if rows:
                return rows, file_url
        except Exception:
            continue

    raise NoCandidateFound(
        f"Found {len(file_urls)} candidate file(s) but none had a '{parse_solar.SHEET_NAME}' sheet "
        f"with the expected 'of which: domestic' rows (source page: {PAGE_URL})"
    )


if __name__ == "__main__":
    rows, file_url = find_and_parse()
    parse_solar.write_csv(rows)
    print(f"Updated from {file_url}")
    print(f"Wrote {len(rows)} rows to {parse_solar.OUTPUT_CSV}")
