"""Offline tests for the parser using a fake Google Flights page with the same structure."""

import json

from tracker.scrape import extract_payload, parse_flights


def seg(orig, dest, hm, ymd, code, num, name):
    s = [None] * 23
    s[3], s[6], s[8], s[20], s[22] = orig, dest, hm, ymd, [code, num, None, name]
    return s


def itin(names, segs, price):
    f = [None] * 23
    f[0], f[1], f[2] = "multi" if len(names) > 1 else "X", names, segs
    return [f, [[None, price]]]


def fake_html(payload):
    return ('<html><script class="ds:1">AF_initDataCallback({key: \'ds:1\', hash: \'1\', data:'
            + json.dumps(payload) + ', sideChannel: {}});</script></html>')


def test_parse():
    best = [itin(["United"], [seg("SFO", "JFK", [8, 5], [2026, 12, 3], "UA", "123", "United")], 325)]
    other = [
        itin(["JetBlue"], [seg("SFO", "JFK", [None, 30], [2026, 12, 3], "B6", "916", "JetBlue")], 289),
        # duplicate of UA123 at a higher price -> lowest kept
        itin(["United"], [seg("SFO", "JFK", [8, 5], [2026, 12, 3], "UA", "123", "United")], 399),
        # one-stop -> excluded
        itin(["Delta"], [seg("SFO", "SLC", [6], [2026, 12, 3], "DL", "1", "Delta"),
                         seg("SLC", "JFK", [11], [2026, 12, 3], "DL", "2", "Delta")], 199),
        # nearby airport -> excluded
        itin(["Alaska"], [seg("OAK", "JFK", [7], [2026, 12, 3], "AS", "9", "Alaska")], 250),
    ]
    payload = [None, None, [best], [other]]
    flights = parse_flights(extract_payload(fake_html(payload)), "SFO", "JFK", "2026-12-03")
    assert [(f.flight_id, f.airline, f.departure_time, f.price) for f in flights] == [
        ("B6916_2026-12-03", "JetBlue", "00:30", 289),
        ("UA123_2026-12-03", "United", "08:05", 325),
    ]


def test_no_flights():
    html = '<script class="ds:1">AF_initDataCallback({key: \'ds:1\', data:errorHasStatus: true, x: 1});</script>'
    assert extract_payload(html) == []


def test_excel(tmp_path):
    from openpyxl import load_workbook

    from tracker.excel import build_workbook
    from tracker.sheets import append_csv

    append_csv(tmp_path, "2026-11", [
        ["2026-11-13", "17:13", "UA123_2026-12-03", "United", "SFO", "JFK", "2026-12-03", 20, 325],
        ["2026-11-13", "17:13", "DL1_2026-12-03", "Delta", "ATL", "MCO", "2026-12-03", 20, 99],
    ])
    out = tmp_path / "out.xlsx"
    assert build_workbook(str(tmp_path), str(out), ["SFO-JFK", "ATL-MCO"]) == 2
    wb = load_workbook(out)
    assert wb.sheetnames == ["SFO-JFK", "ATL-MCO", "run_log"]
    row = [c.value for c in wb["SFO-JFK"][2]]
    assert row[2] == "UA123_2026-12-03" and row[7] == 20 and row[8] == 325
