# How the website updates itself

Every morning (about 9am) GitHub runs `.github/workflows/update-site.yml`. No AI is involved.

1. **`read_calendar.py`** reads the private "MCR Free Community Events" Google Calendar (via the CALENDAR_ICAL_URL secret).
2. **`build_site.py`** rebuilds `index.html` from it, using:
   - **`events.py`** – turns calendar entries into listings (area, cost, repeats, duplicates).
   - **`search_info.py`** – adds the information Google and AI search tools read.
   - **`landing_pages.py`** – builds a page for each borough (`/area/…`) and each type of activity (`/activity/…`), plus the Christmas page (`/christmas/`, events with words like Christmas, festive, Santa or carols, until 6 January).
3. If anything changed, the new page is published.

**Safety:** nothing is published if the calendar gives fewer than 100 listings, or more than 15% would disappear
at once. GitHub then emails you. To publish anyway: Actions → "Update site from calendar" → Run workflow → tick "force".

**Results of each run:** GitHub → Actions → "Update site from calendar" → the run → summary (added, removed, things to check).

**To add or change events:** edit the Google Calendar. Don't edit `index.html` by hand – it is rebuilt every morning
(except the page design and menu, which are kept).
