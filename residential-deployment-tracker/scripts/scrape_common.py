"""Shared helpers for scraping gov.uk statistics pages."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = "GFI-residential-deployment-tracker/1.0 (built environment team research tool)"
TIMEOUT = 30


def fetch_html(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def find_file_links(soup: BeautifulSoup, base_url: str, extensions=(".xlsx", ".ods")) -> list[str]:
    """Return absolute URLs of every link ending in one of the given extensions."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(extensions):
            links.append(urljoin(base_url, href))
    # de-duplicate, preserve order
    seen = set()
    unique = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


def find_links_by_text(soup: BeautifulSoup, base_url: str, must_contain: list[str]) -> list[str]:
    """Return absolute URLs of <a> tags whose visible text contains all given substrings (case-insensitive)."""
    links = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        if all(term.lower() in text for term in must_contain):
            links.append(urljoin(base_url, a["href"]))
    seen = set()
    unique = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


def download(url: str, dest_dir: Path | None = None) -> Path:
    dest_dir = dest_dir or Path(tempfile.mkdtemp(prefix="gfi-tracker-"))
    filename = re.sub(r"[^A-Za-z0-9_.-]", "_", url.split("/")[-1]) or "download.xlsx"
    dest_path = dest_dir / filename
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    dest_path.write_bytes(resp.content)
    return dest_path


class NoCandidateFound(Exception):
    """Raised when a scraper can't confidently find the data file on a page.

    Callers should fall back to telling the user the source page link and
    asking them to download/drop the file in manually.
    """
