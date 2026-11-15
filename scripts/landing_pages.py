"""Builds one page per borough (/area/stockport/) and one per type of activity (/activity/coffee-chat/).
These give Google and AI search tools a page to match searches like "free things to do in Stockport"
or "coffee mornings Greater Manchester". Rebuilt every morning by build_site.py – don't edit the pages by hand.
"""
import os, re, json, html as H, datetime as dt
from search_info import SITE, EMAIL, COST_TEXT, DAYS, DAYNAME, when_text, clip, safe_link

# Borough -> the areas the site uses for it
BOROUGHS = {
    'Manchester': ['City centre & Ardwick', 'Hulme & Moss Side', 'Chorlton & Whalley Range', 'Fallowfield, Rusholme & Levenshulme',
                   'Gorton, Longsight & Openshaw', 'Didsbury & Withington', 'Wythenshawe', 'North Manchester'],
    'Salford': ['Salford'],
    'Trafford': ['Stretford & Old Trafford', 'Urmston & Flixton', 'Sale & Timperley', 'Altrincham & Hale', 'Partington'],
    'Stockport': ['Stockport & Marple'],
    'Tameside': ['Tameside'],
    'Oldham': ['Oldham'],
    'Rochdale': ['Rochdale'],
    'Bury': ['Bury'],
    'Bolton': ['Bolton'],
    'Wigan': ['Wigan'],
}
# Category in the calendar -> (web address, page heading, words people search for)
ACTIVITIES = {
    'Coffee & chat': ('coffee-chat', 'Coffee mornings and chatty cafés', 'coffee mornings, chatty cafés and social drop-ins'),
    'Wellbeing & support': ('wellbeing-support', 'Wellbeing and support groups', 'wellbeing groups, peer support and social groups'),
    'Family & kids': ('family-kids', 'Family, baby and toddler activities', 'stay and play, baby and toddler groups, storytimes and family activities'),
    'Learning & skills': ('learning-skills', 'ESOL, job clubs and learning', 'ESOL and English classes, job clubs, digital help and advice sessions'),
    'Active & sport': ('active-sport', 'Exercise, walks and sport', 'walking groups, chair exercise, yoga, tai chi, dance and sport'),
    'Outdoors & nature': ('outdoors-nature', 'Gardening and nature', 'community gardening, allotments, nature walks and park activities'),
    'Arts, crafts & writing': ('arts-crafts', 'Arts, crafts and writing groups', 'craft groups, knit and natter, art classes, book clubs and writing groups'),
    'Music & singing': ('music-singing', 'Choirs, singing and music', 'community choirs, singing groups and music sessions'),
    'Food & markets': ('food-markets', 'Lunch clubs, community meals and food', 'lunch clubs, community meals, food banks and pantries'),
    'Film & talks': ('film-talks', 'Free films and talks', 'community cinema, talks and lectures'),
    'Community': ('community', 'Community groups and events', 'community groups, residents\u2019 meetings and local events'),
}
GM = 'Greater Manchester'
# Christmas page (/christmas/): events whose title or details use one of these words, from now until 6 January
XMAS = re.compile(r'christmas|xmas|festive|santa|\bcarols\b|\bcarol (singing|service|concert)|grotto|panto(mime)?\b|mince pies?|'
                  r'wreath|yule|winter wonderland|nativity|reindeer|lights? switch[- ]on', re.I)


# 55+ page (/55-plus/): groups for over-50s, 55+, 65+ etc., plus Age UK and Good Neighbours groups
OLDER = re.compile(r'\b(50|55|60|65|70)\s?\+|\bover[- ]?(45|50|55|60|65|70)s?\b|\b(45|50|55|60|65)\s?(and|&) over\b|'
                   r'\bolder (people|person|adults?|men|women|residents|lgbt\w*)\b|\bpensioners?\b|\bretire(d|es|ment)\b|'
                   r'\bsenior citizens?\b|\bsilver\b|\blater life\b|\bageing\b|\bage friendly\b|\bdementia\b|\bmemory caf', re.I)
OLDER_ORGS = re.compile(r'\bage uk\b|good neighbours|pensioners', re.I)


def is_older(ev):
    return bool(OLDER.search(ev['title']) or OLDER.search(ev.get('info') or '') or OLDER_ORGS.search(ev.get('org') or '')
                or OLDER_ORGS.search(ev['title']))


def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


STYLE = '''body{margin:0;background:#F3F5EF;color:#15302B;font:17px/1.6 "Atkinson Hyperlegible","Segoe UI",system-ui,-apple-system,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:28px 16px 60px}a{color:#1C6B61}
h1{font:800 clamp(28px,5.5vw,40px)/1.1 "Bricolage Grotesque","Segoe UI",system-ui,sans-serif;margin:12px 0 14px}
h2{font:800 22px/1.2 "Bricolage Grotesque","Segoe UI",system-ui,sans-serif;margin:32px 0 8px}
h3{font-size:18px;margin:22px 0 6px}ul.ev{list-style:none;padding:0;margin:0}
ul.ev li{background:#fff;border:1px solid #D6DED5;border-radius:12px;padding:12px 14px;margin:8px 0}
ul.ev .t{font-weight:700}ul.ev .m{font-size:15px;color:#3D5650}ul.ev .i{font-size:15px;margin-top:4px}
.btn{display:inline-block;background:#1C6B61;color:#fff;font-weight:700;text-decoration:none;border-radius:999px;padding:12px 22px;margin:4px 0}
.lead{font-size:18px}.links{font-size:15px;line-height:1.9}
footer{border-top:1px solid #D6DED5;margin-top:40px;padding-top:16px;font-size:15px;color:#56706A}
@media print{.topnav,.btn,footer,.links{display:none!important}ul.ev li{break-inside:avoid}}'''


def topnav(html_of_index_page):
    """Reuse the site's top menu from the About page so every page matches."""
    m = re.search(r'<!--topnav-start-->.*?<!--topnav-end-->', html_of_index_page, re.S)
    return re.sub(r' aria-current="page"', '', m.group(0)) if m else ''


def browse_links(current=None):
    e = H.escape
    a = ' · '.join(('<strong>' + e(b) + '</strong>') if current == f'/area/{slug(b)}/' else f'<a href="/area/{slug(b)}/">{e(b)}</a>' for b in BOROUGHS)
    c = ' · '.join(('<strong>' + e(v[1]) + '</strong>') if current == f'/activity/{v[0]}/' else f'<a href="/activity/{v[0]}/">{e(v[1])}</a>'
                   for v in ACTIVITIES.values())
    return f'<nav class="links" aria-label="Browse"><h2>Browse by area</h2><p>{a}</p><h2>Browse by activity</h2><p>{c}</p></nav>'


def day_key(ev):
    by = (ev.get('rule') or {}).get('byday') or ['MO']
    if len(by) == 7: return -1
    return min(DAYS.index(d) for d in by)


def item(ev, nd, show_area):
    e = H.escape
    meta = [when_text(ev, nd), ev.get('venue', '')]
    if show_area and ev.get('area'): meta.append(ev['area'])
    meta.append(COST_TEXT.get(ev.get('cost'), ev.get('cost') or 'Price not stated'))
    s = f'<li><div class="t">{e(ev["title"])}</div><div class="m">{" · ".join(e(x) for x in meta if x)}'
    if ev.get('org'): s += ' · Run by ' + e(ev['org'])
    s += '</div>'
    if ev.get('info'): s += f'<div class="i">{e(clip(ev["info"], 220))}</div>'
    if safe_link(ev.get('link')): s += f' <a href="{e(ev["link"])}" rel="nofollow noopener">More info</a>'
    return s + '</li>'


def listing(items, show_area):
    regular = [x for x in items if x[0].get('rule')]
    oneoff = sorted([x for x in items if not x[0].get('rule')], key=lambda x: (x[1], x[0].get('start', '')))
    h = []
    if regular:
        h.append('<h2>Regular weekly and monthly groups</h2>')
        for i, label in [(-1, 'Every day')] + [(i, DAYNAME[d] + 's') for i, d in enumerate(DAYS)]:
            day = sorted([x for x in regular if day_key(x[0]) == i], key=lambda x: (x[0].get('start', ''), x[0]['title']))
            if day:
                h.append(f'<h3>{label}</h3><ul class="ev">' + ''.join(item(*x, show_area) for x in day) + '</ul>')
    if oneoff:
        h.append('<h2>One-off events coming up</h2><ul class="ev">' + ''.join(item(*x, show_area) for x in oneoff) + '</ul>')
    if not items:
        h.append('<p>Nothing is listed here at the moment. Know a free or low-cost group? '
                 f'<a href="/add/">Tell us about it</a>.</p>')
    return '\n'.join(h)


def page(path, title, desc, h1, intro, body, nav, crumb, today):
    e = H.escape
    url = SITE + path.lstrip('/')
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': title, 'url': url, 'description': desc, 'inLanguage': 'en-GB',
         'dateModified': today.isoformat(), 'isPartOf': {'@type': 'WebSite', 'name': 'Community Pages', 'url': SITE}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Community Pages', 'item': SITE},
            {'@type': 'ListItem', 'position': 2, 'name': crumb, 'item': url}]}]}
    return f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#1C6B61">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Community Pages">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="en_GB">
<meta property="og:image" content="https://communitypages.org.uk/share.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Community Pages: find activities near you. Local groups across Greater Manchester.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace('<', '\\u003c')}</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Bricolage+Grotesque:opsz,wght@12..96,800&display=swap" onload="this.onload=null;this.rel=\'stylesheet\'"><noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Bricolage+Grotesque:opsz,wght@12..96,800&display=swap"></noscript>
<style>{STYLE}</style>
</head>
<body>
{nav}
<main class="wrap">
<h1>{e(h1)}</h1>
<p class="lead">{intro}</p>
<p>Updated {today.strftime('%-d %B %Y')}. Things change, so please check with the organiser before you go.</p>
<p><a class="btn" href="/">Search all activities by date and postcode</a></p>
{body}
{browse_links(path)}
<footer><a href="/">Find activities</a> · <a href="/about/">About</a> · <a href="/link-workers/">For link workers</a> · <a href="/add/">Add an event</a> · <a href="/privacy/">Privacy</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></footer>
</main>
</body>
</html>
'''


def app_page(folder, path, title, desc, h1, intro, body, only, today):
    """A copy of the home page (same search box, date, postcode and Search button) that only shows some activities.
    `only` = regular expressions the page uses to pick its activities: 'text' (title or details) and 'org' (organiser)."""
    e = H.escape
    s = open(os.path.join(folder, 'index.html')).read()
    url = SITE + path.lstrip('/')
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', 'name': title, 'url': url, 'description': desc, 'inLanguage': 'en-GB',
         'dateModified': today.isoformat(), 'isPartOf': {'@type': 'WebSite', 'name': 'Community Pages', 'url': SITE}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Community Pages', 'item': SITE},
            {'@type': 'ListItem', 'position': 2, 'name': h1, 'item': url}]}]}
    a, b = s.index('<!--seo-start-->') + len('<!--seo-start-->'), s.index('<!--seo-end-->')
    old = s[a:b]
    keep = old[:old.index('<title>')]          # the small script and style that hide the plain list once the page loads
    csp = re.search(r'<meta http-equiv="Content-Security-Policy"[^>]*>', old)
    head = keep + f'''<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
{csp.group(0) if csp else ''}
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="theme-color" content="#1C6B61">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Community Pages">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="en_GB">
<meta property="og:image" content="https://communitypages.org.uk/share.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Community Pages: find activities near you. Local groups across Greater Manchester.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace('<', '\\u003c')}</script>
'''
    s = s[:a] + head + s[b:]
    # plain list for search engines and for anyone without JavaScript
    a, b = s.index('<!--seo-list-start-->'), s.index('<!--seo-list-end-->')
    plain = (f'<!--seo-list-start--><p id="seo-loading">Loading…</p><div class="wrap" id="seo-list"><h1>{e(h1)}</h1><p>{intro}</p>'
             f'<p>Updated {today.strftime("%-d %B %Y")}. Please check with the organiser before you go.</p>{body}{browse_links(path)}</div>')
    s = s[:a] + plain + s[b:]
    # tell the search app which activities to show
    cfg = json.dumps({'text': only['text'], 'org': only.get('org'), 'h1': e(h1), 'intro': e(only['short'])}, ensure_ascii=False).replace('<', '\\u003c')
    s = s.replace('<script id="app-js">', f'<script>window.CP_ONLY={cfg};</script><script id="app-js">', 1)
    # menu: highlight this page instead of the home page
    s = s.replace('<a class="logo" href="/" aria-current="page">', '<a class="logo" href="/">', 1)
    s = s.replace(f'<a class="l" href="{path}">', f'<a class="l" href="{path}" aria-current="page">', 1)
    return s


def build(folder, items, today):
    """Writes the area and activity pages. Returns their paths (e.g. 'area/stockport/') for the sitemap."""
    nav = topnav(open(os.path.join(folder, 'about', 'index.html')).read())
    written = []

    def save(path, text):
        d = os.path.join(folder, path.strip('/'))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w').write(text)
        written.append(path.lstrip('/'))

    for borough, areas in BOROUGHS.items():
        mine = [x for x in items if x[0].get('area') in areas]
        n = len(mine)
        where = f'{borough}, {GM}' if borough != 'Manchester' else 'Manchester'
        title = f'Free things to do in {borough} – £5 and under | Community Pages'
        desc = (f'{n} free, donation and £5-or-less activities in {where}: coffee mornings, ESOL, walks, '
                f'stay and play, craft groups, lunch clubs and more. Checked by hand, updated daily.')
        parts = '' if len(areas) == 1 else ' Covers ' + ', '.join(areas) + '.'
        intro = (f'{n} free, donation-based and £5-or-less activities and groups in {H.escape(where)}.{H.escape(parts)} '
                 'Good for anyone looking for something to do nearby, and for social prescribing link workers.')
        path = f'/area/{slug(borough)}/'
        save(path, page(path, title, desc, f'Free and low-cost things to do in {borough}', intro,
                        listing(mine, show_area=len(areas) > 1), nav, borough, today))

    for cat, (s, heading, words) in ACTIVITIES.items():
        mine = sorted([x for x in items if x[0].get('category') == cat], key=lambda x: x[0].get('area', ''))
        n = len(mine)
        title = f'{heading} in {GM} | Community Pages'
        desc = f'{n} {words} across {GM}. All free, donation or £5 or less. Checked by hand, updated daily.'
        intro = f'{n} {H.escape(words)} across {GM}, all free, donation-based or £5 or less.'
        path = f'/activity/{s}/'
        save(path, page(path, title, desc, f'{heading} in {GM}', intro, listing(mine, show_area=True), nav, heading, today))
    # Christmas page
    end = dt.date(today.year + 1 if today.month >= 7 else today.year, 1, 6)
    mine = [x for x in items if x[1] <= end and (XMAS.search(x[0]['title']) or XMAS.search(x[0].get('info') or ''))]
    oneoff = sorted([x for x in mine if not x[0].get('rule')], key=lambda x: (x[1], x[0].get('start', ''), x[0]['title']))
    regular = sorted([x for x in mine if x[0].get('rule')], key=lambda x: (day_key(x[0]), x[0].get('start', ''), x[0]['title']))
    body = []
    last = None
    for ev, nd in oneoff:
        if nd != last:
            body.append(('</ul>' if last else '') + f'<h3>{nd.strftime("%A %-d %B")}</h3><ul class="ev">')
            last = nd
        body.append(item(ev, nd, True))
    if last: body.append('</ul>')
    if regular:
        body.append('<h2>Regular groups with a Christmas theme</h2><ul class="ev">' + ''.join(item(*x, True) for x in regular) + '</ul>')
    if not mine:
        body.append('<p>No Christmas activities are listed at the moment. Running a free or low-cost Christmas event? '
                    '<a href="/add/">Tell us about it</a>.</p>')
    n = len(mine)
    path = '/christmas/'
    save(path, app_page(folder, path, f'Free Christmas activities in {GM} – £5 and under | Community Pages',
                        f'{n} free, donation and £5-or-less Christmas events across {GM}: Santa visits, carols, Christmas meals, '
                        'wreath making and festive crafts. Search by date and postcode. Updated daily.',
                        f'Christmas activities in {GM}',
                        f'{n} free, donation-based and £5-or-less Christmas events across {GM}, from now until 6 January: '
                        'Santa visits, carols, Christmas meals, wreath making and festive crafts.',
                        '\n'.join(body), {'text': XMAS.pattern, 'short': 'Free and low-cost Christmas activities across Greater Manchester.'}, today))
    # 55+ page, grouped by borough
    mine = [x for x in items if is_older(x[0])]
    where = {a: b for b, areas in BOROUGHS.items() for a in areas}
    body, jump = [], []
    for borough in BOROUGHS:
        here = [x for x in mine if where.get(x[0].get('area')) == borough]
        if not here: continue
        regular = sorted([x for x in here if x[0].get('rule')], key=lambda x: (day_key(x[0]), x[0].get('start', ''), x[0]['title']))
        oneoff = sorted([x for x in here if not x[0].get('rule')], key=lambda x: (x[1], x[0].get('start', ''), x[0]['title']))
        jump.append(f'<a href="#{slug(borough)}">{H.escape(borough)} ({len(here)})</a>')
        body.append(f'<h2 id="{slug(borough)}">{H.escape(borough)}</h2><ul class="ev">' + ''.join(item(*x, True) for x in regular + oneoff) + '</ul>')
    if jump:
        body.insert(0, '<p class="links"><strong>Jump to:</strong> ' + ' · '.join(jump) + '</p>')
    else:
        body.append('<p>Nothing is listed here at the moment. Know a free or low-cost group for people 55+? '
                    '<a href="/add/">Tell us about it</a>.</p>')
    n = len(mine)
    path = '/55-plus/'
    save(path, app_page(folder, path, f'55+ activities in {GM} – free and £5 and under | Community Pages',
                        f'{n} free, donation and £5-or-less activities for people aged 55+ across {GM}: lunch clubs, coffee mornings, '
                        'chair exercise, singing, digital help and more. Search by date and postcode. Updated daily.',
                        f'55+ activities in {GM}',
                        f'{n} free, donation-based and £5-or-less groups for people aged 55 and over across {GM}, including over-50s, 55+ and 65+ '
                        'groups, Age UK and Good Neighbours activities, and dementia-friendly sessions. The age shown in each title is the group\u2019s own.',
                        '\n'.join(body), {'text': OLDER.pattern, 'org': OLDER_ORGS.pattern,
                                           'short': 'Free and low-cost groups for people aged 55 and over across Greater Manchester.'}, today))
    return written
