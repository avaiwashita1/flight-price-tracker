"""Fetch Google Flights results for one route/date and extract nonstop flights.

Uses fast-flights to build the query and fetch the page, but parses the embedded
data ourselves so we can also read flight numbers (needed for flight_id).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from fast_flights import FlightQuery, Passengers, create_query, fetch_flights_html
from selectolax.lexbor import LexborHTMLParser


class FetchError(Exception):
    """The page could not be fetched or did not contain flight data (blocked, captcha, layout change)."""


class EmptyResults(FetchError):
    """The page loaded but listed no flights. On busy routes this means an incomplete page; retry."""


def _shape(obj, depth=2):
    """Short description of a nested list's structure, for diagnostics."""
    if isinstance(obj, list):
        if depth == 0:
            return f"list[{len(obj)}]"
        return "[" + ", ".join(_shape(x, depth - 1) for x in obj[:10]) + (", ..." if len(obj) > 10 else "") + "]"
    return type(obj).__name__ if obj is not None else "None"


@dataclass
class FlightPrice:
    flight_id: str        # e.g. UA123_2026-12-03
    airline: str          # e.g. United
    origin: str
    destination: str
    departure_date: str   # YYYY-MM-DD
    departure_time: str   # HH:MM (local to origin)
    price: int


def _get(obj, *path):
    """Safely index into nested lists; returns None if any step is missing."""
    for i in path:
        if not isinstance(obj, list) or i >= len(obj):
            return None
        obj = obj[i]
    return obj


def _hhmm(value) -> str:
    # Google omits zero components: [8] = 08:00, [None, 31] = 00:31
    padded = [*(value or []), None, None]
    return f"{padded[0] or 0:02d}:{padded[1] or 0:02d}"


def extract_payload(html: str) -> list:
    script = LexborHTMLParser(html).css_first(r"script.ds\:1")
    if script is None:
        raise FetchError("flight data not found in page (possibly blocked or a consent/captcha page)")
    js = script.text()
    try:
        data = js.split("data:", 1)[1].rsplit(",", 1)[0]
    except IndexError as e:
        raise FetchError("unexpected script format") from e
    if data.rstrip().endswith("errorHasStatus: true"):
        return []  # Google says: no flights for this search
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise FetchError("could not decode flight data") from e


def parse_flights(payload: list, origin: str, destination: str, departure_date: str,
                  nonstop_only: bool = True) -> list[FlightPrice]:
    results: dict[str, FlightPrice] = {}
    # payload[2] = "best" flights, payload[3] = "other" flights; read both.
    for section_idx in (2, 3):
        itineraries = _get(payload, section_idx, 0) or []
        for itin in itineraries:
            flight = _get(itin, 0)
            price = _get(itin, 1, 0, 1)
            segments = _get(flight, 2) or []
            if not isinstance(price, (int, float)) or not segments:
                continue
            if nonstop_only and len(segments) != 1:
                continue

            seg = segments[0]
            seg_origin, seg_dest = _get(seg, 3), _get(seg, 6)
            if seg_origin != origin or seg_dest != destination:
                continue  # e.g. a nearby-airport result
            dep_date = _get(seg, 20)
            if dep_date:
                y, m, d = dep_date[:3]
                if f"{y:04d}-{m:02d}-{d:02d}" != departure_date:
                    continue
            dep_time = _hhmm(_get(seg, 8))

            airline_names = _get(flight, 1) or []
            airline = airline_names[0] if airline_names else ""
            carrier_code = _get(seg, 22, 0) or _get(flight, 0) or "XX"
            flight_number = _get(seg, 22, 1)
            if flight_number:
                fid = f"{carrier_code}{flight_number}_{departure_date}"
            else:  # fallback if Google stops exposing flight numbers
                fid = f"{carrier_code}_{dep_time.replace(':', '')}_{departure_date}"
            if not airline:
                airline = _get(seg, 22, 3) or carrier_code

            fp = FlightPrice(fid, airline, origin, destination, departure_date, dep_time, int(price))
            # Keep the lowest price if the same flight appears twice
            if fid not in results or fp.price < results[fid].price:
                results[fid] = fp
    return sorted(results.values(), key=lambda f: f.departure_time)


def search(origin: str, destination: str, departure_date: str, *, nonstop_only=True,
           currency="USD", seat="economy", adults=1) -> list[FlightPrice]:
    query = create_query(
        flights=[FlightQuery(date=departure_date, from_airport=origin, to_airport=destination,
                             max_stops=0 if nonstop_only else None)],
        trip="one-way",
        seat=seat,
        passengers=Passengers(adults=adults),
        language="en-US",
        currency=currency,
    )
    try:
        html = fetch_flights_html(query)
    except Exception as e:
        raise FetchError(f"request failed: {e}") from e
    payload = extract_payload(html)
    flights = parse_flights(payload, origin, destination, departure_date, nonstop_only)
    if not flights:
        title = LexborHTMLParser(html).css_first("title")
        raise EmptyResults(
            f"0 flights; html={len(html)} chars, title={title.text() if title else None!r}, "
            f"payload={_shape(payload)}"
        )
    return flights
