"""Adds the information Google and AI search tools read to index.html.
Used by build_site.py – you don't run this file yourself. Safe to run more than once.

What it adds:
- <head>: title, description, social tags, site info (as before).
- Inside <div id="app">: a plain-HTML list of every event in the app (not 'Paid'),
  so search engines and AI tools that don't run JavaScript can read it.
  The app replaces this list as soon as it loads, so visitors don't see it twice.
- A schema.org Event block (JSON-LD) for each event, with the next date it happens
  and, for regular groups, how often it repeats.
"""
import re, sys, os, json, html as H, datetime as dt

SITE = 'https://communitypages.org.uk/'
TITLE = 'Community Pages – local wellbeing activities £5 and under in Greater Manchester'
DESC = ('Local wellbeing activities £5 and under across Greater Manchester – free, donation or low cost: '
        'coffee mornings, ESOL, job clubs, walks, stay and play, food banks and more. '
        'Search by area, date and postcode. Updated every day.')
EMAIL = 'hello@communitypages.org.uk'
HEAD = f'''<!--seo-start-->
<script>document.documentElement.className+=' js'</script>
<style>.js #seo-list{{display:none}}#seo-loading{{display:none}}.js #seo-loading{{display:block;max-width:1100px;margin:0 auto;padding:40px 16px;font:17px "Atkinson Hyperlegible","Segoe UI",system-ui,sans-serif;color:#56706A}}</style>
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<link rel="canonical" href="{SITE}">
<meta name="robots" content="index,follow">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="theme-color" content="#1C6B61">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Community Pages">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{SITE}">
<meta property="og:locale" content="en_GB">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[
{{"@type":"WebSite","name":"Community Pages","url":"{SITE}","inLanguage":"en-GB","description":"{DESC}"}},
{{"@type":"Organization","name":"Community Pages","url":"{SITE}","email":"{EMAIL}","description":"Free, volunteer-run listing of free, donation and £5-or-less community activities in Greater Manchester, for residents and social prescribing link workers.","areaServed":{{"@type":"AdministrativeArea","name":"Greater Manchester"}},"sameAs":["https://www.patreon.com/c/communitypages"]}}]}}</script>
<!--seo-end-->'''
NOSCRIPT = '''<!--seo-noscript--><noscript><h1>Community Pages</h1><p>Local wellbeing activities £5 and under – free, donation or low cost – across Greater Manchester: Manchester, Salford, Trafford, Stockport, Tameside, Oldham, Rochdale, Bury, Bolton and Wigan. Turn on JavaScript to search by date, area and postcode. Contact: hello@communitypages.org.uk</p></noscript>'''

DAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
DAYNAME = dict(zip(DAYS, ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']))
SCHEMA_DAY = {d: 'https://schema.org/' + DAYNAME[d] for d in DAYS}
ORD = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th', -1: 'last'}
COST_TEXT = {'Free': 'Free', 'Pay what you can': 'Donation / pay what you can', 'Low cost': '£5 or less',
             'Price not stated': 'Price not stated – check with the organiser'}


# ---------- dates (same rules as the app) ----------
def nth(d): return (d.day - 1) // 7 + 1
def is_last(d): return (d + dt.timedelta(7)).month != d.month

def occurs(ev, d):
    s = d.isoformat()
    r = ev.get('rule')
    if not r:
        return ev['date'] <= s <= (ev.get('endDate') or ev['date'])
    if s < ev['date'] or (r.get('until') and s > r['until']): return False
    if DAYS[d.weekday()] not in (r.get('byday') or []): return False
    if (r.get('interval') or 1) > 1:
        d0 = dt.date.fromisoformat(ev['date'])
        m0 = d0 - dt.timedelta(d0.weekday()); m1 = d - dt.timedelta(d.weekday())
        if ((m1 - m0).days // 7) % r['interval']: return False
    if r.get('freq') == 'monthly':
        return any(p == nth(d) or (p == -1 and is_last(d)) for p in (r.get('pos') or [1]))
    return True

def next_date(ev, today, days=120):
    for i in range(days):
        d = today + dt.timedelta(i)
        if occurs(ev, d): return d
    return None

def uk_offset(d):
    # last Sunday of March to last Sunday of October = BST
    def last_sun(y, m):
        x = dt.date(y, m + 1, 1) - dt.timedelta(1)
        return x - dt.timedelta((x.weekday() + 1) % 7)
    return '+01:00' if last_sun(d.year, 3) <= d < last_sun(d.year, 10) else '+00:00'


# ---------- text ----------
def has_time(ev):
    """False for all-day events, including old entries saved with a 00:00 start and no end."""
    return bool(ev.get('start')) and not (ev['start'] == '00:00' and not ev.get('end'))

def clip(text, n):
    """Shorten text to about n characters at a word boundary, with an ellipsis."""
    text = text or ''
    if len(text) <= n: return text
    cut = text[:n].rsplit(' ', 1)[0].rstrip(' ,;:–-(')
    return cut + '…'

def rule_text(r):
    days = ' and '.join(DAYNAME[x] for x in r.get('byday', []))
    if len(r.get('byday', [])) == 7: days = 'day'
    if r.get('freq') == 'monthly':
        return ' and '.join(ORD.get(p, str(p)) for p in r.get('pos', [1])) + ' ' + days + ' of the month'
    if (r.get('interval') or 1) == 2: return 'Every other ' + days
    return 'Every ' + days

def time_text(ev):
    if not has_time(ev): return 'all day'
    return ev['start'] + ('–' + ev['end'] if ev.get('end') else '')

def when_text(ev, nd):
    if ev.get('rule'):
        t = rule_text(ev['rule']) + ', ' + time_text(ev)
        if ev['rule'].get('until'): t += ' (until ' + dt.date.fromisoformat(ev['rule']['until']).strftime('%-d %b %Y') + ')'
        return t
    t = dt.date.fromisoformat(ev['date']).strftime('%a %-d %b %Y')
    if ev.get('endDate') and ev['endDate'] != ev['date']:
        t += ' to ' + dt.date.fromisoformat(ev['endDate']).strftime('%a %-d %b %Y')
    return t + ', ' + time_text(ev)


def safe_link(u):
    return u if isinstance(u, str) and re.match(r'^https?://[^\s"<>]+$', u) else ''


def live_events(events, today):
    out = []
    for ev in events:
        if ev.get('cost') == 'Paid': continue
        nd = next_date(ev, today)
        if nd: out.append((ev, nd))
    return out


def static_html(items, today):
    e = H.escape
    regular = sorted([x for x in items if x[0].get('rule')], key=lambda x: (x[0].get('area', ''), x[0]['title']))
    oneoff = sorted([x for x in items if not x[0].get('rule')], key=lambda x: (x[1], x[0].get('start', '')))
    def li(ev, nd):
        bits = [e(when_text(ev, nd)), e(ev.get('venue', ''))]
        if ev.get('area'): bits.append(e(ev['area']))
        bits.append(e(COST_TEXT.get(ev.get('cost'), ev.get('cost') or 'Price not stated')))
        if ev.get('booking'): bits.append(e(ev['booking']))
        s = '<li><strong>' + e(ev['title']) + '</strong> – ' + ' · '.join(bits)
        if ev.get('org'): s += ' · Run by ' + e(ev['org'])
        if ev.get('info'): s += '. ' + e(clip(ev['info'], 240))
        if safe_link(ev.get('link')): s += ' <a href="' + e(ev['link']) + '" rel="nofollow noopener">More info</a>'
        return s + '</li>'
    h = ['<!--seo-list-start--><p id="seo-loading">Loading activities…</p><div class="wrap" id="seo-list">',
         '<h1>Community Pages – local wellbeing activities £5 and under in Greater Manchester</h1>',
         '<p>Free, donation-based and £5-or-less community activities across Greater Manchester, checked by hand and updated every day. '
         f'List updated {today.strftime("%-d %B %Y")}. {len(items)} events and regular groups. '
         f'Please check with the organiser before you go. Contact: {EMAIL}</p>',
         '<h2>Dated events coming up</h2><ul>']
    h += [li(*x) for x in oneoff]
    h.append('</ul><h2>Regular weekly and monthly groups, by area</h2>')
    area = None
    for ev, nd in regular:
        if ev.get('area') != area:
            if area is not None: h.append('</ul>')
            area = ev.get('area'); h.append('<h3>' + e(area or 'Other') + '</h3><ul>')
        h.append(li(ev, nd))
    if area is not None: h.append('</ul>')
    h.append('</div><!--seo-list-end-->')
    return '\n'.join(h)


def event_ld(ev, nd):
    off = uk_offset(nd)
    start = ev.get('start') if has_time(ev) else None
    def stamp(day, t): return day.isoformat() + ('T' + t + ':00' + off if t else '')
    o = {'@type': 'Event', 'name': ev['title'],
         'startDate': stamp(nd, start),
         'eventStatus': 'https://schema.org/EventScheduled',
         'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
         'location': {'@type': 'Place', 'name': ev.get('venue', '').split(',')[0],
                      'address': {'@type': 'PostalAddress', 'streetAddress': ev.get('venue', ''),
                                  'addressRegion': 'Greater Manchester', 'addressCountry': 'GB'}},
         'url': safe_link(ev.get('link')) or SITE}
    if ev.get('end') and start: o['endDate'] = stamp(nd, ev['end'])
    elif ev.get('endDate'): o['endDate'] = ev['endDate']
    if ev.get('info'): o['description'] = clip(ev['info'], 300)
    if ev.get('org'): o['organizer'] = {'@type': 'Organization', 'name': ev['org']}
    c = ev.get('cost')
    if c == 'Free':
        o['isAccessibleForFree'] = True
        o['offers'] = {'@type': 'Offer', 'price': '0', 'priceCurrency': 'GBP', 'url': o['url']}
    elif c == 'Pay what you can':
        o['offers'] = {'@type': 'Offer', 'price': '0', 'priceCurrency': 'GBP', 'description': 'Donation / pay what you can', 'url': o['url']}
    elif c == 'Low cost':
        o['offers'] = {'@type': 'Offer', 'description': '£5 or less', 'priceCurrency': 'GBP', 'url': o['url']}
    r = ev.get('rule')
    if r:
        s = {'@type': 'Schedule', 'scheduleTimezone': 'Europe/London', 'startDate': ev['date'],
             'byDay': [SCHEMA_DAY[x] for x in r.get('byday', [])]}
        if r.get('freq') == 'monthly':
            s['repeatFrequency'] = 'P1M'; s['byMonthWeek'] = r.get('pos', [1])
        else:
            s['repeatFrequency'] = 'P%dW' % (r.get('interval') or 1)
        if start: s['startTime'] = start + ':00'
        if ev.get('end') and start: s['endTime'] = ev['end'] + ':00'
        if r.get('until'): s['endDate'] = r['until']
        o['eventSchedule'] = s
    return o


def apply(html, today=None):
    today = today or dt.date.today()
    html = re.sub(r'<!--seo-start-->.*?<!--seo-end-->\n?', '', html, flags=re.S)
    html = re.sub(r'<!--seo-noscript-->.*?</noscript>', '', html, flags=re.S)
    html = re.sub(r'<!--seo-list-start-->.*?<!--seo-list-end-->', '', html, flags=re.S)
    html = re.sub(r'<!--seo-events-start-->.*?<!--seo-events-end-->\n?', '', html, flags=re.S)
    html = re.sub(r'^<!doctype html><html[^>]*>', '<!doctype html><html lang="en-GB">', html, count=1, flags=re.I)
    html = html.replace('<meta charset=utf8>', '<meta charset="utf-8">', 1)
    # drop the stray <title> the export puts in <body> (only the first one; the one inside the app's JS stays)
    body = html.find('<body>')
    t = html.find('<title>', body)
    if body != -1 and t != -1 and t < html.find('<script', body):
        html = html[:t] + html[html.find('</title>', t) + 8:]

    a = html.find('id="events-data"'); a = html.find('>', a) + 1; b = html.find('</script>', a)
    items = live_events(json.loads(html[a:b]), today)
    ld = json.dumps({'@context': 'https://schema.org', '@graph': [event_ld(*x) for x in items]},
                    ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    events_block = '<!--seo-events-start--><script type="application/ld+json" id="events-ld">' + ld + '</script><!--seo-events-end-->\n'

    html = html.replace('</head>', HEAD + '</head>', 1)
    html = html.replace('<body>', '<body>' + NOSCRIPT, 1)
    app = html.find('<div id="app">')
    assert app != -1 and app < html.find('id="events-data"'), 'app container not found'
    app_end = app + len('<div id="app">')
    html = html[:app_end] + static_html(items, today) + html[app_end:]
    html = html.replace('<script type="application/json" id="events-data">', events_block + '<script type="application/json" id="events-data">', 1)
    assert html.count('<!--seo-start-->') == 1 and 'id="app-js"' in html and html.count('<!--seo-list-start-->') == 1
    return html, items


LLMS = '''# Community Pages

> Free, volunteer-run website listing community activities and events across Greater Manchester that are free, donation-based or cost £5 or less. Covers all ten boroughs: Manchester, Salford, Trafford, Stockport, Tameside, Oldham, Rochdale, Bury, Bolton and Wigan. Built for residents and for social prescribing link workers.

Typical activities: coffee mornings, chatty cafés, ESOL and English classes, job clubs, digital help, walking groups, chair exercise, stay and play, baby and toddler groups, lunch clubs, food banks, wellbeing and peer support groups, choirs, craft and knitting groups, gardening.

- {n} current listings, checked by hand and updated every day.
- Each listing gives the date or how often it runs, start and end time, venue with postcode, area, cost (free, donation, £5 or less, or price not stated) and whether to drop in or book first.
- Activities costing more than £5, political campaigns, religious worship and business promotion are not listed.
- People should check with the organiser before going.

## Pages

- [Find activities]({site}): searchable list by date, area and postcode, with a printable list.
- [All listings as plain text]({site}llms-full.txt): every current activity, one per line, grouped by area.
- [About]({site}about/): who runs the site and what is listed.
- [For link workers]({site}link-workers/): how to find and print local activities for someone.
- [Add your event]({site}add/): how groups can get listed for free.
- [Support us]({site}support/)

## Contact

- Email: {email}

Last updated: {date}
'''

PAGES = ['', 'about/', 'link-workers/', 'add/', 'support/', 'privacy/']


def llms_full(items, today):
    """Every current listing as plain text, for AI tools."""
    def line(ev, nd):
        bits = [when_text(ev, nd), ev.get('venue', '')]
        bits.append(COST_TEXT.get(ev.get('cost'), ev.get('cost') or 'Price not stated'))
        if ev.get('booking'): bits.append(ev['booking'])
        t = '- ' + ev['title'] + ': ' + '; '.join(b for b in bits if b)
        if ev.get('org'): t += '. Run by ' + ev['org']
        if ev.get('info'): t += '. ' + clip(ev['info'], 200)
        if safe_link(ev.get('link')): t += ' ' + ev['link']
        return t
    regular = sorted([x for x in items if x[0].get('rule')], key=lambda x: (x[0].get('area', ''), x[0]['title']))
    oneoff = sorted([x for x in items if not x[0].get('rule')], key=lambda x: (x[1], x[0].get('start', '')))
    out = ['# Community Pages – all current listings', '',
           f'> Free, donation and £5-or-less activities across Greater Manchester. {len(items)} listings, updated {today.strftime("%-d %B %Y")}. '
           f'Source: {SITE} – please check with the organiser before going.', '', '## Regular groups, by area']
    area = None
    for ev, nd in regular:
        if ev.get('area') != area:
            area = ev.get('area'); out += ['', '### ' + (area or 'Other')]
        out.append(line(ev, nd))
    out += ['', '## Dated events coming up']
    out += [line(ev, nd) for ev, nd in oneoff]
    return '\n'.join(out) + '\n'


def write_extras(folder, items, today):
    """sitemap.xml, llms.txt and llms-full.txt."""
    urls = ''.join(f'<url><loc>{SITE}{p}</loc>' + (f'<lastmod>{today.isoformat()}</lastmod><changefreq>daily</changefreq>' if p == '' else '') + '</url>\n'
                   for p in PAGES)
    open(os.path.join(folder, 'sitemap.xml'), 'w').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n')
    open(os.path.join(folder, 'llms.txt'), 'w').write(LLMS.format(site=SITE, n=len(items), email=EMAIL, date=today.isoformat()))
    open(os.path.join(folder, 'llms-full.txt'), 'w').write(llms_full(items, today))

