"""Write poster/listings.json: the site's current listings in a small form the poster maker can load.
Usage: python3 scripts/poster_data.py index.html poster/listings.json [today]
"""
import json, re, sys, datetime as dt

PHONE = re.compile(r'(?:\+44\s?|0)(?:\d[\s-]?){9,10}\d')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')


def events(html):
    a = html.find('id="events-data"'); a = html.find('>', a) + 1; b = html.find('</script>', a)
    return json.loads(html[a:b])


def clean_title(t, venue, org=''):
    """'Baby Time – Gorton Library' or 'Baby Time, Gorton Library' -> 'Baby Time' when the end is the venue."""
    vname = (venue or '').split(',')[0].strip().lower()
    for sep in (' – ', ' — ', ' - ', ', ', ' at '):
        if sep in t:
            head, tail = t.rsplit(sep, 1)
            tl = tail.strip().lower()
            if (vname and (tl in vname or vname in tl or tl.split()[0] == vname.split()[0])) or (org and tl == org.strip().lower()):
                return head.strip()
    return t.strip()


def build(evs, today):
    out = []
    horizon = (today + dt.timedelta(days=120)).isoformat()
    for e in evs:
        if e.get('cost') == 'Paid':
            continue
        r = e.get('rule')
        if r:
            if r.get('until') and r['until'] < today.isoformat():
                continue
        else:
            last = e.get('endDate') or e['date']
            if last < today.isoformat() or e['date'] > horizon:
                continue
        info = (e.get('info') or '')
        rec = {'t': clean_title(e['title'], e.get('venue'), e.get('org') or ''), 'v': e.get('venue', ''), 'a': e.get('area', ''),
               's': e.get('start', ''), 'e': e.get('end', ''), 'c': e.get('cost', ''), 'b': e.get('booking', '')}
        if e.get('org'): rec['o'] = e['org']
        if e.get('link'): rec['l'] = e['link']
        m = PHONE.search(info) or EMAIL.search(info)
        if m: rec['k'] = m.group(0).strip()
        p = re.search(r'£\s?\d+(?:\.\d\d)?', info)
        if e.get('cost') == 'Low cost' and p: rec['p'] = p.group(0).replace(' ', '')
        if r:
            rec['r'] = {k: r[k] for k in ('freq', 'byday', 'interval', 'pos') if k in r}
        else:
            rec['d'] = e['date']
        out.append(rec)
    return out


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    today = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
    data = build(events(open(src).read()), today)
    json.dump({'updated': today.isoformat(), 'items': data}, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(data), 'listings written for the poster maker')
