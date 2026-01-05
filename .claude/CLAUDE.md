# Windsurf World Tour Stats - Project Context

## Project Overview
Building a comprehensive database and web application for professional windsurf wave event results from PWA (Professional Windsurfers Association) and IWT/Live Heats (2016+). **Currently in Phase 4 - Athlete Data Integration COMPLETE**.

**Goal**: Scrape, clean, store, and display historical windsurf wave event data (4-5 star competitions) with unified athlete profiles.

**Status**: All PWA and LiveHeats data successfully scraped, merged, and loaded into unified database with complete heat-level detail. Athlete matching system complete with 359 unified athletes. FastAPI serving data via production HTTPS endpoint with optimized connection pooling and reliability improvements (Dec 2025).

---

## Database Connection

### Oracle MySQL Heatwave via SSH Tunnel

**IMPORTANT**: Always use SSH tunnel to connect to the database. Connection must use `mysql-connector-python` (NOT pyodbc).

#### Environment Variables (.env)
```bash
# MySQL Connection via SSH Tunnel
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jfa_heatwave_db
DB_USER=admin
DB_PASSWORD=<your_password>
```

#### Connection Pattern
```python
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Create connection to Oracle MySQL Heatwave database"""
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        connect_timeout=30
    )
    return conn
```

#### SQL Parameterization
- Use `%s` for placeholders (mysql-connector-python syntax)
- NOT `?` (that's for pyodbc/sqlite)

#### Before Running Database Scripts
1. Ensure SSH tunnel is running to Oracle Cloud server
2. Test connection with: `python test_db_connection.py`
3. Use absolute paths for CSV files when running from subdirectories

---

## Project Structure

```
Windsurf World Tour Stats/
├── src/
│   ├── api/               # FastAPI production application
│   │   ├── main.py                               ✅ COMPLETE
│   │   ├── config.py                             ✅ COMPLETE
│   │   ├── database.py                           ✅ COMPLETE
│   │   ├── models.py                             ✅ COMPLETE
│   │   └── routes/
│   │       ├── events.py                         ✅ COMPLETE
│   │       └── athletes.py                       ✅ COMPLETE
│   ├── scrapers/          # Web scrapers for PWA and Live Heats
│   │   ├── pwa_event_scraper.py                  ✅ COMPLETE
│   │   ├── pwa_results_scraper.py                ✅ COMPLETE
│   │   ├── pwa_heat_scraper.py                   ✅ COMPLETE
│   │   ├── scrape_liveheats_matched_results.py   ✅ COMPLETE
│   │   ├── scrape_liveheats_heat_data.py         ✅ COMPLETE
│   │   ├── scrape_pwa_athlete_profiles.py        ✅ COMPLETE
│   │   ├── scrape_liveheats_athlete_profiles.py  ✅ COMPLETE
│   │   ├── match_pwa_liveheats_athletes.py       ✅ COMPLETE
│   │   ├── merge_final_athletes.py               ✅ COMPLETE
│   │   ├── merge_wave_results.py                 ✅ COMPLETE
│   │   ├── merge_heat_progression.py             ✅ COMPLETE
│   │   ├── merge_heat_results.py                 ✅ COMPLETE
│   │   └── merge_heat_scores.py                  ✅ COMPLETE
│   ├── database/          # Database connection and loading scripts
│   │   ├── create_tables.py                      ✅ COMPLETE (5 tables)
│   │   ├── create_athlete_tables.py              ✅ COMPLETE (2 tables)
│   │   ├── create_views.py                       ✅ COMPLETE (3 views)
│   │   ├── load_pwa_events.py                    ✅ COMPLETE
│   │   ├── load_wave_results.py                  ✅ COMPLETE
│   │   ├── load_all_heat_data.py                 ✅ COMPLETE
│   │   └── load_athletes.py                      ✅ COMPLETE
│   └── cleaning/          # Data cleaning scripts (COMPLETE)
├── data/
│   ├── raw/pwa/
│   │   ├── pwa_events_raw.csv                    ✅ 118 events (55 wave)
│   │   ├── pwa_wave_results_raw.csv              ✅ 1,879 results
│   │   ├── pwa_heat_structure.csv                ✅ 113 heats
│   │   ├── pwa_heat_results.csv                  ✅ 344 results
│   │   ├── pwa_heat_scores.csv                   ✅ PWA scores (see note)
│   │   └── pwa_athlete_profiles.csv              ✅ 281 athletes
│   ├── raw/liveheats/
│   │   ├── liveheats_matched_results.csv         ✅ 173 results (5 divisions)
│   │   ├── liveheats_heat_progression.csv        ✅ 106 heats
│   │   ├── liveheats_heat_results.csv            ✅ 449 results
│   │   ├── liveheats_heat_scores.csv             ✅ LiveHeats scores (see note)
│   │   └── liveheats_athlete_profiles.csv        ✅ 233 athletes
│   ├── processed/
│   │   ├── wave_results_merged.csv               ✅ 2,052 results
│   │   ├── heat_progression_merged.csv           ✅ 219 heats
│   │   ├── heat_results_merged.csv               ✅ 793 results
│   │   ├── heat_scores_merged.csv                ✅ 39,460 scores (deduplicated)
│   │   └── athletes/
│   │       ├── athletes_final.csv                ✅ 359 unified athletes
│   │       └── athlete_ids_link.csv              ✅ 514 source ID mappings
│   └── reports/
│       └── pwa_liveheats_matching_report.csv     ✅ Athlete matching audit
│
│ **Note on Heat Scores**: Raw CSV files may contain duplicates from multiple scraping runs.
│ Database was deduplicated in January 2026 (41,402 duplicates removed from 80,862 records).
│ Current clean database count: 39,460 records (33,223 PWA + 6,237 LiveHeats).
│
├── deployment/            # Production deployment configs
│   ├── gunicorn.conf.py                          ✅ COMPLETE
│   ├── nginx.conf                                ✅ COMPLETE
│   └── systemd/
│       └── windsurf-api.service                  ✅ COMPLETE
├── test_db_connection.py                         ✅ COMPLETE
├── .env                                          # Database credentials (git-ignored)
├── .env.production                               # Production environment vars
├── PROJECT_PLAN.md                               # Detailed project roadmap
├── DEPLOYMENT.md                                 ✅ Deployment guide
└── requirements.txt
```

---

## FastAPI Production Application

### Live API Endpoints
**Base URL**: https://windsurf-world-tour-stats-api.duckdns.org

#### Events Endpoints
- `GET /api/v1/events` - List events with filtering and pagination
- `GET /api/v1/events/{id}` - Get single event by database ID

#### Athletes Endpoints
- `GET /api/v1/athletes/summary` - List athlete career summaries with statistics
- `GET /api/v1/athletes/{athlete_id}/summary` - Get specific athlete summary
- `GET /api/v1/athletes/results` - List competition results with athlete profiles

#### Health & Documentation
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

### Running Locally
```bash
# Start SSH tunnel to database
ssh -L 3306:10.0.151.92:3306 -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128

# Run development server
uvicorn src.api.main:app --reload --port 8001

# Access at http://localhost:8001/docs
```

### Production Configuration (Updated Dec 2025)

**Deployment Location**: `/opt/windsurf-api` on Oracle Cloud VM

**Connection Pool Settings** (Optimized for reliability):
- **Pool Size**: 20 connections (increased from 5)
- **Pool Timeout**: 30 seconds (prevents infinite hangs)
- **Pool Recycle**: 3600 seconds (1 hour - prevents stale connections)
- **Pool Pre-Ping**: Enabled (validates connections before use)

**Gunicorn Configuration**:
- **Workers**: 5 (calculated as `2 x CPU cores + 1`)
- **Timeout**: 120 seconds (increased from 60s for complex queries)
- **Worker Class**: `uvicorn.workers.UvicornWorker`

**Reliability Features**:
- **Automatic retry logic**: 3 attempts with exponential backoff (0.5s, 1s, 2s)
- **Connection validation**: Pre-ping checks prevent stale connection errors
- **Connection recycling**: Hourly refresh prevents MySQL timeout issues
- **Increased timeout**: Handles complex multi-query endpoints without worker kills

**Environment Variables** (`.env.production`):
```bash
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
```

**Deployment Method**: Git-based deployment from https://github.com/datawithjack/windsurf-world-tour-stats-data.git

**Update Process**:
```bash
cd /opt/windsurf-api
git pull origin main
sudo systemctl restart windsurf-api
```

---

## Current Database Schema (Complete)

### 1. PWA_IWT_EVENTS (Event Metadata)
**Records**: 118 events (2016-2025), 55 wave discipline events

```sql
CREATE TABLE PWA_IWT_EVENTS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(50) NOT NULL,              -- 'PWA' or 'Live Heats'
    scraped_at DATETIME NOT NULL,
    year INT NOT NULL,
    event_id INT NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    event_url TEXT,
    event_date VARCHAR(100),
    start_date DATE,
    end_date DATE,
    day_window INT,
    event_section VARCHAR(100),
    event_status INT,
    competition_state INT,
    has_wave_discipline BOOLEAN DEFAULT FALSE,
    all_disciplines VARCHAR(255),
    country_flag VARCHAR(100),
    country_code VARCHAR(10),
    stars INT,
    event_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_event_id (event_id),
    INDEX idx_year (year),
    INDEX idx_country_code (country_code),
    INDEX idx_has_wave (has_wave_discipline),
    UNIQUE KEY unique_event (source, event_id)
)
```

### 2. PWA_IWT_RESULTS (Final Rankings)
**Records**: 2,052 athlete placements (1,879 PWA + 173 LiveHeats)

```sql
CREATE TABLE PWA_IWT_RESULTS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    scraped_at DATETIME NOT NULL,
    event_id INT NOT NULL,
    year INT NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    division_label VARCHAR(100) NOT NULL,
    division_code VARCHAR(50),
    sex VARCHAR(20),
    place VARCHAR(10) NOT NULL,
    athlete_name VARCHAR(255),
    sail_number VARCHAR(50),
    athlete_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_event_id (event_id),
    INDEX idx_year (year),
    INDEX idx_sex (sex),
    INDEX idx_athlete_id (athlete_id),
    INDEX idx_athlete_name (athlete_name),
    UNIQUE KEY unique_result (source, event_id, division_code, athlete_id, place)
)
```

### 3. PWA_IWT_HEAT_PROGRESSION (Heat Structure)
**Records**: 219 heat structures (113 PWA + 106 LiveHeats)

```sql
CREATE TABLE PWA_IWT_HEAT_PROGRESSION (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    scraped_at DATETIME,
    pwa_event_id INT NOT NULL,
    pwa_year INT,
    pwa_event_name VARCHAR(255),
    pwa_division_code VARCHAR(50),
    sex VARCHAR(20),
    round_name VARCHAR(100),
    round_order INT,
    heat_id VARCHAR(100) NOT NULL,
    heat_order INT,
    total_winners_progressing INT,
    winners_progressing_to_round_order INT,
    total_losers_progressing INT,
    losers_progressing_to_round_order INT,
    elimination_name TEXT,
    liveheats_event_id VARCHAR(50),
    liveheats_division_id VARCHAR(50),
    division_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_event (pwa_event_id),
    INDEX idx_heat (heat_id),
    UNIQUE KEY unique_heat (source, heat_id)
)
```

### 4. PWA_IWT_HEAT_RESULTS (Heat-by-Heat Results)
**Records**: 793 heat results (344 PWA + 449 LiveHeats)

```sql
CREATE TABLE PWA_IWT_HEAT_RESULTS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    scraped_at DATETIME,
    pwa_event_id INT NOT NULL,
    pwa_year INT,
    pwa_event_name VARCHAR(255),
    pwa_division_code VARCHAR(50),
    sex VARCHAR(20),
    heat_id VARCHAR(100) NOT NULL,
    athlete_id VARCHAR(100),
    athlete_name VARCHAR(255),
    sail_number VARCHAR(50),
    place INT,
    result_total DECIMAL(10,2),
    win_by DECIMAL(10,2),
    needs DECIMAL(10,2),
    round VARCHAR(100),
    round_position INT,
    liveheats_event_id VARCHAR(50),
    liveheats_division_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_event (pwa_event_id),
    INDEX idx_heat (heat_id),
    INDEX idx_athlete (athlete_id),
    UNIQUE KEY unique_heat_athlete (source, heat_id, athlete_id)
)
```

### 5. PWA_IWT_HEAT_SCORES (Individual Wave Scores)
**Records**: 39,460 wave scores (33,223 PWA + 6,237 LiveHeats)

**Note**: Initial data load contained 80,862 records with 41,402 duplicates (due to multiple scraping runs). Duplicates were removed in January 2026, keeping the earliest scraped version of each record.

### 6. ATHLETES (Unified Athlete Profiles)
**Records**: 359 unified athletes

```sql
CREATE TABLE ATHLETES (
    id INT AUTO_INCREMENT PRIMARY KEY,
    primary_name VARCHAR(255) NOT NULL,
    pwa_name VARCHAR(255),
    liveheats_name VARCHAR(255),
    match_score INT,
    match_stage VARCHAR(50),
    year_of_birth INT,
    nationality VARCHAR(100),
    pwa_athlete_id VARCHAR(100),
    pwa_sail_number VARCHAR(50),
    pwa_profile_url TEXT,
    pwa_sponsors TEXT,
    pwa_nationality VARCHAR(100),
    pwa_year_of_birth INT,
    liveheats_athlete_id VARCHAR(100),
    liveheats_image_url TEXT,
    liveheats_dob DATE,
    liveheats_nationality VARCHAR(100),
    liveheats_year_of_birth INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_primary_name (primary_name),
    INDEX idx_nationality (nationality),
    INDEX idx_year_of_birth (year_of_birth)
)
```

### 7. ATHLETE_SOURCE_IDS (Source ID Mappings)
**Records**: 514 mappings (281 PWA + 233 LiveHeats)

```sql
CREATE TABLE ATHLETE_SOURCE_IDS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    athlete_id INT NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_source_id (source, source_id),
    FOREIGN KEY (athlete_id) REFERENCES ATHLETES(id) ON DELETE CASCADE,
    INDEX idx_athlete_id (athlete_id),
    INDEX idx_source (source)
)
```

### Database Views (For API)

#### ATHLETE_RESULTS_VIEW
Joins results with unified athlete profiles. **2,052 records**

#### ATHLETE_HEAT_RESULTS_VIEW
Joins heat results with athlete profiles. **793 records**

#### ATHLETE_SUMMARY_VIEW
Aggregated career statistics per athlete. **359 athletes**

```sql
CREATE TABLE PWA_IWT_HEAT_SCORES (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    scraped_at DATETIME,
    pwa_event_id INT NOT NULL,
    pwa_year INT,
    pwa_event_name VARCHAR(255),
    pwa_division_code VARCHAR(50),
    sex VARCHAR(20),
    heat_id VARCHAR(100) NOT NULL,
    athlete_id VARCHAR(100),
    athlete_name VARCHAR(255),
    sail_number VARCHAR(50),
    score DECIMAL(10,2),
    type VARCHAR(20),                    -- 'Wave' or 'Jump'
    counting BOOLEAN,                    -- TRUE if counts toward total
    modified_total DECIMAL(10,2),
    modifier TEXT,
    total_wave DECIMAL(10,2),
    total_jump DECIMAL(10,2),
    total_points DECIMAL(10,2),
    liveheats_event_id VARCHAR(50),
    liveheats_division_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_event (pwa_event_id),
    INDEX idx_heat (heat_id),
    INDEX idx_athlete (athlete_id),
    INDEX idx_counting (counting),
    UNIQUE KEY unique_heat_score (source, heat_id, athlete_id, score, type, counting)
)
```

---

## Complete Database Status

### Total Records in Database: **43,515 records**

| Table | PWA Records | LiveHeats Records | Total | Status |
|-------|-------------|-------------------|-------|--------|
| PWA_IWT_EVENTS | 118 | - | 118 | ✅ LOADED |
| PWA_IWT_RESULTS | 1,879 | 173 | 2,052 | ✅ LOADED |
| PWA_IWT_HEAT_PROGRESSION | 113 | 106 | 219 | ✅ LOADED |
| PWA_IWT_HEAT_RESULTS | 344 | 449 | 793 | ✅ LOADED |
| PWA_IWT_HEAT_SCORES | 33,223 | 6,237 | 39,460 | ✅ LOADED & DEDUPLICATED |
| ATHLETES | - | - | 359 | ✅ LOADED |
| ATHLETE_SOURCE_IDS | 281 | 233 | 514 | ✅ LOADED |
| **TOTAL** | **35,958** | **7,198** | **43,515** | ✅ COMPLETE |

### Database Views

| View | Records | Status |
|------|---------|--------|
| ATHLETE_RESULTS_VIEW | 2,052 | ✅ CREATED |
| ATHLETE_HEAT_RESULTS_VIEW | 793 | ✅ CREATED |
| ATHLETE_SUMMARY_VIEW | 359 | ✅ CREATED |

### Data Coverage by Year:
- **2025**: 431 final results (including Chile 5★, Sylt 7★, Aloha Classic 5★)
- **2024**: 393 results
- **2023**: 300 results
- **2022**: 112 results
- **2019**: 247 results
- **2018**: 181 results
- **2017**: 177 results
- **2016**: 211 results

---

## Data Collection Status

### ✅ Phase 1-3 COMPLETE (Data Collection & Integration)

**PWA Data Scrapers:**
- ✅ Event metadata scraper ([pwa_event_scraper.py](../../src/scrapers/pwa_event_scraper.py))
- ✅ Results scraper ([pwa_results_scraper.py](../../src/scrapers/pwa_results_scraper.py))
- ✅ Heat data scraper ([pwa_heat_scraper.py](../../src/scrapers/pwa_heat_scraper.py))

**LiveHeats Data Scrapers:**
- ✅ Matched results scraper ([scrape_liveheats_matched_results.py](../../src/scrapers/scrape_liveheats_matched_results.py))
- ✅ Heat data scraper ([scrape_liveheats_heat_data.py](../../src/scrapers/scrape_liveheats_heat_data.py))
- ✅ Event matching ([match_pwa_to_liveheats.py](../../src/scrapers/match_pwa_to_liveheats.py))

**Data Merge Scripts:**
- ✅ Wave results merger ([merge_wave_results.py](../../src/scrapers/merge_wave_results.py))
- ✅ Heat progression merger ([merge_heat_progression.py](../../src/scrapers/merge_heat_progression.py))
- ✅ Heat results merger ([merge_heat_results.py](../../src/scrapers/merge_heat_results.py))
- ✅ Heat scores merger ([merge_heat_scores.py](../../src/scrapers/merge_heat_scores.py))

**Database Scripts:**
- ✅ Event/result tables ([create_tables.py](../../src/database/create_tables.py)) - 5 tables
- ✅ Athlete tables ([create_athlete_tables.py](../../src/database/create_athlete_tables.py)) - 2 tables
- ✅ Database views ([create_views.py](../../src/database/create_views.py)) - 3 views
- ✅ Events loader ([load_pwa_events.py](../../src/database/load_pwa_events.py))
- ✅ Results loader ([load_wave_results.py](../../src/database/load_wave_results.py))
- ✅ Heat data loader ([load_all_heat_data.py](../../src/database/load_all_heat_data.py))
- ✅ Athletes loader ([load_athletes.py](../../src/database/load_athletes.py))

**API Application:**
- ✅ FastAPI app ([src/api/main.py](../../src/api/main.py))
- ✅ Database connection pooling ([src/api/database.py](../../src/api/database.py))
- ✅ Pydantic models ([src/api/models.py](../../src/api/models.py))
- ✅ Events routes ([src/api/routes/events.py](../../src/api/routes/events.py))
- ✅ Athletes routes ([src/api/routes/athletes.py](../../src/api/routes/athletes.py))
- ✅ Production deployment ([DEPLOYMENT.md](../../DEPLOYMENT.md))

### ✅ Phase 4 COMPLETE (Athlete Data Integration)
- ✅ Athlete profile scraping (PWA: 281, LiveHeats: 233)
- ✅ Fuzzy name matching system (match_score, match_stage)
- ✅ Unified athlete profiles (359 athletes)
- ✅ Source ID mapping table (514 mappings)
- ✅ Database views for API (ATHLETE_RESULTS_VIEW, ATHLETE_SUMMARY_VIEW, ATHLETE_HEAT_RESULTS_VIEW)
- ✅ Data quality reporting and validation

### ✅ Phase 5 COMPLETE (API Development)
- ✅ FastAPI application with database connection pooling
- ✅ Events endpoints with filtering and pagination
- ✅ Athletes endpoints (summary, results)
- ✅ Production deployment to Oracle Cloud VM
- ✅ HTTPS with Let's Encrypt (https://windsurf-world-tour-stats-api.duckdns.org)
- ✅ Nginx reverse proxy with Gunicorn
- ✅ Systemd service with auto-restart
- ✅ Interactive API documentation (/docs, /redoc)

### 📋 Phase 6-7 (Future)
- Automated update scripts for new events
- Scheduling/monitoring for regular scraping
- Frontend web application
- Data visualization dashboards
- Statistical analysis tools

---

## Data Sources

### 1. PWA (Professional Windsurfers Association)
- **Website**: https://www.pwaworldtour.com
- **Years**: 2016-2025
- **Technology**: Selenium (JavaScript-heavy site)
- **Data Format**: HTML scraping + XML/JSON APIs
- **Coverage**: 118 events, 1,879 results, 344 heat results, 33,223 scores (deduplicated)

#### PWA Data Endpoints:
- Events: `https://www.pwaworldtour.com/index.php?id=2337`
- Results: `https://www.pwaworldtour.com/index.php?id=4&tx_pwatour_event[...]`
- Heat XML: `https://www.pwaworldtour.com/fileadmin/live_ladder/live_ladder_{category_code}.xml`
- Heat Scores JSON: `https://www.pwaworldtour.com/fileadmin/live_score/{heat_id}.json`

### 2. Live Heats (IWT)
- **Website**: https://liveheats.com
- **Years**: 2023+ (recent events)
- **Technology**: GraphQL API
- **API Endpoint**: `https://liveheats.com/api/graphql`
- **Coverage**: 5 matched divisions, 173 results, 449 heat results, 6,237 scores (deduplicated)

#### Live Heats GraphQL Organization:
- Query organization: "WaveTour"
- Filter: `status: "results_published"`
- Typical 4-5 star PWA/IWT events

#### LiveHeats GraphQL Query Example:
```graphql
query getEventDivision($id: ID!) {
  eventDivision(id: $id) {
    id
    division { id name }
    heats {
      id round roundPosition
      result { athleteId total place rides }
    }
  }
}
```

---

## Example: Chile 2025 Complete Data

**Event**: 2025 Chile World Cup (5 stars)
**Status**: ALL DATA VERIFIED IN DATABASE ✅

| Data Type | Men | Women | Total |
|-----------|-----|-------|-------|
| Final Rankings | 59 | 18 | 77 |
| Heats | 49 | 14 | 63 |
| Heat Results | 194 | 52 | 246 |
| Wave Scores | 830 | 185 | 1,015 |

**Complete heat-by-heat progression tracked from Round 1 through Finals!**

---

## Important Notes

### PWA Scraping Notes
1. **Discipline Codes**:
   - `1` = Wave
   - `2` = Slalom
   - `3` = Freestyle

2. **Star Ratings**:
   - Range: 4★ to 7★ (focus on 4-5★ wave events)
   - Older events (pre-2022) often don't have star ratings

3. **Event Status Codes**:
   - `1` = Upcoming
   - `2` = In Progress
   - `3` = Completed

### LiveHeats Integration Notes
1. **Event Matching**:
   - Match by date, location, and star rating
   - Manual verification in matching report CSV
   - 5 divisions successfully matched and integrated

2. **Data Prioritization**:
   - When both sources have same event, use source with more data
   - LiveHeats typically has more complete recent event data (2023+)
   - PWA has historical data back to 2016

3. **Athlete IDs**:
   - LiveHeats uses numeric IDs
   - PWA uses "Name_Code" format
   - Both stored in unified schema for future matching

### Database Best Practices
1. Always test connection before running scripts
2. Use transactions for bulk inserts
3. Use `ON DUPLICATE KEY UPDATE` for upserts
4. Handle NULL/NaN values explicitly
5. Use batch processing (100-500 rows recommended)

### Development Workflow
1. Scrape raw data → `data/raw/`
2. Validate and inspect CSV
3. Merge data from multiple sources → `data/processed/`
4. Create/update database table schema
5. Load data with upsert logic
6. Verify data in database

---

## Common Commands

### Database Operations
```bash
# Test database connection
python test_db_connection.py

# Create/recreate all tables
cd src/database && python create_tables.py

# Load all data
cd src/database && python load_pwa_events.py
cd src/database && python load_wave_results.py
cd src/database && python load_all_heat_data.py

# Verify data
python verify_chile_complete_db.py
```

### Data Scraping & Merging
```bash
# Scrape PWA data
cd src/scrapers && python pwa_event_scraper.py
cd src/scrapers && python pwa_results_scraper.py
cd src/scrapers && python pwa_heat_scraper.py

# Scrape LiveHeats data
cd src/scrapers && python scrape_liveheats_matched_results.py
cd src/scrapers && python scrape_liveheats_heat_data.py

# Merge data
cd src/scrapers && python merge_wave_results.py
cd src/scrapers && python merge_heat_progression.py
cd src/scrapers && python merge_heat_results.py
cd src/scrapers && python merge_heat_scores.py
```

---

## Key Decisions Made

### 1. Database Driver
**Decision**: Use `mysql-connector-python` instead of `pyodbc`
**Reason**: Native MySQL driver, better compatibility, simpler installation

### 2. Connection Method
**Decision**: SSH tunnel to localhost
**Reason**: Secure connection to Oracle Cloud MySQL, standard practice

### 3. Dual-Source Strategy
**Decision**: Integrate both PWA and LiveHeats data
**Reason**:
- PWA provides historical data (2016-2025)
- LiveHeats provides more complete recent data (2023+)
- Combined coverage gives most complete dataset

### 4. Data Merging Strategy
**Decision**: Keep both sources, prioritize by completeness
**Reason**:
- No true overlaps (different heat IDs, event IDs)
- Both sources complement each other
- Source tracking allows validation

### 5. Five-Table Schema
**Decision**: Separate tables for events, results, and 3 heat data types
**Reason**:
- Clear data separation
- Efficient querying
- Scalable for future data types

---

## Next Steps (Prioritized)

### Immediate (Phase 6 - Enhanced Features):
1. Add remaining API endpoints (heats, heat results, scores)
2. Add athlete search and filtering capabilities
3. Implement head-to-head athlete comparisons
4. Create event timeline and statistics views
5. Add data export functionality (CSV, JSON)

### Short-term (Phase 7 - Frontend Application):
1. Design frontend web application architecture
2. Build athlete profile pages with career stats
3. Create event browsing and filtering UI
4. Develop heat-by-heat competition viewer
5. Add data visualization (charts, graphs, timelines)

### Long-term (Maintenance & Enhancement):
1. Automated update scripts for new events
2. Scheduling/monitoring for regular scraping
3. Advanced statistical analysis
4. Machine learning predictions
5. Mobile-responsive design

---

## Troubleshooting

### Connection Issues
**Problem**: Can't connect to database
**Solutions**:
1. Check SSH tunnel is running
2. Verify `.env` credentials are correct
3. Test with `test_db_connection.py`
4. Check port 3306 is forwarded correctly

### Data Loading Errors
**Problem**: SQL errors on INSERT
**Solutions**:
1. Handle NaN/None values explicitly with `pd.notna()`
2. Check data types match schema (VARCHAR lengths, DECIMAL precision)
3. Verify unique constraints (source + IDs)
4. Use batch processing to isolate problem records

### Scraper Issues
**Problem**: Selenium timeouts or missing data
**Solutions**:
1. Check website availability
2. Verify element selectors haven't changed
3. Increase timeout values
4. Use explicit waits instead of implicit

---

## Reference Files

### Core Scripts
- **Test Connection**: [test_db_connection.py](../../test_db_connection.py)
- **Create Tables**: [src/database/create_tables.py](../../src/database/create_tables.py)
- **Load All Heat Data**: [src/database/load_all_heat_data.py](../../src/database/load_all_heat_data.py)

### Data Files
- **Merged Results**: [data/processed/wave_results_merged.csv](../../data/processed/wave_results_merged.csv)
- **Merged Heat Progression**: [data/processed/heat_progression_merged.csv](../../data/processed/heat_progression_merged.csv)
- **Merged Heat Results**: [data/processed/heat_results_merged.csv](../../data/processed/heat_results_merged.csv)
- **Merged Heat Scores**: [data/processed/heat_scores_merged.csv](../../data/processed/heat_scores_merged.csv)

### Reports
- **PWA-LiveHeats Matching**: [data/reports/pwa_liveheats_matching_report_v2.csv](../../data/reports/pwa_liveheats_matching_report_v2.csv)

---

## Memory/Context for AI Assistants

- Always read screenshots automatically when user drops them
- Database requires SSH tunnel to Oracle MySQL Heatwave
- Use `mysql-connector-python` for all database operations
- PWA scrapers need Selenium (JavaScript-rendered pages)
- LiveHeats uses GraphQL API (requests library)
- CSV files are intermediates before database load
- Focus on wave discipline events (4-5 stars when available)
- Maintain `source` column for data traceability
- Handle NaN/None values explicitly in all data operations
- Use batch processing for database inserts (100-500 rows)
- Test database connection before running any DB scripts
- **All Phase 1-3 data collection is COMPLETE - focus on data quality now**

---

**Last Updated**: 2026-01-02 (Heat scores table deduplicated - 41,402 duplicates removed, 43,515 clean records in database, production API live)
