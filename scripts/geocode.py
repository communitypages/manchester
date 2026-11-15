"""Adds each listing's exact location ("ll": [latitude, longitude]) from its full postcode, so the site can show
straight-line distances from the user's postcode. No AI and no outside service: the locations come from the
files in /pc/ (one per postcode district, e.g. pc/M16.json), which the website also uses to look up the
user's own postcode in their browser.

The /pc/ files were made from the free UK postcode list (Office for National Statistics / Ordnance Survey
data, Open Government Licence; copy at github.com/dwyl/uk-postcodes-latitude-longitude-complete-csv).
A postcode that isn't in them (e.g. a brand new one) can be added by hand: open the district's file and add
"INWARD": [latitude, longitude], e.g. "0EP": [53.45157, -2.27614] in pc/M16.json.
Listings whose postcode isn't found still get a rough distance from the centre of the postcode district.
"""
import json, os, re

PC = re.compile(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?)\s?(\d[A-Z]{2})\b')


def add_locations(events, site_folder):
    cache, found = {}, 0
    for ev in events:
        ev.pop('ll', None)
        m = PC.findall((ev.get('venue') or '').upper())
        if not m:
            continue
        out, inw = m[-1]
        if out not in cache:
            f = os.path.join(site_folder, 'pc', out + '.json')
            cache[out] = json.load(open(f)) if os.path.exists(f) else {}
        ll = cache[out].get(inw)
        if ll:
            ev['ll'] = ll
            found += 1
    return found
