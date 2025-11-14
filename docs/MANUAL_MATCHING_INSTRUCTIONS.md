# Manual LiveHeats Event Matching Instructions

## Overview
You need to fill in LiveHeats event and division IDs for 17 PWA events (34 divisions total).

The template CSV has been created at: `data/reports/liveheats_manual_matching_template.csv`

## How to Find LiveHeats IDs

### Method 1: Check PWA Website (RECOMMENDED)

Many PWA event pages have LiveHeats widgets embedded. You can extract the IDs from the widget URLs.

**Steps:**
1. Open the PWA event URL (in the `pwa_event_url` column)
2. Look for a LiveHeats widget/iframe on the page
3. Right-click the widget and "Inspect Element"
4. Look for URLs like: `https://liveheats.com/events/[EVENT_ID]/divisions/[DIVISION_ID]`
5. Copy the event ID and division ID

**Example from existing matches:**
- PWA: 2025 Chile World Cup → LiveHeats Event ID: `321865`
  - Men's division ID: `584952`
  - Women's division ID: `584951`

### Method 2: Check LiveHeats Website Directly

1. Go to https://liveheats.com
2. Navigate to the year (2023, 2024, or 2025)
3. Find events that match by location (Chile, Fiji, Peru, etc.)
4. Click on the event
5. The URL will show: `https://liveheats.com/events/[EVENT_ID]`
6. Click on a division to get: `https://liveheats.com/events/[EVENT_ID]/divisions/[DIVISION_ID]`

## What to Fill In

For each row in the CSV, fill in these columns:

### Required Fields:
1. **liveheats_event_id**: The numeric event ID from LiveHeats
2. **liveheats_division_id**: The numeric division ID from LiveHeats
3. **matched**: Change from `False` to `True` once you've verified the match

### Optional but Helpful:
4. **liveheats_event_name**: The event name on LiveHeats (e.g., "FIJI.PRO: 5 STAR 2023 FIJI SURF PRO")
5. **liveheats_division_name**: The division name (e.g., "Men", "Women")
6. **notes**: Add any notes about the match

## Matching Tips

### Location Patterns
LiveHeats typically uses this format: **"LOCATION: X STAR Event Name"**

- **Chile** → "CHILE: 5 STAR ..."
- **Fiji** → "FIJI: 5 STAR ..."
- **Peru** → "PERU: 5 STAR ..."
- **Hawaii/Aloha** → "HAWAII: 5 STAR Aloha Classic ..."
- **Gran Canaria** → "GRAN CANARIA: X STAR ..."
- **Tenerife** → "TENERIFE: X STAR ..."
- **Germany/Sylt** → "GERMANY: X STAR Sylt ..."
- **Japan** → "JAPAN: X STAR Omaezaki ..."

### Division Matching
- PWA "Wave Men" → LiveHeats "Men"
- PWA "Wave Women" → LiveHeats "Women"

### Events Not on LiveHeats
If you can't find an event on LiveHeats:
- Leave `matched = False`
- Add a note: "Event not found on LiveHeats"
- We'll skip these during scraping

## Example of Completed Row

```csv
pwa_event_id,pwa_event_name,pwa_year,...,matched,liveheats_event_id,liveheats_division_id,...
349,"2023 Cloudbreak, Fiji World Cup *****",2023,...,True,321XXX,584XXX,...
```

## After Filling In

Once you've filled in the IDs:

1. **Save the CSV file**
2. **Run the LiveHeats heat scraper:**
   ```bash
   cd src/scrapers
   python scrape_liveheats_heat_data.py
   ```
   (You may need to update the script to use the new matching file path)

3. **Continue with merge and load steps**

## Quick Reference: Events to Match

### 2025 (5 events)
1. Gran Canaria Gloria Windsurf World Cup (374)
2. Margaret River Wave Classic (385)
3. SPiCARE Omaezaki Japan World Cup (386)
4. Puerto Rico World Cup (387)
5. MFC | Maui Pro-Am (388)

### 2024 (6 events)
1. SPICARE Omaezaki Japan World Cup (352)
2. Topocalma, Chile World Cup (354)
3. Gran Canaria GLORIA PWA Windsurfing Grand Slam (357)
4. Tenerife PWA World Cup (358)
5. Pacasmayo, Peru World Cup (360)
6. Aloha Classic (365)

### 2023 (6 events)
1. Gran Canaria PWA Windsurfing Grand Slam (338)
2. Omaezaki Japan World Cup (345)
3. Topocalma, Chile World Cup (346)
4. Pacasmayo, Peru World Cup (347)
5. MAUI STRONG Aloha Classic Grand Final (348)
6. Cloudbreak, Fiji World Cup (349) ← You mentioned this has LiveHeats widget!

## Start Here

The **Fiji 2023** event (349) is a good one to start with since you've already seen it has a LiveHeats widget on the PWA site!

1. Open the PWA page for Fiji 2023
2. Inspect the LiveHeats widget
3. Extract the event ID and division IDs
4. Fill in the template CSV

Good luck! Let me know if you need help with any specific event.
