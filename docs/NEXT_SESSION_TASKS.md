# Next Session Task List

## Current Status (2025-11-14 Evening)

### ✅ Completed Today
1. Fixed Sylt 2025 cross-source duplicate data issue
2. Created manual LiveHeats matching template for 17 events
3. Matched 10 events (20 divisions) to LiveHeats
4. Scraped heat data from LiveHeats for matched events
5. Merged new data with existing LiveHeats data
6. Loaded merged data to database
7. Ran data quality analysis

### 🎯 Results Achieved
- **Reduced events missing heat data from 32 → 4** (87% improvement!)
- **Fixed Sylt cross-source issue** (removed LiveHeats duplicates, kept PWA)
- **Added complete heat data for 15 events** from 2023-2025

---

## 🔥 Priority Tasks for Next Session

### 1. Investigate Gran Canaria/Tenerife PWA Heat Data Issue
**Problem:** These events have PWA heat SCORES but no HEAT RESULTS/PROGRESSION

**Affected Events:**
- 2025 Gran Canaria (374): 2,307 scores, 0 heat results ❌
- 2024 Gran Canaria (357): 2,156 scores, 0 heat results ❌
- 2024 Tenerife (358): 1,750 scores, 0 heat results ❌
- 2023 Gran Canaria (338): 2,374 scores, 0 heat results ❌

**Action Items:**
- [ ] Check PWA heat scraper logs for these events
- [ ] Verify if XML ladder files exist for these events
- [ ] Check if XML format is different/failed to parse
- [ ] Look at PWA website to see if heat progression is visible
- [ ] If XML files exist but failed to parse, fix parser
- [ ] Re-run PWA heat scraper for these specific events

**Files to Check:**
- `src/scrapers/pwa_heat_scraper.py` (lines 200-300 - XML parsing)
- `data/raw/pwa/pwa_heat_structure.csv`
- `data/raw/pwa/pwa_heat_results.csv`

---

### 2. Fill In Remaining LiveHeats Matches (Optional)

**4 events still missing heat data:**
1. 2023 Omaezaki (345) - Check if on LiveHeats
2. 2023 Chile (346) - Check if on LiveHeats
3. 2023 Aloha Classic (348) - Check if on LiveHeats
4. 2016 Gran Canaria (250) - Old event, likely no data

**Action Items:**
- [ ] Check LiveHeats website manually for 2023 events
- [ ] If found, add to `data/reports/liveheats_manual_matching_template.csv`
- [ ] Re-run `scrape_new_liveheats_events.py`
- [ ] Merge and load as before

---

### 3. Data Quality Improvements (Lower Priority)

#### 3a. Populate Missing Athlete Names for LiveHeats Results
**Issue:** LiveHeats results have athlete IDs but no names (100% missing)

**Action:**
- [ ] Create script to populate names from ATHLETES table via ATHLETE_SOURCE_IDS mapping
- [ ] Update PWA_IWT_RESULTS where source='Live Heats' and athlete_name is NULL

#### 3b. Classify NULL Score Types
**Issue:** 5,577 heat scores have NULL type (should be 'Wave' or 'Jump')

**Action:**
- [ ] Analyze score patterns to determine classification rules
- [ ] Create script to update PWA_IWT_HEAT_SCORES.type field
- [ ] Validate classification accuracy

#### 3c. Populate NULL Division Codes
**Issue:** 96%+ of LiveHeats heat data has NULL division codes

**Decision Needed:**
- Is this acceptable? (LiveHeats doesn't provide division codes)
- Or should we map from division names → division codes?

---

## 🗂️ Files Modified Today

### Created Files:
- `fix_sylt_duplicates.py` - Fixed Sylt cross-source issue
- `match_liveheats_events_2023_2025.py` - Automated matching script (didn't work due to API changes)
- `check_liveheats_events.py` - Event availability checker
- `explore_liveheats_organizations.py` - GraphQL schema exploration
- `find_liveheats_matches.py` - Fuzzy matching attempt
- `scrape_new_liveheats_events.py` - Wrapper for LiveHeats scraper
- `MANUAL_MATCHING_INSTRUCTIONS.md` - Guide for manual matching
- `NEXT_SESSION_TASKS.md` - This file

### Modified Files:
- `src/scrapers/pwa_heat_scraper.py` (line 97-104) - Changed year filter from `>= 2023` to `>= 2016`
- `data/reports/liveheats_manual_matching_template.csv` - Filled in 10 events with LiveHeats IDs

### Database Changes:
- Deleted Sylt 2025 LiveHeats duplicates (31 results, 31 heat results, 62 scores)
- Updated Sylt 2025 event source from 'Live Heats' → 'PWA'
- Loaded heat data for 10 new events (thousands of new records)

---

## 📊 Current Database Stats

### Events with Complete Heat Data:
- **2025**: Chile (370), Tenerife (376), Sylt (378), Aloha (380), Margaret River (385), Omaezaki (386), Puerto Rico (387), Maui (388)
- **2024**: Omaezaki (352), Chile (354), Gran Canaria (357), Tenerife (358), Peru (360), Sylt (363), Aloha (365)
- **2023**: Sylt (342), Peru (347), Fiji (349)
- **2021**: Marignane (322)
- **2016**: La Torche (257)

**Total: 20 events with heat data**

### Events with SCORES but NO HEAT RESULTS:
- 2025 Gran Canaria (374): 2,307 scores
- 2024 Gran Canaria (357): 2,156 scores
- 2024 Tenerife (358): 1,750 scores
- 2023 Gran Canaria (338): 2,374 scores

**This is the high-value target for next session!**

---

## 🚀 Quick Start Commands for Next Session

### Check PWA Heat Scraper for Gran Canaria/Tenerife
```bash
cd "C:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"

# Re-run scraper for specific events to see logs
python src/scrapers/pwa_heat_scraper.py
```

### Check if XML ladder files exist
```bash
# Look at PWA website for event 374 (2025 Gran Canaria)
# https://www.pwaworldtour.com/index.php?id=38&tx_pwaevent_pi1%5BshowUid%5D=374
```

### Verify current database state
```bash
python analyze_data_quality.py
```

---

## 💡 Key Insights from Today

1. **LiveHeats GraphQL API changed** - Organization field is now `organisation` (British spelling)
2. **Manual matching is more reliable** than automated matching for LiveHeats
3. **Cross-source events need careful handling** - Sylt had data from both PWA and LiveHeats
4. **PWA heat scraper is incomplete** - Gets scores but sometimes misses heat structure
5. **Gran Canaria/Tenerife have heat scores without structure** - This is unusual and worth investigating

---

## 📝 Notes

- SSH tunnel must be running to access database
- PWA heat scraper takes ~10 minutes to run (52 events)
- LiveHeats scraper works well when event/division IDs are provided
- Merge scripts handle duplicates via UPSERT logic
- Data quality analysis should be run after any data changes

---

**Next session goal: Get complete heat data for Gran Canaria and Tenerife events (4 events, ~8,500 scores already exist!)**
