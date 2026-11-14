"""One collection run: search every route x departure date once and record prices.

Usage:
    python run.py              # search, save CSVs, rebuild output/flight_prices.xlsx
                               # (also writes to Google Sheets if credentials are set)
    python run.py --dry-run    # search and print/CSV only, no Google Sheets
    python run.py --limit 2    # only search the first 2 dates per route (quick test)
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from tracker.scrape import FetchError, search
from tracker.excel import build_workbook
from tracker.sheets import RUN_LOG_HEADER, append_csv, writer_from_env


def departure_dates(today: date) -> list[date]:
    start = max(today, config.FIRST_DEPARTURE_DATE)
    end = today + timedelta(days=config.LOOKAHEAD_DAYS)
    if config.LAST_DEPARTURE_DATE:
        end = min(end, config.LAST_DEPARTURE_DATE)
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def try_search(origin, dest, dep: str, attempt: int):
    try:
        return search(origin, dest, dep, nonstop_only=config.NONSTOP_ONLY,
                      currency=config.CURRENCY, seat=config.SEAT, adults=config.ADULTS)
    except FetchError as e:
        print(f"  attempt {attempt} failed for {origin}-{dest} {dep}: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't write to Google Sheets")
    ap.add_argument("--limit", type=int, default=None, help="max departure dates per route")
    args = ap.parse_args()

    now = datetime.now(ZoneInfo(config.TIMEZONE))
    obs_date, obs_time = now.date(), now.strftime("%H:%M")
    dates = departure_dates(obs_date)[: args.limit]
    if not dates:
        print("No departure dates in the collection window; nothing to do.")
        return

    writer = None if args.dry_run else writer_from_env()

    # First pass over every search; failures are retried in later passes so Google has
    # time to recover instead of us hammering the same search back to back.
    pending = [(o, d, dep) for o, d in config.ROUTES for dep in dates]
    results = {}
    for attempt in range(1, config.MAX_ATTEMPTS + 1):
        if attempt > 1:
            if not pending:
                break
            print(f"Retry pass {attempt}: {len(pending)} searches")
            time.sleep(min(config.RETRY_BACKOFF_SECONDS * (attempt - 1), 120))
        still_failing = []
        for origin, dest, dep in pending:
            flights = try_search(origin, dest, dep.isoformat(), attempt)
            if flights is None:
                still_failing.append((origin, dest, dep))
            else:
                results[(origin, dest, dep)] = flights
                print(f"{origin}-{dest} {dep}: {len(flights)} nonstop flights")
            time.sleep(random.uniform(*config.DELAY_BETWEEN_SEARCHES))
        pending = still_failing

    ok, total_rows = len(results), 0
    failed = [f"{o}-{d} {dep}" for o, d, dep in pending]
    for origin, dest in config.ROUTES:
        tab = f"{origin}-{dest}"
        rows = []
        for dep in dates:
            for f in results.get((origin, dest, dep), []):
                rows.append([obs_date.isoformat(), obs_time, f.flight_id, f.airline, origin,
                             dest, dep.isoformat(), (dep - obs_date).days, f.price])
        append_csv(config.CSV_BACKUP_DIR, obs_date.strftime("%Y-%m"), rows)
        if writer:
            try:
                writer.append(tab, rows)
            except Exception as e:  # CSV backup still has the data
                print(f"Google Sheets write failed for {tab}: {e}", file=sys.stderr)
        total_rows += len(rows)

    summary = [obs_date.isoformat(), obs_time, ok, len(failed), total_rows, "; ".join(failed)]
    print(f"Done: {ok} searches ok, {len(failed)} failed, {total_rows} rows.")
    log_path = Path(config.CSV_BACKUP_DIR) / "run_log.csv"
    new_log = not log_path.exists()
    with log_path.open("a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(RUN_LOG_HEADER)
        w.writerow(summary)
    n = build_workbook(config.CSV_BACKUP_DIR, config.EXCEL_FILE,
                       [f"{o}-{d}" for o, d in config.ROUTES])
    print(f"Wrote {config.EXCEL_FILE} ({n} rows total).")
    if writer:
        try:
            writer.append(config.RUN_LOG_TAB, [summary], header=RUN_LOG_HEADER, price_col=False)
        except Exception as e:
            print(f"Could not write run log: {e}", file=sys.stderr)

    # Fail the job (so GitHub emails you) if every search failed, e.g. Google is blocking us.
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
