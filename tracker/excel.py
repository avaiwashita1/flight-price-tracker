"""Build an Excel workbook (one tab per route + run_log) from the CSV files in data/."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

from tracker.sheets import HEADER, RUN_LOG_HEADER

PRICE_FORMAT = '"$"#,##0'


def _date_cell(ws, value: str):
    cell = WriteOnlyCell(ws, value=date.fromisoformat(value))
    cell.number_format = "yyyy-mm-dd"
    return cell


def build_workbook(data_dir: str, out_path: str, route_order: list[str]) -> int:
    by_route: dict[str, list[list[str]]] = defaultdict(list)
    for path in sorted(Path(data_dir).glob("observations_*.csv")):
        with path.open(newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            for row in reader:
                if len(row) == len(HEADER):
                    by_route[f"{row[4]}-{row[5]}"].append(row)

    wb = Workbook(write_only=True)
    routes = [r for r in route_order if r in by_route] + sorted(set(by_route) - set(route_order))
    for route in routes:
        ws = wb.create_sheet(title=route)
        ws.freeze_panes = "A2"
        ws.append(HEADER)
        for row in by_route[route]:
            price = WriteOnlyCell(ws, value=int(row[8]))
            price.number_format = PRICE_FORMAT
            ws.append([_date_cell(ws, row[0]), row[1], *row[2:6], _date_cell(ws, row[6]), int(row[7]), price])

    log_path = Path(data_dir) / "run_log.csv"
    ws = wb.create_sheet(title="run_log")
    if log_path.exists():
        with log_path.open(newline="") as f:
            for row in csv.reader(f):
                ws.append(row)
    else:
        ws.append(RUN_LOG_HEADER)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return sum(len(v) for v in by_route.values())
