# Flight Price Tracker

Collects the cheapest **nonstop, one-way, economy** fare (USD, 1 adult) for every flight on 5 routes, for every departure date in the next 21 days. It runs every 3 hours on GitHub Actions (free) and writes to Google Sheets (one tab per route), with a CSV backup committed to this repo.

Prices come from Google Flights through the open-source [`fast-flights`](https://github.com/AWeirdDev/fast-flights) library. There's no API key and no cost.

## Columns

| observation_date | observation_time | flight_id | airline | origin | destination | departure_date | days_to_departure | price |
|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | 17:13 | UA123_2026-12-03 | United | SFO | JFK | 2026-12-03 | 21 | $325 |

Times are Pacific (set `TIMEZONE` in `config.py`). The `run_log` tab records one row per run: how many searches succeeded or failed and which ones failed.

## One-time setup (about 20 minutes)

### 1. Google Sheets access (free)
1. Go to https://console.cloud.google.com/ and create a project (any name).
2. Enable the **Google Sheets API**: *APIs & Services → Library → Google Sheets API → Enable*.
3. Create a service account: *APIs & Services → Credentials → Create credentials → Service account*. Name it anything. Skip the optional steps.
4. Open the service account, go to *Keys → Add key → Create new key → JSON*. A `.json` file downloads. Keep it private.
5. Create a blank Google Sheet. Click **Share** and share it with the service account's email (`...@...iam.gserviceaccount.com`) as **Editor**.
6. Copy the Sheet ID from its URL: `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`.

### 2. GitHub
1. Create a **private** GitHub repo and push this folder to it.
2. In the repo, go to *Settings → Secrets and variables → Actions → New repository secret* and add:
   - `SPREADSHEET_ID`: the Sheet ID from step 1.6
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: the entire contents of the downloaded JSON file
3. Go to the *Actions* tab → **Collect flight prices** → **Run workflow** to test it now. Route tabs should appear in your Sheet within about 10 minutes.

After that, it runs automatically every 3 hours.

## Configuration (`config.py`)
- `ROUTES`: the routes to track
- `FIRST_DEPARTURE_DATE` / `LAST_DEPARTURE_DATE` / `LOOKAHEAD_DAYS`: the departure-date window
- Schedule: edit the `cron` line in `.github/workflows/collect.yml` (`"17 * * * *"` = hourly)

## Run locally
```bash
pip install -r requirements.txt
python run.py --dry-run --limit 2     # quick test, no Sheets
python -m pytest tests                # parser tests (offline)
```

## Things to know
- **Scraping:** Google's terms of service don't allow automated access. Google can block requests or change its page format at any time. If that happens, the `run_log` tab shows failed searches, and the job fails (GitHub emails you) when every search fails. Updating `fast-flights` usually fixes format changes.
- **GitHub free minutes:** private repos get 2,000 minutes per month. Every 3 hours uses about 1,000–1,500. Hourly would go over the limit unless the repo is public, which would also make the CSV data public.
- **Sheet size:** Google Sheets allows 10 million cells. This collects about 3,000–5,000 rows per run. That's fine for a few weeks but fills up in about 2–3 months. The CSVs in `data/` keep everything regardless.
- **Southwest** may be missing from Google Flights results or incomplete. Check your data before drawing conclusions about routes Southwest flies.
