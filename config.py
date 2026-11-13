"""Settings for the flight price tracker. Edit this file to change what gets collected."""

from datetime import date

# One-way routes to track: (origin, destination). Each route gets its own spreadsheet tab.
ROUTES = [
    ("SFO", "JFK"),  # Transcontinental, business-heavy; United, JetBlue, Delta, American, Alaska
    ("ORD", "LGA"),  # Business route between three legacy-carrier hubs; United, American, Delta
    ("ATL", "MCO"),  # Leisure; Delta's hub vs. low-cost carriers (Frontier, Spirit, Southwest)
    ("DEN", "LAS"),  # Leisure, heavy ultra-low-cost competition (Frontier, Southwest, United, Spirit)
    ("SEA", "LAX"),  # West-coast hub fight: Alaska vs. Delta, plus others
]

# Departure dates to search on every run: from max(today, FIRST_DEPARTURE_DATE)
# through today + LOOKAHEAD_DAYS.
FIRST_DEPARTURE_DATE = date(2026, 11, 20)
LAST_DEPARTURE_DATE = None  # e.g. date(2027, 1, 31) to stop collecting; None = no end
LOOKAHEAD_DAYS = 21

# Search settings
NONSTOP_ONLY = True
CURRENCY = "USD"
SEAT = "economy"
ADULTS = 1

# Timezone used for observation_date / observation_time / days_to_departure
TIMEZONE = "America/Los_Angeles"

# Politeness and reliability
DELAY_BETWEEN_SEARCHES = (1.5, 3.5)  # random pause in seconds between searches
MAX_ATTEMPTS = 3                     # attempts per search before giving up
RETRY_BACKOFF_SECONDS = 15           # wait 15s, then 30s, ... between attempts

# Output
CSV_BACKUP_DIR = "data"     # every row is also appended to a monthly CSV here
RUN_LOG_TAB = "run_log"     # spreadsheet tab with one line per run (success/failure counts)
