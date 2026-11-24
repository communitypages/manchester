# Community Pages

The website for [communitypages.org.uk](https://communitypages.org.uk): free, donation and £5-and-under community activities across Greater Manchester, for anyone looking for something to do and people to meet.

Run by Louise Fletcher. Contact: hello@communitypages.org.uk

## How the site updates

Every day at 5pm (UK winter time) GitHub rebuilds the site from the Community Pages Google Calendar. No AI is involved. See [scripts/README.md](scripts/README.md) for the details.

To add or change an activity, edit the Google Calendar, not the files here. The home page, area, activity, Christmas, 50+ and Kids pages are rebuilt automatically, so changes made to them by hand will be lost.

## What's here

| Folder or file | What it is |
|---|---|
| index.html | Home page (search). Its design and menu are kept; the listings are rebuilt daily. |
| events.json | All current listings, rebuilt daily |
| area/, activity/, christmas/, 50-plus/, kids/ | Built automatically from the home page |
| about/, add/, how-to-use/, link-workers/, map/, support/, privacy/, terms/ | Pages edited by hand |
| embed/, for-partners/ | Partner list for licensed websites (for-partners is hidden) |
| pc/ | Postcode data used for distances |
| scripts/ | The code that rebuilds the site |
| .github/workflows/ | The daily update |
