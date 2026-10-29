"""Step 2 of the daily update: rebuilds index.html (and sitemap.xml, llms.txt) from the calendar copy.
Usage: python3 scripts/build_site.py --pages pages/ --today 2026-10-27 --window-end 2027-03-27
Stops without changing anything if the calendar looks wrong (e.g. the feed came back nearly empty).
"""
import argparse, contextlib, io, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import events as mcr_sync, search_info as seo_head
import datetime as dt

MAX_REMOVED_SHARE = 0.15   # refuse if more than 15% of listings would disappear in one go
MIN_EVENTS = 100           # refuse if the calendar gives fewer listings than this

p = argparse.ArgumentParser()
p.add_argument('--pages', required=True); p.add_argument('--today', required=True); p.add_argument('--window-end', required=True)
p.add_argument('--page', default='index.html'); p.add_argument('--force', action='store_true')
a = p.parse_args()

html = open(a.page).read()
b0 = html.find('<body>') + len('<body>'); b1 = html.rfind('</body>')
head, tail = html[:b0], html[b1:]
before = len(json.loads(html[mcr_sync.page_parts(html)[0]:mcr_sync.page_parts(html)[1]]))

tmp = tempfile.mktemp(suffix='.html')
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    mcr_sync.cmd_build(a.pages, a.page, a.today, a.window_end, tmp)
report = json.loads(buf.getvalue())

problems = []
if report['total'] < MIN_EVENTS:
    problems.append(f"only {report['total']} listings from the calendar")
if before and len(report['removed']) > before * MAX_REMOVED_SHARE:
    problems.append(f"{len(report['removed'])} of {before} listings would be removed")
if problems and not a.force:
    print('NOT PUBLISHED: ' + '; '.join(problems))
    print('If this is expected, run the workflow by hand with "force" ticked.')
    sys.exit(1)

new, items = seo_head.apply(head + open(tmp).read() + tail, dt.date.fromisoformat(a.today))
open(a.page, 'w').write(new)
d = os.path.dirname(os.path.abspath(a.page))
open(os.path.join(d, 'sitemap.xml'), 'w').write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f'<url><loc>{seo_head.SITE}</loc><lastmod>{a.today}</lastmod><changefreq>weekly</changefreq></url>\n</urlset>\n')
open(os.path.join(d, 'llms.txt'), 'w').write(
    seo_head.LLMS.format(site=seo_head.SITE, n=len(items), email=seo_head.EMAIL, date=a.today))

# short report for the GitHub run page
out = os.environ.get('GITHUB_STEP_SUMMARY')
lines = [f"## Site rebuilt {a.today}", f"- Listings: {report['total']} ({len(items)} showing on the site)",
         f"- Added: {len(report['added'])}", f"- Removed (ended or deleted from calendar): {len(report['removed'])}",
         f"- Changed: {report['updated']}"]
for k, label in (('added', 'Added'), ('removed', 'Removed'), ('check_area', 'Area to check'), ('check_rules', 'Check against listing rules')):
    if report[k]:
        lines.append(f"\n### {label}\n" + '\n'.join('- ' + t for t in report[k][:60]))
text = '\n'.join(lines)
print(text)
if out:
    open(out, 'a').write(text + '\n')
