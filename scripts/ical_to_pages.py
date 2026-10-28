"""Read the calendar's private iCal feed and save it in the format mcr_sync.py expects.
No AI involved. Usage:
  python3 ical_to_pages.py --url "$CALENDAR_ICAL_URL" --out pages/ --from 2026-10-27 --to 2027-03-27
(--file feed.ics can be used instead of --url for testing.)
Each repeating event is expanded into its dates, with recurringEventId set, like the Google Calendar API.
"""
import argparse, json, os, sys, datetime as dt, urllib.request
import icalendar, recurring_ical_events


def gid(uid):
    uid = str(uid)
    return uid[:-len('@google.com')] if uid.endswith('@google.com') else uid


def stamp(v):
    """Google-API style start/end dict."""
    if isinstance(v, dt.datetime):
        if v.tzinfo is None:  # floating time: treat as UK local
            import zoneinfo
            v = v.replace(tzinfo=zoneinfo.ZoneInfo('Europe/London'))
        return {'dateTime': v.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
    return {'date': v.isoformat()}


def convert(ics_bytes, start, end):
    cal = icalendar.Calendar.from_ical(ics_bytes)
    repeating = {gid(c.get('UID')) for c in cal.walk('VEVENT') if c.get('RRULE') or c.get('RECURRENCE-ID')}
    out = []
    for c in recurring_ical_events.of(cal).between(start, end):
        if str(c.get('STATUS', '')).upper() == 'CANCELLED':
            continue
        s = c.get('DTSTART').dt
        e = c.get('DTEND').dt if c.get('DTEND') else (s + dt.timedelta(days=1) if not isinstance(s, dt.datetime) else s + dt.timedelta(hours=1))
        base = gid(c.get('UID'))
        ev = {'summary': str(c.get('SUMMARY', '')), 'location': str(c.get('LOCATION', '') or ''),
              'description': str(c.get('DESCRIPTION', '') or ''), 'start': stamp(s), 'end': stamp(e), 'status': 'confirmed'}
        if base in repeating:
            ev['recurringEventId'] = base
            ev['id'] = base + '_' + (s.astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') if isinstance(s, dt.datetime) else s.strftime('%Y%m%d'))
        else:
            ev['id'] = base
        out.append(ev)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--url'); p.add_argument('--file'); p.add_argument('--out', required=True)
    p.add_argument('--from', dest='start', required=True); p.add_argument('--to', dest='end', required=True)
    a = p.parse_args()
    if a.file:
        data = open(a.file, 'rb').read()
    else:
        if not a.url:
            sys.exit('No calendar address given (set the CALENDAR_ICAL_URL secret).')
        try:
            data = urllib.request.urlopen(a.url, timeout=60).read()
        except Exception as e:
            sys.exit(f'Could not read the calendar ({e}). Make the calendar public, or add the CALENDAR_ICAL_URL secret.')
        if not data.lstrip().startswith(b'BEGIN:VCALENDAR'):
            sys.exit('The calendar address did not return a calendar. Make the calendar public, or add the CALENDAR_ICAL_URL secret.')
    events = convert(data, dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end))
    os.makedirs(a.out, exist_ok=True)
    json.dump({'events': events}, open(os.path.join(a.out, 'calendar.json'), 'w'), ensure_ascii=False)
    print(len(events), 'calendar dates read')
