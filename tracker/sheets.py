"""Append rows to Google Sheets (one tab per route) and to a CSV backup."""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path

HEADER = [
    "observation_date", "observation_time", "flight_id", "airline", "origin",
    "destination", "departure_date", "days_to_departure", "price",
]
RUN_LOG_HEADER = [
    "observation_date", "observation_time", "searches_ok", "searches_failed",
    "rows_written", "failed_searches",
]


def _retry(fn, attempts=4, wait=10):
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(wait * (2 ** i))


class SheetWriter:
    def __init__(self, spreadsheet_id: str, service_account_json: str):
        import gspread

        creds = json.loads(service_account_json)
        self.client = gspread.service_account_from_dict(creds)
        self.book = _retry(lambda: self.client.open_by_key(spreadsheet_id))
        self._tabs = {ws.title: ws for ws in self.book.worksheets()}

    def _tab(self, name: str, header: list[str], price_col: bool):
        if name in self._tabs:
            return self._tabs[name]
        ws = _retry(lambda: self.book.add_worksheet(title=name, rows=1000, cols=len(header)))
        _retry(lambda: ws.append_row(header))
        ws.freeze(rows=1)
        if price_col:
            ws.format("I:I", {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0"}})
        self._tabs[name] = ws
        return ws

    def append(self, tab: str, rows: list[list], header=HEADER, price_col=True):
        if not rows:
            return
        ws = self._tab(tab, header, price_col)
        _retry(lambda: ws.append_rows(rows, value_input_option="USER_ENTERED"))


def append_csv(directory: str, month: str, rows: list[list]):
    if not rows:
        return
    path = Path(directory) / f"observations_{month}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
        w.writerows(rows)


def writer_from_env() -> SheetWriter | None:
    sid = os.environ.get("SPREADSHEET_ID")
    creds = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sid or not creds:
        return None
    return SheetWriter(sid, creds)
