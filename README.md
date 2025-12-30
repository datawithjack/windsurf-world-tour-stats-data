# Windsurf World Tour Stats

A comprehensive database and API for professional windsurf wave event results from PWA (Professional Windsurfers Association) and IWT/Live Heats (2016-2025).

## Project Status

**Phase 5 COMPLETE** - Production API deployed at https://windsurf-world-tour-stats-api.duckdns.org

**Latest Update (Dec 2025)**: API reliability improvements - optimized connection pooling, automatic retry logic, and increased timeouts for better performance and stability.

### Current Coverage
- **7,869 total records** across all tables
- **55 wave events** from 2016-2025
- **2,052 final results** (1,879 PWA + 173 LiveHeats)
- **35 events with complete heat-by-heat data**
- **359 unified athlete profiles** with cross-source matching
- **3,814 individual wave scores**

## Quick Start

### Prerequisites
- Python 3.9+
- SSH tunnel to Oracle MySQL Heatwave database
- `.env` file with database credentials

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Test database connection
python database_analysis/test_db_connection.py

# Run API locally
uvicorn src.api.main:app --reload --port 8001
```

Visit http://localhost:8001/docs for interactive API documentation.

## Project Structure

```
Windsurf World Tour Stats/
├── src/                          # Source code
│   ├── api/                      # FastAPI application (PRODUCTION)
│   ├── scrapers/                 # Web scrapers for PWA and LiveHeats
│   ├── database/                 # Database schema and loading scripts
│   └── cleaning/                 # Data cleaning scripts
├── data/                         # Data files
│   ├── raw/                      # Raw scraped data (CSV)
│   ├── processed/                # Merged/cleaned data (CSV)
│   └── reports/                  # Data quality reports
├── database_analysis/            # Database analysis & validation scripts
├── docs/                         # All project documentation
├── deployment/                   # Production deployment configs
├── old_scripts/                  # Legacy/reference scripts
└── logs/                         # Application logs
```

## Documentation

All documentation is in the `docs/` folder:

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Quick start guide
- **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** - Detailed project roadmap
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[docs/API_QUICK_START.md](docs/API_QUICK_START.md)** - API development guide

## Live API Endpoints

Base URL: `https://windsurf-world-tour-stats-api.duckdns.org`

### Events
- `GET /api/v1/events` - List events with filtering
- `GET /api/v1/events/{id}` - Get single event

### Athletes
- `GET /api/v1/athletes/summary` - Athlete career summaries
- `GET /api/v1/athletes/{id}/summary` - Specific athlete summary
- `GET /api/v1/athletes/results` - Competition results with profiles

### Documentation
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation

## Database Schema

### Core Tables
1. **PWA_IWT_EVENTS** (118 events)
2. **PWA_IWT_RESULTS** (2,052 final rankings)
3. **PWA_IWT_HEAT_PROGRESSION** (219 heat structures)
4. **PWA_IWT_HEAT_RESULTS** (793 heat results)
5. **PWA_IWT_HEAT_SCORES** (3,814 wave scores)
6. **ATHLETES** (359 unified athlete profiles)
7. **ATHLETE_SOURCE_IDS** (514 source ID mappings)

### Database Views
- **ATHLETE_RESULTS_VIEW** - Results joined with athlete profiles
- **ATHLETE_HEAT_RESULTS_VIEW** - Heat results with athlete profiles
- **ATHLETE_SUMMARY_VIEW** - Career statistics per athlete

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for detailed schema documentation.

## Development Workflow

### 1. Data Collection
```bash
# Scrape PWA data
cd src/scrapers
python pwa_event_scraper.py
python pwa_results_scraper.py
python pwa_heat_scraper.py

# Scrape LiveHeats data (with manual matching)
python scrape_liveheats_matched_results.py
python scrape_liveheats_heat_data.py
```

### 2. Data Processing
```bash
# Merge data from both sources
cd src/scrapers
python merge_wave_results.py
python merge_heat_progression.py
python merge_heat_results.py
python merge_heat_scores.py
```

### 3. Database Loading
```bash
cd src/database
python create_tables.py           # Create schema
python load_pwa_events.py         # Load events
python load_wave_results.py       # Load results
python load_all_heat_data.py      # Load heat data
python load_athletes.py           # Load athlete profiles
```

### 4. Quality Analysis
```bash
python database_analysis/analyze_data_quality.py
python database_analysis/find_missing_heat_data.py
```

## Data Sources

### PWA (Professional Windsurfers Association)
- Website: https://www.pwaworldtour.com
- Years: 2016-2025
- Technology: Selenium (JavaScript-rendered pages)
- Coverage: 118 events, 1,879 results, 1,901 heat scores

### LiveHeats (IWT)
- Website: https://liveheats.com
- Years: 2023-2025
- Technology: GraphQL API
- Coverage: 5 matched divisions, 173 results, 1,913 scores

## Contributing

When working on the project:

1. **Keep repository clean** - Use `database_analysis/` for analysis scripts, `docs/` for documentation
2. **Test database connection** before operations
3. **Run data quality analysis** after loading new data
4. **Update documentation** when adding features
5. **Use the tracking CSV files** to avoid re-scraping data

## Next Steps

See [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) for current priorities.

### Planned Features (Phase 6-7)
- [ ] Automated update scripts for new events
- [ ] Frontend web application
- [ ] Advanced statistical analysis
- [ ] Head-to-head athlete comparisons
- [ ] Data visualization dashboards

## Contact & Support

For issues, questions, or contributions, please refer to the project documentation in the `docs/` folder.

---

**Last Updated**: 2025-11-14 (After Phase 5 completion - Production API live with 7,869 database records)
