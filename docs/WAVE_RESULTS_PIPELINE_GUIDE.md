# Wave Results Pipeline Guide

## Overview

This guide explains the complete pipeline for collecting, scraping, and merging wave event results from both PWA and Live Heats sources.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
├──────────────────────────┬──────────────────────────────────┤
│  PWA (2016-2025)         │  Live Heats (2023+)              │
│  - 55 wave events        │  - Recent events with GraphQL    │
│  - Full athlete details  │  - Some overlap with PWA         │
└──────────────────────────┴──────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  SCRAPING LAYER                              │
├──────────────────────────┬──────────────────────────────────┤
│  pwa_results_scraper.py  │  scrape_liveheats_matched_       │
│  - HTML scraping         │  results.py                       │
│  - Athlete names         │  - GraphQL API                   │
│  - Sail numbers          │  - Athlete IDs only              │
│  - PWA athlete IDs       │  - Based on matching report      │
└──────────────────────────┴──────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  RAW DATA LAYER                              │
├──────────────────────────┬──────────────────────────────────┤
│  pwa_wave_results_       │  liveheats_matched_results.csv   │
│  updated.csv             │  - 48 records (5 events)         │
│  - 1,880 records         │  - Missing athlete names         │
│  - Complete info         │  - Has athlete IDs               │
└──────────────────────────┴──────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              MERGE & DEDUPLICATION                           │
│              merge_wave_results.py                           │
│  - Combines both sources                                     │
│  - Removes duplicates (prioritizes PWA)                      │
│  - Standardizes format                                       │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED OUTPUT                                  │
│  data/processed/wave_results_merged.csv                      │
│  - Single source of truth                                    │
│  - All wave events 2016-2025                                 │
│  - Standardized format                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
src/scrapers/
├── pwa_results_scraper.py               # Scrape PWA results
├── match_pwa_to_liveheats.py            # Match PWA events to LH
├── scrape_liveheats_matched_results.py  # Scrape Live Heats results
├── merge_wave_results.py                # Merge both sources
└── run_complete_results_pipeline.py     # Orchestrator script

data/
├── raw/
│   ├── pwa/
│   │   ├── pwa_events_raw.csv                    # Event metadata
│   │   ├── pwa_wave_results_updated.csv          # PWA results (1,880 rows)
│   │   └── pwa_wave_divisions_raw.csv            # Division tracking
│   └── liveheats/
│       ├── liveheats_events_2023plus.csv         # LH events
│       └── liveheats_matched_results.csv         # LH results (48 rows)
├── reports/
│   └── pwa_liveheats_matching_report_v2.csv      # Matching report
└── processed/
    └── wave_results_merged.csv                   # FINAL MERGED OUTPUT
```

---

## Data Schema

### Unified Results Format

All results (PWA + Live Heats) follow this schema:

| Column          | Type   | Description                                    |
|-----------------|--------|------------------------------------------------|
| source          | string | 'PWA' or 'Live Heats'                          |
| scraped_at      | datetime | Timestamp of scrape                           |
| event_id        | int    | Event ID (from source system)                  |
| year            | int    | Event year                                     |
| event_name      | string | Full event name                                |
| division_label  | string | Division name (e.g., "Wave Men")               |
| division_code   | string | Division code/ID from source                   |
| sex             | string | "Men" or "Women"                               |
| place           | string | Final placement (can have ties: "5", "5", "7") |
| athlete_name    | string | Athlete full name                              |
| sail_number     | string | Sail number (e.g., "G-44")                     |
| athlete_id      | string | Athlete ID from source system                  |

---

## Scripts Reference

### 1. PWA Results Scraper

**File**: [src/scrapers/pwa_results_scraper.py](src/scrapers/pwa_results_scraper.py)

**Purpose**: Scrape final results for all PWA wave events (2016-2025)

**Input**:
- `data/raw/pwa/pwa_events_raw.csv` (event metadata)

**Output**:
- `data/raw/pwa/pwa_wave_results_updated.csv` (results)
- `data/raw/pwa/pwa_wave_divisions_raw.csv` (division info)

**Usage**:
```bash
cd src/scrapers
python pwa_results_scraper.py
```

**Features**:
- Scrapes HTML results tables from PWA website
- Extracts athlete names, sail numbers, PWA athlete IDs
- Handles multiple divisions per event (Men/Women)
- Includes retry logic and rate limiting

**Statistics** (as of Oct 2025):
- 55 wave events processed
- 1,880 athlete results extracted
- Complete athlete information

---

### 2. Event Matching Script

**File**: [src/scrapers/match_pwa_to_liveheats.py](src/scrapers/match_pwa_to_liveheats.py)

**Purpose**: Match PWA events to Live Heats events to identify overlap

**Input**:
- `data/raw/pwa/pwa_events_raw.csv`
- Live Heats GraphQL API

**Output**:
- `data/reports/pwa_liveheats_matching_report_v2.csv`
- `data/raw/liveheats/liveheats_events_2023plus.csv`

**Usage**:
```bash
cd src/scrapers
python match_pwa_to_liveheats.py
```

**Matching Logic**:
- Date overlap (±1 day): 60 points
- Location match: 30 points
- Star rating match: 10 points
- Threshold for match: 80/100

**Current Matches** (5 divisions across 4 events):
1. 2025 Chile World Cup (Men + Women)
2. 2025 Sylt Germany Grand Slam (Men)
3. 2025 Aloha Classic Maui (Men + Women)

---

### 3. Live Heats Results Scraper

**File**: [src/scrapers/scrape_liveheats_matched_results.py](src/scrapers/scrape_liveheats_matched_results.py)

**Purpose**: Scrape final results from Live Heats for matched events

**Input**:
- `data/reports/pwa_liveheats_matching_report_v2.csv`

**Output**:
- `data/raw/liveheats/liveheats_matched_results.csv`

**Usage**:
```bash
cd src/scrapers
python scrape_liveheats_matched_results.py
```

**Features**:
- Uses GraphQL API (https://liveheats.com/api/graphql)
- Fetches final rankings from first heat (which contains results)
- Attempts to fetch athlete names/sail numbers (currently limited by API)
- Maps Live Heats divisions to PWA format

**Current Limitation**:
- Live Heats GraphQL doesn't expose athlete details in the result query
- Currently only captures athlete IDs
- Names/sail numbers are empty in output

**Statistics** (as of Oct 2025):
- 5 divisions scraped successfully
- 48 athlete results
- 0 errors

---

### 4. Results Merger

**File**: [src/scrapers/merge_wave_results.py](src/scrapers/merge_wave_results.py)

**Purpose**: Merge PWA and Live Heats results into unified dataset

**Input**:
- `data/raw/pwa/pwa_wave_results_updated.csv`
- `data/raw/liveheats/liveheats_matched_results.csv`

**Output**:
- `data/processed/wave_results_merged.csv`

**Usage**:
```bash
cd src/scrapers
python merge_wave_results.py
```

**Merge Strategy**:
1. Load both sources
2. Standardize column format
3. Identify overlapping events (same event_id in both sources)
4. For overlaps: prioritize PWA (has complete athlete info)
5. Include unique events from both sources
6. Sort by year (desc), event, division, place

**Deduplication**:
- Events in BOTH sources → Keep PWA version only
- Events in PWA only → Include
- Events in Live Heats only → Include

**Expected Output** (estimated):
- ~1,880 - 1,900 total records
- Mostly PWA data
- Small number of Live Heats-only events (if any)

---

### 5. Complete Pipeline Orchestrator

**File**: [src/scrapers/run_complete_results_pipeline.py](src/scrapers/run_complete_results_pipeline.py)

**Purpose**: Run the entire pipeline in sequence

**Usage**:
```bash
# Run full pipeline
cd src/scrapers
python run_complete_results_pipeline.py

# Skip certain steps (use existing data)
python run_complete_results_pipeline.py --skip-pwa
python run_complete_results_pipeline.py --skip-matching
python run_complete_results_pipeline.py --skip-liveheats

# Skip all scraping, just re-run merge
python run_complete_results_pipeline.py --skip-pwa --skip-matching --skip-liveheats
```

**Pipeline Steps**:
1. **PWA Scraping** (optional: --skip-pwa)
   - Runs `pwa_results_scraper.py`
   - Updates `pwa_wave_results_updated.csv`

2. **Event Matching** (optional: --skip-matching)
   - Runs `match_pwa_to_liveheats.py`
   - Updates matching report

3. **Live Heats Scraping** (optional: --skip-liveheats)
   - Runs `scrape_liveheats_matched_results.py`
   - Updates `liveheats_matched_results.csv`

4. **Merge** (always runs unless all previous failed)
   - Runs `merge_wave_results.py`
   - Creates final unified dataset

**Exit Codes**:
- 0: Success
- 1: Errors occurred

---

## Quick Start

### Option 1: Run Complete Pipeline

```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"

# Run everything from scratch (WARNING: Takes 30-60 minutes)
python src/scrapers/run_complete_results_pipeline.py
```

### Option 2: Use Existing Data and Just Merge

```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"

# Skip scraping, just merge existing data
python src/scrapers/run_complete_results_pipeline.py --skip-pwa --skip-matching --skip-liveheats

# Or run merge directly
python src/scrapers/merge_wave_results.py
```

### Option 3: Run Individual Scripts

```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"

# 1. Scrape PWA results (if needed)
python src/scrapers/pwa_results_scraper.py

# 2. Match events (if needed)
python src/scrapers/match_pwa_to_liveheats.py

# 3. Scrape Live Heats (if needed)
python src/scrapers/scrape_liveheats_matched_results.py

# 4. Merge
python src/scrapers/merge_wave_results.py
```

---

## Current Data Status (Oct 2025)

### PWA Results
- **File**: `data/raw/pwa/pwa_wave_results_updated.csv`
- **Records**: 1,880
- **Events**: 55 wave events (2016-2025)
- **Completeness**: ✅ Full athlete names, sail numbers, IDs
- **Last Updated**: 2025-10-18

### Live Heats Results
- **File**: `data/raw/liveheats/liveheats_matched_results.csv`
- **Records**: 48
- **Events**: 4 events (5 divisions)
- **Completeness**: ⚠️ Athlete IDs only (no names/sail numbers)
- **Last Updated**: 2025-10-20

### Matching Report
- **File**: `data/reports/pwa_liveheats_matching_report_v2.csv`
- **Matched Events**: 4 events (100% match score or 90%+)
- **Divisions**: 5 (2 Women, 3 Men)
- **Last Updated**: 2025-10-18

---

## Known Issues & Limitations

### 1. Live Heats Athlete Names Missing

**Problem**: Live Heats GraphQL API doesn't expose athlete details in result queries

**Impact**: `athlete_name` and `sail_number` columns are empty for Live Heats records

**Workaround Options**:
1. **Use PWA data priority** (current approach)
   - For overlapping events, always use PWA results
   - Live Heats data only used for events NOT in PWA

2. **Future enhancement**: Cross-reference athlete IDs
   - Build athlete ID mapping table (PWA ID ↔ Live Heats ID)
   - Enrich Live Heats results with names from mapping

3. **Manual enrichment**: Small dataset (48 records)
   - Could manually add athlete names if needed

### 2. Overlapping Events Handling

**Current Strategy**: PWA takes priority for all overlapping events

**Rationale**:
- PWA has complete athlete information
- Live Heats missing athlete names
- Consistency is more important than having multiple sources

**Alternative Strategy** (not implemented):
- Keep both sources, mark with different `source` values
- Allows comparing data quality between sources
- Adds complexity for downstream analysis

### 3. Event Matching Accuracy

**Current Matching**: 100% confident for all 4 matched events

**Potential Issues**:
- Some PWA events might not be in Live Heats
- Some Live Heats events might not be in PWA
- Future events might need manual review

---

## Next Steps & Enhancements

### Short-term
1. ✅ **Test merge script**
   - Run `merge_wave_results.py`
   - Verify output quality
   - Check deduplication logic

2. **Validate merged data**
   - Spot-check athlete placements
   - Verify no duplicate event/division/athlete combinations
   - Check date ranges

3. **Load to database**
   - Create `WAVE_RESULTS` table in MySQL
   - Load merged CSV
   - Add indexes for querying

### Medium-term
1. **Athlete ID mapping**
   - Build cross-reference table PWA ↔ Live Heats
   - Enrich Live Heats records with athlete names
   - Handle name variations

2. **Automated updates**
   - Schedule pipeline to run weekly/monthly
   - Detect new events automatically
   - Incremental updates instead of full scrapes

3. **Data quality validation**
   - Check for missing data
   - Verify placement sequences (1, 2, 3...)
   - Flag suspicious results

### Long-term
1. **Heat-level data**
   - Scrape individual heat scores (not just final results)
   - Build heat progression trees
   - Analyze performance across heats

2. **Web application**
   - Display unified results
   - Filter by year, location, athlete
   - Compare athlete performance over time

---

## Troubleshooting

### "No such file or directory" errors

**Problem**: Script can't find input files

**Solution**: Run scripts from project root:
```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"
python src/scrapers/script_name.py
```

### GraphQL errors from Live Heats

**Problem**: API structure changed or fields unavailable

**Solution**:
1. Check Live Heats API docs (if available)
2. Use GraphQL introspection to explore schema
3. Fall back to athlete IDs only (current approach)

### Merge produces fewer records than expected

**Problem**: Deduplication removing too many records

**Solution**:
1. Check matching report for overlapping events
2. Review `overlapping_events` in merge script output
3. Consider changing priority strategy if needed

### PWA scraper timing out

**Problem**: SSL issues or rate limiting

**Solution**:
1. Increase timeout values in scraper
2. Add longer delays between requests
3. Use `--skip-pwa` flag and use existing data

---

## Contact & Support

For questions about this pipeline:
- Review this guide
- Check script comments/docstrings
- Examine output logs from scrapers

**Last Updated**: 2025-10-20
**Version**: 1.0
