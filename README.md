# Flight Price Tracker

Collects the cheapest **nonstop, one-way, economy** fare (USD, 1 adult) for every flight on 5 routes, for every departure date in the next 21 days. It runs every 3 hours on GitHub Actions (free). The output is an **Excel file** with one tab per route. No Google Cloud or other accounts are needed.

Prices come from Google Flights through the open-source [`fast-flights`](https://github.com/AWeirdDev/fast-flights) library. There's no API key and no cost.

## Columns

| observation_date | observation_time | flight_id | airline | origin | destination | departure_date | days_to_departure | price |
|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | 17:13 | UA123_2026-12-03 | United | SFO | JFK | 2026-12-03 | 21 | $325 |

Times are Pacific (set `TIMEZONE` in `config.py`). The `run_log` tab records one row per run: how many searches succeeded or failed and which ones failed.

## Getting your data
**Excel file (all data so far):**
1. In the repo, open the **Actions** tab → **Collect flight prices**.
2. Click the most recent run with a green check.
3. Scroll to **Artifacts** and download **flight_prices**. It's a zip containing `flight_prices.xlsx`.

Each run's Excel file contains *all* data collected so far, so you only ever need the latest one. Downloads are kept for 7 days.

**Raw CSVs:** every row is also saved in `data/observations_YYYY-MM.csv` in the repo itself. This is the permanent master copy. The Excel file is rebuilt from it each run.

## Setup
None. The schedule starts automatically once this is on GitHub. To start a run now: **Actions** tab → **Collect flight prices** → **Run workflow**.

## Configuration (`config.py`)
- `ROUTES`: the routes to track
- `FIRST_DEPARTURE_DATE` / `LAST_DEPARTURE_DATE` / `LOOKAHEAD_DAYS`: the departure-date window
- Schedule: edit the `cron` line in `.github/workflows/collect.yml` (`"17 * * * *"` = hourly)

## Run locally
```bash
pip install -r requirements.txt
python run.py --limit 2       # quick test: 2 dates per route
python -m pytest tests        # offline tests
```

## Optional: Google Sheets
If you have Google Cloud access (e.g. a personal Gmail account), the script can also write to a Google Sheet live. Create a service account with the Sheets API enabled, share a Sheet with its email, and add the repo secrets `SPREADSHEET_ID` and `GOOGLE_SERVICE_ACCOUNT_JSON`. Without those secrets, this step is skipped.

## Things to know
- **Scraping:** Google's terms of service don't allow automated access. Google can block requests or change its page format at any time. If that happens, the `run_log` shows failed searches, and the job fails (GitHub emails you) when every search fails. Updating `fast-flights` usually fixes format changes.
- **GitHub free minutes:** private repos get 2,000 minutes per month. Every 3 hours uses about 1,000–1,500. Hourly would go over the limit unless the repo is public, which would also make the data public.
- **Southwest** may be missing from Google Flights results or incomplete. Check your data before drawing conclusions about routes Southwest flies.
