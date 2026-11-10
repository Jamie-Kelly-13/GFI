"""Orchestrator: check all 3 sources for new data, update CSVs, rebuild chart.

Designed to be run by the scheduled GitHub Action, but safe to run locally
too. Never raises on a single source failing - it logs the problem and the
source page link (for a manual fallback) and continues with the others.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import build_chart
import scrape_battery
import scrape_heat_pump
import scrape_solar

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = REPO_ROOT / "data" / "last_checked.json"


def load_status() -> dict:
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {}


def save_status(status: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2, sort_keys=True))


def check_heat_pump(status: dict) -> bool:
    try:
        rows, release_url, file_url = scrape_heat_pump.find_and_parse()
    except Exception as exc:
        status["heat_pump"] = {
            "ok": False,
            "error": str(exc),
            "source_page": scrape_heat_pump.COLLECTION_URL,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"[heat_pump] FAILED: {exc}")
        return False

    latest = rows[-1]["quarter"] if rows else None
    changed = latest != status.get("heat_pump", {}).get("latest_period")
    if changed:
        import parse_heat_pump

        parse_heat_pump.write_csv(rows)
        print(f"[heat_pump] updated, latest period: {latest}")
    else:
        print(f"[heat_pump] no change (latest period still {latest})")

    status["heat_pump"] = {
        "ok": True,
        "latest_period": latest,
        "source_page": release_url,
        "file_url": file_url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    return changed


def check_battery(status: dict) -> bool:
    try:
        rows, file_url = scrape_battery.find_and_parse()
    except Exception as exc:
        status["battery"] = {
            "ok": False,
            "error": str(exc),
            "source_page": scrape_battery.PAGE_URL,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"[battery] FAILED: {exc}")
        return False

    latest = rows[-1]["year_month"] if rows else None
    changed = latest != status.get("battery", {}).get("latest_period")
    if changed:
        import parse_battery

        parse_battery.write_csv(rows)
        print(f"[battery] updated, latest period: {latest}")
    else:
        print(f"[battery] no change (latest period still {latest})")

    status["battery"] = {
        "ok": True,
        "latest_period": latest,
        "source_page": scrape_battery.PAGE_URL,
        "file_url": file_url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    return changed


def check_solar(status: dict) -> bool:
    try:
        rows, file_url = scrape_solar.find_and_parse()
    except Exception as exc:
        status["solar"] = {
            "ok": False,
            "error": str(exc),
            "source_page": scrape_solar.PAGE_URL,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"[solar] FAILED: {exc}")
        return False

    import parse_solar

    latest = rows[-1]["year_month"] if rows else None
    changed = latest != status.get("solar", {}).get("latest_period")
    if changed:
        parse_solar.write_csv(rows)
        print(f"[solar] updated, latest period: {latest}")
    else:
        print(f"[solar] no change (latest period still {latest})")

    status["solar"] = {
        "ok": True,
        "latest_period": latest,
        "source_page": scrape_solar.PAGE_URL,
        "file_url": file_url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    return changed


def main() -> None:
    status = load_status()
    any_changed = False
    any_changed |= check_heat_pump(status)
    any_changed |= check_battery(status)
    any_changed |= check_solar(status)
    save_status(status)

    if any_changed:
        build_chart.build()
        print("New data found - chart rebuilt.")
    else:
        print("No new data from any source.")


if __name__ == "__main__":
    main()
