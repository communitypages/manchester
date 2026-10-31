"""Turns calendar entries into website listings.

Works out each listing's area (from the postcode), category, cost, booking and how often it repeats,
leaves out obvious duplicates, and flags anything to check (no postcode, unknown area, listing rules).
Used by build_site.py – you don't run this file yourself.
"""
import json, re, collections, datetime as dt

OTHER = 'Other / check venue'
AREA_BY_PC = {'BL0': 'Bury', 'BL1': 'Bolton', 'BL2': 'Bolton', 'BL3': 'Bolton', 'BL4': 'Bolton', 'BL5': 'Bolton', 'BL6': 'Bolton', 'BL7': 'Bolton',
  'BL8': 'Bury', 'BL9': 'Bury', 'M1': 'City centre & Ardwick', 'M2': 'City centre & Ardwick', 'M3': 'City centre & Ardwick', 'M4': 'City centre & Ardwick',
  'M8': 'North Manchester', 'M9': 'North Manchester', 'M40': 'North Manchester',
  'M11': 'Gorton, Longsight & Openshaw', 'M12': 'Gorton, Longsight & Openshaw', 'M18': 'Gorton, Longsight & Openshaw',
  'M13': 'Fallowfield, Rusholme & Levenshulme', 'M14': 'Fallowfield, Rusholme & Levenshulme', 'M19': 'Fallowfield, Rusholme & Levenshulme',
  'M15': 'Hulme & Moss Side', 'M16': 'Chorlton & Whalley Range', 'M21': 'Chorlton & Whalley Range',
  'M20': 'Didsbury & Withington', 'M22': 'Wythenshawe', 'M23': 'Wythenshawe', 'M90': 'Wythenshawe',
  'M24': 'Rochdale', 'M25': 'Bury', 'M26': 'Bury',
  'M27': 'Salford', 'M28': 'Salford', 'M29': 'Wigan', 'M30': 'Salford', 'M31': 'Partington', 'M32': 'Stretford & Old Trafford',
  'M33': 'Sale & Timperley', 'M34': 'Tameside', 'M35': 'Oldham', 'M38': 'Salford', 'M41': 'Urmston & Flixton', 'M43': 'Tameside', 'M44': 'Salford',
  'M45': 'Bury', 'M46': 'Wigan', 'M5': 'Salford', 'M6': 'Salford', 'M7': 'Salford', 'M50': 'Salford',
  'OL1': 'Oldham', 'OL2': 'Oldham', 'OL3': 'Oldham', 'OL4': 'Oldham', 'OL8': 'Oldham', 'OL9': 'Oldham', 'OL10': 'Rochdale', 'OL11': 'Rochdale',
  'OL12': 'Rochdale', 'OL15': 'Rochdale', 'OL16': 'Rochdale', 'OL5': 'Tameside', 'OL6': 'Tameside', 'OL7': 'Tameside',
  'SK1': 'Stockport & Marple', 'SK2': 'Stockport & Marple', 'SK3': 'Stockport & Marple', 'SK4': 'Stockport & Marple', 'SK5': 'Stockport & Marple',
  'SK6': 'Stockport & Marple', 'SK7': 'Stockport & Marple', 'SK8': 'Stockport & Marple', 'SK14': 'Tameside', 'SK15': 'Tameside', 'SK16': 'Tameside',
  'WA13': OTHER, 'WA14': 'Altrincham & Hale', 'WA15': 'Sale & Timperley',
  'WN1': 'Wigan', 'WN2': 'Wigan', 'WN3': 'Wigan', 'WN4': 'Wigan', 'WN5': 'Wigan', 'WN6': 'Wigan', 'WN7': 'Wigan'}
# Districts split between areas: the place name in the address decides first, then the postcode sector.
SPLIT_DISTRICTS = {'M16'}
AREA_BY_SECTOR = {'M16 0': 'Stretford & Old Trafford', 'M16 9': 'Stretford & Old Trafford', 'M16 8': 'Chorlton & Whalley Range'}
AREA_BY_WORD = [('moss side', 'Hulme & Moss Side'), ('hulme', 'Hulme & Moss Side'), ('moston', 'North Manchester'), ('harpurhey', 'North Manchester'),
  ('blackley', 'North Manchester'), ('cheetham', 'North Manchester'), ('ardwick', 'City centre & Ardwick'), ('ancoats', 'City centre & Ardwick'),
  ('city centre', 'City centre & Ardwick'), ('wythenshawe', 'Wythenshawe'), ('sharston', 'Wythenshawe'), ('baguley', 'Wythenshawe'),
  ('didsbury', 'Didsbury & Withington'), ('withington', 'Didsbury & Withington'),
  ('gorton', 'Gorton, Longsight & Openshaw'), ('longsight', 'Gorton, Longsight & Openshaw'), ('openshaw', 'Gorton, Longsight & Openshaw'),
  ('levenshulme', 'Fallowfield, Rusholme & Levenshulme'), ('rusholme', 'Fallowfield, Rusholme & Levenshulme'),
  ('fallowfield', 'Fallowfield, Rusholme & Levenshulme'), ('old trafford', 'Stretford & Old Trafford'),
  ('chorlton', 'Chorlton & Whalley Range'), ('whalley range', 'Chorlton & Whalley Range'), ('alexandra park', 'Chorlton & Whalley Range'),
  ('stretford', 'Stretford & Old Trafford'), ('urmston', 'Urmston & Flixton'), ('flixton', 'Urmston & Flixton'), ('davyhulme', 'Urmston & Flixton'),
  ('altrincham', 'Altrincham & Hale'), ('sale', 'Sale & Timperley'), ('salford', 'Salford'),
  ('stockport', 'Stockport & Marple'), ('marple', 'Stockport & Marple'), ('romiley', 'Stockport & Marple'), ('tameside', 'Tameside'),
  ('ashton', 'Tameside'), ('oldham', 'Oldham'), ('rochdale', 'Rochdale'), ('bury', 'Bury'), ('bolton', 'Bolton'), ('wigan', 'Wigan'),
  ('manchester', 'City centre & Ardwick')]
# Order areas appear in the app's "regular groups" view (new names are added to the app's list if missing).
AREA_ORDER = ['City centre & Ardwick', 'Hulme & Moss Side', 'Chorlton & Whalley Range', 'Fallowfield, Rusholme & Levenshulme',
  'Gorton, Longsight & Openshaw', 'Didsbury & Withington', 'Wythenshawe', 'North Manchester', 'Stretford & Old Trafford',
  'Urmston & Flixton', 'Sale & Timperley', 'Altrincham & Hale', 'Partington', 'Salford', 'Stockport & Marple', 'Tameside', 'Oldham',
  'Rochdale', 'Bury', 'Bolton', 'Wigan', OTHER]
CATS = [('Family & kids', r'\b(kids?|child|toddler|baby|under-5s|storytime|stay and play|play-d-barn|lego|homework|rhyme|family|half term|youth|ages \d)'),
  ('Learning & skills', r'(esol|english|digital|\bit\b|computer|job|work club|study|skills|advice|homework|tech)'),
  ('Music & singing', r'(choir|sing|music|jam|ukulele|band|dj)'),
  ('Active & sport', r'(running|exercise|tai chi|yoga|dance|boxing|fitness|pilates|walk\b|football|chess)'),
  ('Film & talks', r'(cinema|film|talk|panel|philosophy|lecture|briefing)'),
  ('Outdoors & nature', r'(garden|brook walk|nature|\bpark\b|allotment|lantern parade|\btrees?\b)'),
  ('Arts, crafts & writing', r'(craft|art|knit|colouring|sewing|poetry|writing|book club|\blit\b|reading|exhibition|tour|embroidery|lit )'),
  ('Food & markets', r'(food bank|lunch|soup|meal|eat|market|brunch)'),
  ('Wellbeing & support', r'(wellbeing|support|coffee|drop-in|social|ladies|women|lgbt|pride|friends|pop-in|forum|tenants|age friendly|over-?50|over-?65)')]
# Words that suggest an event may be against the listing rules (political/campaign, religious worship, business).
# These are only flagged in the report for Lu to decide; nothing is removed automatically.
RULE_CHECK = r'(anarch|protest|rally|campaign|petition|vigil|emergency briefing|political|party meeting|worship|prayer|bible|\bmass\b|alpha course|church service|eucharist|build a business|business (insights|support|networking|basics)|entrepreneur|networking)'
WD = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
POSTCODE = re.compile(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b')

def local(st, all_day=False):
    """Date and 'HH:MM' local time for a calendar start/end value. All-day values give time ''."""
    if all_day or 'T' not in st:
        return dt.date.fromisoformat(st[:10]), ''
    import zoneinfo
    t = dt.datetime.fromisoformat(st.replace('Z', '+00:00')).astimezone(zoneinfo.ZoneInfo('Europe/London'))
    return t.date(), t.strftime('%H:%M')

def when(x):
    """(value, is_all_day) for a calendar start/end dict. The connector returns all-day dates as 'YYYY-MM-DDT00:00:00Z' in 'date'."""
    return (x['dateTime'], False) if x.get('dateTime') else (x['date'], True)

def _by_word(loc):
    l = (loc or '').lower()
    for w, a in AREA_BY_WORD:
        if w != 'manchester' and re.search(r'\b' + w + r'\b', l): return a
    return None

def _district(loc):
    m = re.search(r'\b([A-Z]{1,2}\d{1,2})\s?\d[A-Z]{2}\b', loc or '')
    return m.group(1) if m else None

def area_for(loc):
    m = re.search(r'\b([A-Z]{1,2}\d{1,2})\s?(\d)[A-Z]{2}\b', loc or '')
    if m:
        if m.group(1) in SPLIT_DISTRICTS:
            return _by_word(loc) or AREA_BY_SECTOR.get(m.group(1) + ' ' + m.group(2)) or AREA_BY_PC[m.group(1)]
        if m.group(1) in AREA_BY_PC: return AREA_BY_PC[m.group(1)]
    return _by_word(loc) or ('City centre & Ardwick' if re.search(r'\bmanchester\b', (loc or '').lower()) else OTHER)

def cat_for(title, desc):
    t = (title + ' ').lower()
    for c, rx in CATS:
        if re.search(rx, t): return c
    d = (desc or '').lower()
    for c, rx in CATS:
        if re.search(rx, d): return c
    return 'Community'

COSTS = [('pay what you can', 'Pay what you can'), ('pay as you feel', 'Pay what you can'), ('donation', 'Pay what you can'),
         ('price not stated', 'Price not stated'), ('low cost', 'Low cost'), ('free', 'Free'), ('paid', 'Paid'), ('£', 'Paid')]
LOW_COST_LIMIT = 5.0  # events whose highest price is this many pounds or less count as 'Low cost' (up to £5 is ok)

def price_band(text):
    """'Low cost' if every £ amount in text is at or under the limit, 'Paid' if any is over it, None if no £ amount."""
    amounts = [float(a) for a in re.findall(r'£\s?(\d+(?:\.\d+)?)', text or '')]
    pence = [int(p) / 100 for p in re.findall(r'\b(\d{1,2})p\b', text or '')]
    if not amounts and not pence: return None
    return 'Low cost' if max(amounts + pence) <= LOW_COST_LIMIT else 'Paid'

def parse_desc(desc):
    out = {}
    d = (desc or '').strip()
    if re.search(r'(end|finish) time (is a guess|not given)', d, re.I):
        out['endGuess'] = True
        d = re.sub(r'\(?(End|Finish) time (is a guess|not given[^.)]*)\.?\)?', '', d, flags=re.I).strip()
    links = re.findall(r'https?://\S+', d)
    if links:
        out['link'] = links[-1].rstrip('.,)')
        d = d.replace(links[-1], '').strip()
    parts = [p.strip() for p in re.split(r'(?<=\.)\s+', d) if p.strip()]
    def costof(p):
        pl = p.lower().rstrip('.')
        for k, v in COSTS:
            if pl.startswith(k) and len(pl) < 45:
                return (price_band(p) or 'Paid') if k == '£' else v
        return None
    if parts and costof(parts[0]) is None and len(parts) > 1 and costof(parts[1]):
        out['org'] = parts.pop(0).rstrip('.')
    if parts and costof(parts[0]):
        out['cost'] = costof(parts.pop(0))
    if parts and parts[0].lower().rstrip('.') in ('drop in', 'book first', 'booking required'):
        b = parts.pop(0).lower().rstrip('.'); out['booking'] = 'Drop in' if b == 'drop in' else 'Book first'
    # drop leftover sentences that only repeat the price or booking ("Free. Free.")
    parts = [p for p in parts if p.lower().rstrip('.') not in ('free', 'drop in', 'book first', 'price not stated')]
    info = ' '.join(parts).strip()
    if 'cost' not in out:
        il = info.lower()
        out['cost'] = ('Pay what you can' if 'donation' in il or 'pay what' in il or 'pay as you feel' in il
                       else price_band(info) or ('Free' if re.search(r'\bfree\b', il) else 'Price not stated'))
    # Booking (drop in / book first) is not shown: we usually don't know it for sure (31 Oct 2026).
    out.pop('booking', None)
    if info: out['info'] = info
    return out

def series_to_app(insts, window_end):
    insts = sorted(insts, key=lambda c: when(c['start'])[0])
    c0 = insts[0]
    s0, s_allday = when(c0['start']); e0, e_allday = when(c0['end'])
    d0, t0 = local(s0, s_allday)
    de, te = local(e0, e_allday)
    e = {'title': c0['summary'].strip(), 'venue': (c0.get('location') or '').strip() or 'See details',
         'area': area_for(c0.get('location')), 'category': cat_for(c0['summary'], c0.get('description')), 'date': d0.isoformat()}
    if t0:
        e['start'] = t0
        if te and de == d0: e['end'] = te
    elif (de - d0).days > 1:
        e['endDate'] = (de - dt.timedelta(1)).isoformat()
    e.update(parse_desc(c0.get('description')))
    e['gid'] = c0.get('recurringEventId') or c0['id']
    if 'recurringEventId' in c0 and len(insts) > 1:
        ds = sorted({local(*when(c['start']))[0] for c in insts})
        days = sorted({WD[d.weekday()] for d in ds}, key=WD.index)
        per_day = collections.defaultdict(list)
        for d in ds: per_day[WD[d.weekday()]].append(d)
        day_gaps = collections.Counter((b - a).days for v in per_day.values() for a, b in zip(v, v[1:]))
        if day_gaps and min(day_gaps) == 7 and all(g % 7 == 0 for g in day_gaps):
            r = {'freq': 'weekly', 'byday': days}
        elif day_gaps and min(day_gaps) == 14 and all(g % 14 == 0 for g in day_gaps):
            r = {'freq': 'weekly', 'byday': days, 'interval': 2}
        else:
            pos = set()
            for d in ds:
                n = (d.day - 1) // 7 + 1; last = (d + dt.timedelta(7)).month != d.month
                pos.add(-1 if (last and n >= 4 and not any(((x.day - 1) // 7 + 1) == n and (x + dt.timedelta(7)).month == x.month for x in ds)) else n)
            r = {'freq': 'monthly', 'byday': days, 'pos': sorted(pos, key=lambda p: (p < 0, p))}
        if ds[-1] < window_end - dt.timedelta(days=35 if r['freq'] == 'monthly' else 14):
            r['until'] = ds[-1].isoformat()
        e['rule'] = r
    return e


# ---------------- duplicates and rule checks ----------------
def _norm_title(t):
    t = re.sub(r'\s*[–—-]\s.*$', '', t or '').lower()   # drop "– Venue" suffix
    t = re.sub(r'\(.*?\)', '', t)
    return re.sub(r'[^a-z0-9]', '', t)

def _place(v):
    m = re.search(r'\b([A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2})\b', v or '')
    return m.group(1).replace(' ', '') if m else re.sub(r'[^a-z0-9]', '', (v or '').lower())[:12]

def _slot(e):
    r = e.get('rule')
    return (tuple(r.get('byday', [])), r.get('freq'), tuple(r.get('pos', [])), r.get('interval', 1)) if r else e['date']

def find_duplicates(events):
    """Groups of events that look like the same thing listed twice: same day/pattern, same start time,
    same postcode (or venue name) and a matching or near-matching title. Returns [[keep, drop, ...], ...]."""
    import difflib
    by = collections.defaultdict(list)
    for e in events: by[(_slot(e), e.get('start'), _place(e.get('venue')))].append(e)
    groups = []
    for L in by.values():
        if len(L) < 2: continue
        used = set()
        for i, a in enumerate(L):
            if i in used: continue
            g = [a]
            for j in range(i + 1, len(L)):
                if j in used: continue
                ta, tb = _norm_title(a['title']), _norm_title(L[j]['title'])
                if ta == tb or difflib.SequenceMatcher(None, ta, tb).ratio() > 0.8 or (ta and tb and (ta in tb or tb in ta)):
                    g.append(L[j]); used.add(j)
            if len(g) > 1:
                # keep the fullest listing (link + longest details)
                g.sort(key=lambda e: (bool(e.get('link')), e.get('cost') != 'Price not stated', len(e.get('info') or '')), reverse=True)
                groups.append(g)
    return groups

def rule_flags(events):
    return [e['title'] for e in events if re.search(RULE_CHECK, ' '.join([e['title'], e.get('org') or '', e.get('info') or '']), re.I)]


# ---------------- reading the calendar copy and the page ----------------
def load_pages(d):
    import glob, os
    seen = {}
    for f in sorted(glob.glob(os.path.join(d, '*.json'))):
        for e in json.load(open(f)).get('events', []):
            if e.get('status') != 'cancelled': seen[e['id']] = e
    return list(seen.values())

def page_parts(html):
    a = html.find('<script type="application/json" id="events-data">'); a = html.find('>', a) + 1; b = html.find('</script>', a)
    return a, b

def ensure_areas(html):
    """Make sure the app's AREAS list holds every area name, in AREA_ORDER."""
    m = re.search(r'var AREAS=\[[^\]]*\];', html)
    if not m: return html
    return html[:m.start()] + 'var AREAS=' + json.dumps(AREA_ORDER, ensure_ascii=False, separators=(',', ':')) + ';' + html[m.end():]

def cmd_build(pages, app_path, today, window_end, out):
    today = dt.date.fromisoformat(today); window_end = dt.date.fromisoformat(window_end)
    ev = load_pages(pages)
    ser = collections.defaultdict(list)
    for c in ev: ser[c.get('recurringEventId') or c['id']].append(c)
    html = open(app_path).read()
    if html.lstrip().lower().startswith('<!doctype'): html = html[html.find('<body>') + 6: html.rfind('</body>')]
    a, b = page_parts(html)
    old = {e.get('gid'): e for e in json.loads(html[a:b]) if e.get('gid')}
    out_ev, added, updated = [], [], 0
    for gid, insts in ser.items():
        fresh = series_to_app(insts, window_end)
        if gid in old:
            prev = old[gid]
            fresh['id'] = prev['id']; fresh['category'] = prev['category']
            # keep the area already in the app (it may have been set by hand), except where it was
            # 'Other / check venue' or the postcode district is one split between areas (e.g. M16)
            if prev.get('area') and prev['area'] != OTHER and _district(fresh['venue']) not in SPLIT_DISTRICTS:
                fresh['area'] = prev['area']
            for k in ('link', 'org', 'note', 'info'):
                if not fresh.get(k) and prev.get(k): fresh[k] = prev[k]
            if prev.get('date', '9') < fresh['date'] and 'rule' in fresh: fresh['date'] = prev['date']
            if fresh != prev: updated += 1
        else:
            fresh['id'] = 'g' + __import__('hashlib').md5(gid.encode()).hexdigest()[:8]
            added.append(fresh)
        out_ev.append(fresh)
    # leave obvious duplicates out of the app, and report them so the calendar can be tidied
    dups = find_duplicates(out_ev)
    drop = {id(e) for g in dups for e in g[1:]}
    out_ev = [e for e in out_ev if id(e) not in drop]
    removed = [e for g, e in old.items() if g not in ser]
    js = json.dumps(out_ev, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    new_html = ensure_areas(html[:a] + js + html[b:])
    assert new_html.count('id="app-js"') == html.count('id="app-js"')
    a2, b2 = page_parts(new_html); json.loads(new_html[a2:b2])
    open(out, 'w').write(new_html)
    print(json.dumps({'total': len(out_ev), 'added': [e['title'] for e in added], 'removed': [e['title'] for e in removed],
                      'updated': updated,
                      'check_area': [e['title'] for e in out_ev if e['area'] == OTHER],
                      'duplicates_left_out': [{'kept': g[0]['title'], 'kept_gid': g[0]['gid'], 'left_out_gids': [e['gid'] for e in g[1:]]} for g in dups],
                      'check_rules': rule_flags(out_ev),
                      'no_postcode': [e['title'] + ' | ' + e['venue'] for e in out_ev if not POSTCODE.search(e.get('venue') or '')]},
                     ensure_ascii=False, indent=1))
