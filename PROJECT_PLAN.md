# Windsurf World Tour Stats - Project Plan

**Last Updated**: 2025-10-18
**Project Goal**: Build a comprehensive database and web application for professional windsurf wave event results (PWA & IWT/Live Heats, 2016+)

---

## Project Overview

This project scrapes historical and current windsurf wave event data from two main sources:
- **PWA (Professional Windsurfers Association)**: 2016+ wave events
- **Live Heats (IWT)**: 2023+ PWA/IWT 4-5 star events

The data will be stored in Oracle MySQL Heatwave database and displayed via a public-facing web application.

**Pilot Phase**: Wave events only (4-5 star competitions)

---

## Current Status: Phase 1 - Data Collection ✅

### ✅ Completed Tasks

#### 1. Project Setup
- [x] Created folder structure (`/src/scrapers`, `/data/raw`, `/data/cleaned`, `/logs`)
- [x] Set up Python environment with dependencies (selenium, pandas, beautifulsoup4, etc.)
- [x] Created `requirements.txt`

#### 2. PWA Event Scraper
- [x] Built `src/scrapers/pwa_event_scraper.py`
- [x] Successfully scraped 118 total events (55 wave events) from 2016-2025
- [x] Output: `data/raw/pwa/pwa_events_raw.csv`

**Scraped Data Fields**:
```
source, scraped_at, year, event_id, event_name, event_url, event_date,
start_date, end_date, day_window, event_section, event_status,
competition_state, has_wave_discipline, all_disciplines, country_flag,
country_code, stars, event_image_url
```

**Statistics**:
- Total Events: 118
- Wave Events: 55
- Years: 2016-2025 (10 years)
- Star Ratings: 4★ (8), 5★ (15), 6★ (4), 7★ (6), None (22 older events)

---

## Project Phases

### Phase 1: PWA Event Metadata (CURRENT) 🔄

**Goal**: Scrape all PWA wave event metadata to serve as master event list

**Status**: IN PROGRESS

#### Remaining Tasks:
- [ ] Create data cleaning script for PWA events
  - Filter for wave events only (`has_wave_discipline = True`)
  - Filter for 4-5 star events (or events with no star rating for older competitions)
  - Standardize event names, locations, dates
  - Handle missing/null values
  - Output: `data/cleaned/pwa/pwa_events_cleaned.csv`

- [ ] Create event validation script
  - Check for missing critical fields
  - Identify duplicate events
  - Flag data quality issues
  - Generate data quality report

---

### Phase 2: PWA Detailed Event Data 📋

**Goal**: For each wave event, scrape divisions, eliminations, heats, results, and scores

**Status**: NOT STARTED

#### Tasks:

1. **Division & Elimination Scraper**
   - For each event_id, visit elimination ladder page
   - Extract division names (e.g., "Wave Men", "Wave Women")
   - Extract division/elimination IDs
   - Identify 4-5 star wave divisions only
   - Output: `data/raw/pwa/pwa_divisions_raw.csv`

2. **Heat Progression Scraper**
   - Fetch XML data: `https://www.pwaworldtour.com/fileadmin/live_ladder/live_ladder_{category_code}.xml`
   - Extract heat bracket structure (rounds, heats, progression rules)
   - Output: `data/raw/pwa/pwa_heat_progression_raw.csv`

3. **Heat Results Scraper**
   - From same XML, extract athlete results per heat
   - Extract sailor names, sail numbers, heat placements
   - Output: `data/raw/pwa/pwa_heat_results_raw.csv`

4. **Heat Scores Scraper**
   - Fetch JSON data: `https://www.pwaworldtour.com/fileadmin/live_score/{heat_id}.json`
   - Extract individual wave/jump scores
   - Output: `data/raw/pwa/pwa_heat_scores_raw.csv`

5. **Final Rankings Scraper**
   - Visit results page for each division
   - Extract final event rankings and points
   - Output: `data/raw/pwa/pwa_final_rankings_raw.csv`

**Reference**: Use existing code from `old_scripts/Script/functions_pwa_scrape.py`

---

### Phase 3: Live Heats Event Data 📋

**Goal**: Scrape PWA/IWT events from Live Heats (2023+, 4-5 stars, wave only)

**Status**: NOT STARTED

#### Tasks:

1. **Live Heats Event Scraper**
   - GraphQL API: `https://liveheats.com/api/graphql`
   - Query "WaveTour" organization events
   - Filter: 2023+, 4-5 stars, results published
   - Output: `data/raw/liveheats/liveheats_events_raw.csv`

2. **Live Heats Division Scraper**
   - For each event, fetch divisions via GraphQL
   - Output: `data/raw/liveheats/liveheats_divisions_raw.csv`

3. **Live Heats Heat Data Scraper**
   - Fetch heat progression, results, scores via GraphQL
   - Output:
     - `data/raw/liveheats/liveheats_heat_progression_raw.csv`
     - `data/raw/liveheats/liveheats_heat_results_raw.csv`
     - `data/raw/liveheats/liveheats_heat_scores_raw.csv`

4. **Live Heats Final Rankings**
   - Calculate final rankings from heat data
   - Output: `data/raw/liveheats/liveheats_final_rankings_raw.csv`

**Reference**: Use existing code from `old_scripts/Script/functions_iwt_scrape.py`

---

### Phase 4: Data Cleaning & Standardization 🧹

**Goal**: Clean, standardize, and merge PWA + Live Heats data into unified CSVs

**Status**: NOT STARTED

#### Tasks:

1. **Standardize Column Names**
   - Map PWA fields → Standard schema
   - Map Live Heats fields → Standard schema
   - Preserve `source` column for traceability

2. **Athlete ID Standardization**
   - PWA format: `{Sailor_Name}_{Sail_Number}`
   - Live Heats format: `{athleteId}`
   - Create unified athlete ID system
   - Build master athlete list

3. **Event Deduplication**
   - Match events appearing in both sources
   - Handle conflicts (prefer PWA or Live Heats?)
   - Flag duplicate events

4. **Data Validation**
   - Check for missing required fields
   - Validate date formats, numeric fields
   - Flag outliers/anomalies

5. **Create Merged CSVs**
   - `data/cleaned/merged/events.csv`
   - `data/cleaned/merged/divisions.csv`
   - `data/cleaned/merged/heat_progression.csv`
   - `data/cleaned/merged/heat_results.csv`
   - `data/cleaned/merged/heat_scores.csv`
   - `data/cleaned/merged/final_rankings.csv`
   - `data/cleaned/merged/athletes.csv`

**Reference**: Use existing code from `old_scripts/Script/functions_clean.py`

---

### Phase 5: Database Design & Integration 🗄️

**Goal**: Design database schema and load data into Oracle MySQL Heatwave

**Status**: NOT STARTED

#### Database Connection:
- **Platform**: Oracle MySQL Heatwave (already set up)
- **Connection**: pyodbc with ODBC Driver 18 for SQL Server
- **Credentials**: Store in `.env` file (git-ignored)

#### Database Schema Design:

**Tables to Create**:

1. **events**
   - event_id (PK)
   - source (PWA/Live Heats)
   - event_name, standard_event_name
   - location, country_code
   - start_date, end_date, day_window
   - stars, year
   - pwa_event_id, liveheats_event_id (for cross-reference)

2. **divisions**
   - division_id (PK)
   - event_id (FK)
   - division_name (Men/Women)
   - elimination_name, elimination_type
   - source_division_id

3. **heats**
   - heat_id (PK)
   - division_id (FK)
   - round_name, round_order
   - heat_order
   - progression rules

4. **heat_results**
   - result_id (PK)
   - heat_id (FK)
   - athlete_id (FK)
   - place, result_total
   - winBy, needs

5. **heat_scores**
   - score_id (PK)
   - heat_id (FK)
   - athlete_id (FK)
   - score, type (wave/jump)
   - counting (boolean)
   - modified_total, modifier

6. **final_rankings**
   - ranking_id (PK)
   - division_id (FK)
   - athlete_id (FK)
   - place, points

7. **athletes**
   - athlete_id (PK)
   - athlete_name
   - sail_number
   - country_code
   - pwa_athlete_id, liveheats_athlete_id

#### Tasks:
- [ ] Create database connection module
- [ ] Write SQL schema creation scripts
- [ ] Build data loading scripts (CSV → DB)
- [ ] Implement upsert logic (update existing, insert new)
- [ ] Create database indexes for performance
- [ ] Add data validation before insert

---

### Phase 6: Update & Maintenance Scripts 🔄

**Goal**: Create scripts to update database with new events/results

**Status**: NOT STARTED

#### Tasks:
- [ ] Incremental scraper (only new events)
- [ ] Change detection (identify updated results)
- [ ] Automated scheduling (cron/task scheduler)
- [ ] Error handling & logging
- [ ] Data backup procedures

---

### Phase 7: Web Application (Future) 🌐

**Goal**: Build public-facing web app to display stats

**Status**: NOT STARTED - DEFERRED

**Note**: Database and data pipeline must be complete before starting web app development.

---

## Technical Stack

### Data Collection & Processing:
- **Language**: Python 3.13
- **Web Scraping**: Selenium (PWA), Requests (Live Heats GraphQL)
- **Data Processing**: Pandas, NumPy
- **HTML Parsing**: BeautifulSoup4, lxml

### Database:
- **Platform**: Oracle MySQL Heatwave
- **Driver**: pyodbc (ODBC Driver 18 for SQL Server)
- **Connection String Format**:
  ```
  DRIVER={ODBC Driver 18 for SQL Server};SERVER=server.database.windows.net;
  DATABASE=dbname;UID=username;PWD=password;Encrypt=yes;
  TrustServerCertificate=no;Connection Timeout=60;CommandTimeout=60;
  ```

### Future (Web App):
- TBD (React, Vue, Flask, Django, etc.)

---

## Data Schema Mapping

### Unified CSV Schema

#### events.csv
```csv
source, event_id, pwa_event_id, liveheats_event_id, event_name,
standard_event_name, location, country_code, start_date, end_date,
day_window, stars, year, event_url, event_status
```

#### divisions.csv
```csv
source, division_id, event_id, division_name, sex, elimination_name,
elimination_id, elimination_type, pwa_division_id, liveheats_division_id
```

#### heat_progression.csv
```csv
source, event_id, division_id, heat_id, round_name, round_order,
heat_order, total_winners_progressing, winners_progressing_to_round_order,
total_losers_progressing, losers_progressing_to_round_order
```

#### heat_results.csv
```csv
source, event_id, division_id, heat_id, athlete_id, place, result_total,
winBy, needs, round_name, round_order
```

#### heat_scores.csv
```csv
source, event_id, division_id, heat_id, athlete_id, score, modified_total,
modifier, type, counting, total_wave, total_jump, total_points
```

#### final_rankings.csv
```csv
source, event_id, division_id, athlete_id, athlete_name, sail_number,
place, points
```

#### athletes.csv
```csv
athlete_id, athlete_name, sail_number, country_code, pwa_athlete_id,
liveheats_athlete_id, first_seen_event, last_seen_event
```

---

## Key Decisions & Considerations

### 1. Unified vs. Separate Data Approach
**Decision**: Unified CSVs with `source` column
**Rationale**:
- Simpler database schema (one table per entity type)
- Easier querying and analysis
- Full traceability via `source` column
- Better for eventual web app (single query vs. union)

### 2. Star Rating Filter
**Decision**: Include 4-5 star events + older events without star ratings
**Rationale**:
- Older events (pre-2022) often don't have star ratings in titles
- These are still high-level competitions
- Can filter by year if needed

### 3. Athlete ID Strategy
**Decision**: Create unified athlete_id, preserve source-specific IDs
**Rationale**:
- PWA and Live Heats may have different athlete identifiers
- Need consistent ID across sources for athlete statistics
- Preserve source IDs for debugging/verification

### 4. Event Deduplication
**Decision**: Prefer PWA data when events appear in both sources
**Rationale**:
- PWA is the official tour organization
- PWA data often more complete for heat scores
- Live Heats may have more recent events (2023+)

---

## File Structure

```
Windsurf World Tour Stats/
├── src/
│   ├── scrapers/
│   │   ├── pwa_event_scraper.py         ✅ COMPLETE
│   │   ├── pwa_division_scraper.py      📋 TODO
│   │   ├── pwa_heat_scraper.py          📋 TODO
│   │   ├── liveheats_scraper.py         📋 TODO
│   │   └── ...
│   ├── cleaning/
│   │   ├── clean_events.py              📋 TODO
│   │   ├── clean_heats.py               📋 TODO
│   │   ├── merge_sources.py             📋 TODO
│   │   └── ...
│   ├── database/
│   │   ├── connection.py                📋 TODO
│   │   ├── schema.sql                   📋 TODO
│   │   ├── load_data.py                 📋 TODO
│   │   └── ...
│   └── utils/
│       ├── helpers.py
│       └── validation.py
├── data/
│   ├── raw/
│   │   ├── pwa/
│   │   │   └── pwa_events_raw.csv       ✅ COMPLETE (118 events, 55 wave)
│   │   └── liveheats/
│   └── cleaned/
│       ├── pwa/
│       ├── liveheats/
│       └── merged/
├── logs/
├── old_scripts/                         📚 Reference code
│   └── Script/
│       ├── historical_scrape_pwa.py
│       ├── historical_scrape_iwt.py
│       ├── functions_pwa_scrape.py
│       ├── functions_iwt_scrape.py
│       └── functions_clean.py
├── config/
│   └── config.py
├── .env                                 📋 TODO (DB credentials)
├── .gitignore
├── requirements.txt                     ✅ COMPLETE
├── PROJECT_PLAN.md                      📄 THIS FILE
└── README.md                            📋 TODO

```

---

## Next Immediate Steps

### Option 1: Continue PWA Data Pipeline
1. Create PWA event cleaning script
2. Create PWA division/elimination scraper
3. Create PWA heat data scraper
4. Create PWA final rankings scraper

### Option 2: Start Live Heats Pipeline
1. Create Live Heats event scraper (similar to PWA)
2. Extract event metadata from GraphQL API
3. Build out rest of Live Heats scrapers

### Option 3: Focus on Data Quality
1. Create event data cleaning script first
2. Validate PWA event data
3. Create data quality reports
4. Fix any data issues before proceeding

---

## Success Metrics

### Phase 1-3 (Data Collection):
- ✅ 100% of PWA wave events scraped (2016+)
- ✅ 100% of Live Heats wave events scraped (2023+, 4-5★)
- ✅ All heat progression, results, scores captured
- ✅ All final rankings captured

### Phase 4 (Data Quality):
- ✅ <5% missing data in critical fields
- ✅ 100% of athletes have valid IDs
- ✅ All dates in valid format
- ✅ No duplicate events (or flagged appropriately)

### Phase 5 (Database):
- ✅ Database schema created and optimized
- ✅ All data successfully loaded
- ✅ Query performance acceptable (<1s for typical queries)
- ✅ Data integrity constraints enforced

### Phase 6 (Updates):
- ✅ Update script runs successfully
- ✅ New events added within 24 hours of completion
- ✅ Zero data corruption from updates

---

## Questions & Decisions Needed

1. **Star Rating Handling**: How to handle events without star ratings? Include all wave events or apply different filter?

2. **Athlete Matching**: How to match athletes across PWA and Live Heats when names may differ slightly?

3. **Event Matching**: How to definitively match events that appear in both PWA and Live Heats?

4. **Database Hosting**: Will Oracle MySQL Heatwave be sufficient for future scale? Need to confirm connection details.

5. **Update Frequency**: How often should the database be updated? Daily? Weekly? Event-by-event?

6. **Historical Completeness**: Should we go back further than 2016 if PWA has older data?

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| PWA website structure changes | High | Monitor for errors, version scraper code |
| Live Heats API changes | High | GraphQL typically stable, but add error handling |
| Data quality issues in source | Medium | Implement robust validation, manual review |
| Database connection issues | Medium | Use connection pooling, retry logic |
| Athlete name variations | Medium | Fuzzy matching algorithm, manual review |
| Missing historical data | Low | Accept gaps, flag incomplete data |

---

## Notes & Observations

### PWA Data Notes:
- Star ratings appear in event titles as asterisks (*)
- Older events (pre-2022) often don't show star ratings
- Wave discipline identified by `icon-discipline-1` CSS class
- Events have multiple disciplines (wave, slalom, freestyle)
- COVID years (2020-2021) have "Cancelled due to COVID-19" section

### Live Heats Data Notes:
- GraphQL API is well-structured and reliable
- Event status field: "results_published" needed for completed events
- Division structure similar to PWA but different field names
- More recent events (2023+) likely have better data quality

### Technical Notes:
- Selenium needed for PWA (JavaScript-heavy site)
- Simple HTTP requests work for Live Heats GraphQL
- CSV intermediates allow for data inspection before DB load
- Python 3.13 compatible with all dependencies

---

**Document Status**: Living document - update as project progresses
