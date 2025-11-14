# Athlete Database Implementation Guide

## Overview

This guide walks you through building a unified athlete database by:
1. Extracting unique athletes from existing competition results
2. Scraping athlete profiles from PWA and LiveHeats
3. Matching athletes across both sources using fuzzy matching
4. Loading the unified data into MySQL database

## Prerequisites

- SSH tunnel to Oracle MySQL database must be running
- Python packages required: `pandas`, `mysql-connector-python`, `beautifulsoup4`, `requests`, `fuzzywuzzy`, `python-Levenshtein`
- Country mapping file: `ATHLETE DATABASE SCRIPTS OLD/Clean Data/country_info_v2.csv`

## Execution Steps

### Phase 1: Extract Unique Athletes

Extract all unique athlete IDs from the PWA_IWT_RESULTS table.

```bash
python src/scrapers/extract_unique_athletes.py
```

**Output:**
- `data/raw/athletes/unique_athletes_from_db.csv` - All unique athletes
- `data/raw/athletes/pwa_athletes_to_scrape.csv` - PWA athletes only
- `data/raw/athletes/liveheats_athletes_to_scrape.csv` - LiveHeats athletes only

**Expected Results:**
- ~346 PWA athletes
- ~112 LiveHeats athletes

---

### Phase 2A: Scrape PWA Athlete Profiles

Scrape detailed profiles from PWA website for all PWA athletes.

```bash
python src/scrapers/scrape_pwa_athlete_profiles.py
```

**What it does:**
- Uses BeautifulSoup to scrape PWA profile pages
- Extracts: name, age, nationality, sail number, sponsors
- Calculates year of birth from current age
- Applies data cleaning rules (removes invalid profiles)

**Output:**
- `data/raw/athletes/pwa_athletes_raw.csv` - Raw scraped data
- `data/raw/athletes/pwa_athletes_clean.csv` - Cleaned data

**Duration:** ~3-5 minutes (0.5s delay per athlete)

---

### Phase 2B: Scrape LiveHeats Athlete Profiles

Scrape detailed profiles from LiveHeats GraphQL API for all LiveHeats athletes.

```bash
python src/scrapers/scrape_liveheats_athlete_profiles.py
```

**What it does:**
- Uses GraphQL API to fetch athlete details
- Extracts: name, image URL, date of birth, nationality
- Merges duplicate records (same athlete with multiple IDs)

**Output:**
- `data/raw/athletes/liveheats_athletes_raw.csv` - Raw scraped data
- `data/raw/athletes/liveheats_athletes_raw.json` - Raw JSON format
- `data/raw/athletes/liveheats_athletes_clean.csv` - Cleaned data

**Duration:** ~1-2 minutes (0.5s delay per athlete)

---

### Phase 3: Match Athletes Across Sources

Use 4-stage fuzzy matching to link PWA and LiveHeats athletes.

```bash
python src/scrapers/match_pwa_liveheats_athletes.py
```

**Matching Strategy:**
1. **Stage 1:** Exact match + fuzzy ≥91%
2. **Stage 2:** Year of birth ±1 + fuzzy ≥80%
3. **Stage 3:** Country match + fuzzy ≥90%
4. **Stage 4:** Mark as unmatched

**Output:**
- `data/processed/athletes/athletes_matched.csv` - All matches with scores
- `data/processed/athletes/athletes_needs_review.csv` - **Scores 80-89% (manual review required)**
- `data/processed/athletes/athletes_pwa_only.csv` - Unmatched PWA athletes
- `data/processed/athletes/athletes_liveheats_only.csv` - Unmatched LiveHeats athletes

**Expected Results:**
- High-confidence matches (≥90%): Majority of athletes
- Borderline matches (80-89%): ~10-20 athletes requiring manual review
- Unmatched athletes: Those unique to one source

---

### Phase 4: Manual Review (IMPORTANT!)

Review borderline matches in `athletes_needs_review.csv`.

**Process:**
1. Open `data/processed/athletes/athletes_needs_review.csv`
2. For each match, verify if PWA and LiveHeats athletes are the same person
3. Create a new file: `data/processed/athletes/manual_match_decisions.csv`

**Format for manual_match_decisions.csv:**
```csv
lh_athlete_id,pwa_athlete_id,lh_name,pwa_name,score,stage,decision
1169354,1884,Adam Warchol,Adam Warchol,85,YOB±1,accept
1076672,2215,Alex Levy,Adrian Levy,82,Fuzzy91,reject
```

**Columns:**
- Copy all columns from `athletes_needs_review.csv`
- Add `decision` column with values: `accept` or `reject`

**If no manual review needed (all matches ≥90%):**
- Skip this step - the merge script will only use high-confidence matches

---

### Phase 5: Merge Final Athlete Data

Combine all data into final unified tables.

```bash
python src/scrapers/merge_final_athletes.py
```

**What it does:**
- Combines high-confidence matches (≥90%)
- Includes manually accepted matches (if manual_match_decisions.csv exists)
- Appends PWA-only athletes
- Appends LiveHeats-only athletes
- Assigns unified athlete IDs (auto-increment from 1)
- Creates link table mapping unified IDs to source IDs

**Output:**
- `data/processed/athletes/athletes_final.csv` - Master athlete list
- `data/processed/athletes/athlete_ids_link.csv` - Link table

**Expected Results:**
- Total athletes: ~400-450 (depends on match success rate)
- Both sources: ~100-150 matched athletes
- PWA-only: ~200-250 athletes
- LiveHeats-only: ~0-50 athletes

---

### Phase 6: Create Database Tables

Create ATHLETES and ATHLETE_SOURCE_IDS tables in MySQL.

```bash
cd src/database
python create_athlete_tables.py
```

**What it does:**
- Drops existing ATHLETES and ATHLETE_SOURCE_IDS tables (if they exist)
- Creates new tables with proper schema
- Adds indexes for performance
- Verifies table creation

**Tables Created:**
1. **ATHLETES** - Master athlete table with 19 columns
2. **ATHLETE_SOURCE_IDS** - Link table with foreign key to ATHLETES

---

### Phase 7: Load Data into Database

Load CSV files into MySQL tables.

```bash
cd src/database
python load_athletes.py
```

**What it does:**
- Loads `athletes_final.csv` → ATHLETES table
- Loads `athlete_ids_link.csv` → ATHLETE_SOURCE_IDS table
- Uses batch processing (100-500 records per batch)
- Uses `ON DUPLICATE KEY UPDATE` for upserts
- Verifies data load with sample queries

**Expected Results:**
- ATHLETES table: 400-450 records
- ATHLETE_SOURCE_IDS table: 600-800 records (multiple IDs per athlete)

---

## Database Schema

### ATHLETES Table

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Unified athlete ID |
| primary_name | VARCHAR(255) | Best name (LiveHeats preferred) |
| pwa_name | VARCHAR(255) | Name from PWA |
| liveheats_name | VARCHAR(255) | Name from LiveHeats |
| match_score | INT | Fuzzy match confidence (0-100) |
| match_stage | VARCHAR(50) | Matching stage used |
| year_of_birth | INT | Best YOB (LiveHeats preferred) |
| nationality | VARCHAR(100) | Best nationality |
| pwa_athlete_id | VARCHAR(50) | PWA athlete ID |
| pwa_sail_number | VARCHAR(50) | PWA sail number |
| pwa_profile_url | TEXT | PWA profile URL |
| pwa_sponsors | TEXT | Current sponsors (PWA) |
| pwa_nationality | VARCHAR(100) | Nationality from PWA |
| pwa_year_of_birth | INT | Year of birth from PWA |
| liveheats_athlete_id | VARCHAR(50) | LiveHeats athlete ID |
| liveheats_image_url | TEXT | Profile image URL |
| liveheats_dob | DATE | Date of birth |
| liveheats_nationality | VARCHAR(100) | Nationality from LiveHeats |
| liveheats_year_of_birth | INT | Year of birth from LiveHeats |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### ATHLETE_SOURCE_IDS Table

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Auto-increment ID |
| athlete_id | INT (FK) | References ATHLETES.id |
| source | VARCHAR(50) | Source type (PWA, Live Heats, PWA_sail_number) |
| source_id | VARCHAR(100) | Source-specific ID |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

**Unique constraint:** (source, source_id)

---

## Verification Queries

After loading data, verify with these SQL queries:

```sql
-- Count total athletes
SELECT COUNT(*) FROM ATHLETES;

-- Count by match stage
SELECT match_stage, COUNT(*) as count
FROM ATHLETES
GROUP BY match_stage
ORDER BY count DESC;

-- Athletes with both PWA and LiveHeats IDs
SELECT COUNT(*) FROM ATHLETES
WHERE pwa_athlete_id IS NOT NULL
  AND liveheats_athlete_id IS NOT NULL;

-- Count source IDs by type
SELECT source, COUNT(*) as count
FROM ATHLETE_SOURCE_IDS
GROUP BY source;

-- Sample athletes with all details
SELECT id, primary_name, nationality, year_of_birth,
       pwa_sail_number, liveheats_athlete_id, match_stage
FROM ATHLETES
LIMIT 20;
```

---

## Troubleshooting

### Database Connection Errors
**Error:** `Can't connect to MySQL server on 'localhost:3306'`
**Solution:** Ensure SSH tunnel to Oracle Cloud is running

### Scraping Timeouts
**Error:** `Connection timeout` or `Request timeout`
**Solution:**
- Check internet connection
- PWA/LiveHeats websites may be temporarily down
- Increase timeout values in scraper scripts

### Missing Country Mapping
**Warning:** `Country mapping file not found`
**Impact:** Stage 3 country-based matching will be skipped
**Solution:** Ensure `ATHLETE DATABASE SCRIPTS OLD/Clean Data/country_info_v2.csv` exists

### Low Match Rate
**Issue:** Very few athletes matched between sources
**Possible causes:**
- Name format differences (check manual corrections needed)
- Missing year of birth data
- Country mapping issues
**Solution:** Review `athletes_needs_review.csv` for patterns

### Duplicate Key Errors
**Error:** `Duplicate entry for key 'unique_source_id'`
**Solution:**
- Database may already have data
- Drop and recreate tables, or
- Review for actual duplicate athletes in source data

---

## File Structure

```
Windsurf World Tour Stats/
├── src/
│   ├── scrapers/
│   │   ├── extract_unique_athletes.py          [Phase 1]
│   │   ├── scrape_pwa_athlete_profiles.py      [Phase 2A]
│   │   ├── scrape_liveheats_athlete_profiles.py [Phase 2B]
│   │   ├── match_pwa_liveheats_athletes.py     [Phase 3]
│   │   └── merge_final_athletes.py             [Phase 5]
│   └── database/
│       ├── create_athlete_tables.py            [Phase 6]
│       └── load_athletes.py                    [Phase 7]
├── data/
│   ├── raw/athletes/
│   │   ├── unique_athletes_from_db.csv
│   │   ├── pwa_athletes_to_scrape.csv
│   │   ├── liveheats_athletes_to_scrape.csv
│   │   ├── pwa_athletes_raw.csv
│   │   ├── pwa_athletes_clean.csv
│   │   ├── liveheats_athletes_raw.csv
│   │   ├── liveheats_athletes_raw.json
│   │   └── liveheats_athletes_clean.csv
│   └── processed/athletes/
│       ├── athletes_matched.csv
│       ├── athletes_needs_review.csv          [MANUAL REVIEW]
│       ├── athletes_pwa_only.csv
│       ├── athletes_liveheats_only.csv
│       ├── manual_match_decisions.csv         [USER CREATES]
│       ├── athletes_final.csv
│       └── athlete_ids_link.csv
└── ATHLETE DATABASE SCRIPTS OLD/
    └── Clean Data/
        └── country_info_v2.csv                [REQUIRED]
```

---

## Next Steps After Database Load

Once athlete data is loaded:

1. **Update Results Tables:** Add foreign keys from PWA_IWT_RESULTS.athlete_id to ATHLETES.id
2. **Create Views:** Useful views joining results with athlete profiles
3. **Data Analysis:** Query combined competition results + athlete metadata
4. **Web Application:** Display athlete profiles, statistics, career results

---

## Summary

**Total Scripts:** 7
**Total Phases:** 7 (1 requires manual review)
**Estimated Time:** 30-60 minutes (including manual review)
**Database Tables:** 2 new tables in jfa_heatwave_db
**Final Records:** ~400-450 athletes, ~600-800 ID mappings

All scripts follow the same patterns as existing PWA/LiveHeats data scrapers and use proven fuzzy matching techniques from your previous athlete database work.
