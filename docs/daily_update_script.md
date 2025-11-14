# Daily Update Script - Design & Recommendations

## Purpose
Automatically scrape and update windsurf competition data on a daily basis to keep the database current with new events, results, and heat scores.

---

## Architecture Overview

### Update Flow
```
1. Check for new/updated events
2. Scrape new data from sources
3. Validate & clean data
4. Merge with existing data
5. Load into database
6. Run data quality checks
7. Log results & send alerts
```

---

## Critical Lessons from Cross-Source Issues

### Root Cause of Recent Issues

The 3 critical cross-source mismatches (Chile, Sylt, Aloha) happened because:

1. **PWA scraper ran first** → Created event metadata with `source='PWA'`
2. **LiveHeats had better data** → Results/heats scraped from LiveHeats
3. **Source fields didn't match** → Broke joins in views/APIs

### Design Principle for Daily Updates

> **The `source` field is for data lineage ONLY, not for joining**

**Implications:**
- Source tracks WHERE data came from (audit trail)
- Source should NEVER be used as a foreign key constraint
- Business logic must work regardless of source

---

## Recommended Update Script Design

### Phase 1: Source-Agnostic Event Registry

**Problem**: Multiple sources may have the same event with different source values

**Solution**: Create an event matching/deduplication layer

```python
# Pseudo-code
def match_events(pwa_events, liveheats_events):
    """
    Match events across sources by:
    - Date range overlap
    - Location match
    - Name similarity (fuzzy matching)
    """
    matched_events = []

    for pwa_event in pwa_events:
        for lh_event in liveheats_events:
            if is_same_event(pwa_event, lh_event):
                # Merge into unified event record
                unified = {
                    'event_id': pwa_event.id,  # Use PWA ID as canonical
                    'pwa_data': pwa_event,
                    'liveheats_data': lh_event,
                    'primary_source': determine_best_source(pwa_event, lh_event)
                }
                matched_events.append(unified)

    return matched_events
```

### Phase 2: Data Priority Rules

**Problem**: When both sources have the same data, which do we use?

**Solution**: Define explicit priority rules

```python
SOURCE_PRIORITY = {
    # Event metadata
    'event_name': 'PWA',          # PWA has official names
    'event_dates': 'PWA',         # PWA has accurate dates
    'event_location': 'PWA',      # PWA has country codes
    'stars': 'PWA',               # PWA has star ratings

    # Competition data
    'final_results': 'both',      # Merge both sources (they may differ)
    'heat_structure': 'LiveHeats', # LiveHeats has detailed brackets
    'heat_scores': 'LiveHeats',   # LiveHeats has individual scores
    'wave_classification': 'PWA', # PWA classifies wave types better
}
```

### Phase 3: Smart Source Assignment

**Problem**: Event source must match data source or joins break

**Solution**: Set event source to match ACTUAL data source

```python
def determine_event_source(event_data):
    """
    Determine which source should be recorded for the event
    based on where the BULK of the data comes from
    """

    # Count data completeness by source
    scores = {
        'PWA': 0,
        'Live Heats': 0
    }

    # Weight different data types
    if event_data.get('pwa_results'):
        scores['PWA'] += len(event_data['pwa_results']) * 1

    if event_data.get('liveheats_results'):
        scores['Live Heats'] += len(event_data['liveheats_results']) * 1

    if event_data.get('pwa_heat_scores'):
        scores['PWA'] += len(event_data['pwa_heat_scores']) * 10  # Scores weighted heavily

    if event_data.get('liveheats_heat_scores'):
        scores['Live Heats'] += len(event_data['liveheats_heat_scores']) * 10

    # Return source with highest score
    primary_source = max(scores, key=scores.get)

    return primary_source
```

**Result**: Event source automatically aligns with data source, preventing cross-source mismatches

---

## Daily Update Script Structure

### File: `src/update/daily_update.py`

```python
"""
Daily Update Script - Fetch and load latest windsurf competition data

Run daily via cron/scheduler to keep database current
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Configure logging
logging.basicConfig(
    filename=f'logs/daily_update_{datetime.now():%Y%m%d}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DailyUpdateOrchestrator:
    """Coordinates daily data updates from all sources"""

    def __init__(self):
        self.pwa_scraper = PWAEventScraper()
        self.liveheats_scraper = LiveHeatsGraphQLClient()
        self.data_merger = DataMerger()
        self.db_loader = DatabaseLoader()

    def run_daily_update(self):
        """Main update flow"""
        logging.info("="*80)
        logging.info("STARTING DAILY UPDATE")
        logging.info("="*80)

        try:
            # Step 1: Fetch recent events (last 30 days + upcoming)
            recent_events = self.fetch_recent_events()

            # Step 2: Match events across sources
            matched_events = self.match_cross_source_events(recent_events)

            # Step 3: Scrape details for each event
            for event in matched_events:
                self.update_event(event)

            # Step 4: Run data quality checks
            issues = self.run_quality_checks()

            # Step 5: Log summary
            self.log_summary(matched_events, issues)

            logging.info("Daily update completed successfully")

        except Exception as e:
            logging.error(f"Daily update failed: {e}", exc_info=True)
            self.send_alert(f"Daily update failed: {e}")

    def fetch_recent_events(self) -> Dict:
        """Fetch events from last 30 days + next 60 days"""
        date_from = datetime.now() - timedelta(days=30)
        date_to = datetime.now() + timedelta(days=60)

        logging.info(f"Fetching events from {date_from:%Y-%m-%d} to {date_to:%Y-%m-%d}")

        pwa_events = self.pwa_scraper.get_events(date_from, date_to)
        lh_events = self.liveheats_scraper.get_events(date_from, date_to)

        logging.info(f"  PWA: {len(pwa_events)} events")
        logging.info(f"  LiveHeats: {len(lh_events)} events")

        return {
            'pwa': pwa_events,
            'liveheats': lh_events
        }

    def match_cross_source_events(self, events: Dict) -> List:
        """
        Match the same event across PWA and LiveHeats

        CRITICAL: This prevents cross-source mismatches
        """
        logging.info("Matching events across sources...")

        matched = []

        for pwa_event in events['pwa']:
            # Try to find corresponding LiveHeats event
            lh_match = self.find_liveheats_match(pwa_event, events['liveheats'])

            if lh_match:
                # Merge metadata + data
                unified = self.merge_event_data(pwa_event, lh_match)

                # CRITICAL: Determine primary source based on data completeness
                unified['primary_source'] = self.determine_primary_source(unified)

                matched.append(unified)
                logging.info(f"  Matched: {pwa_event.name} (primary source: {unified['primary_source']})")
            else:
                # PWA-only event
                matched.append({
                    'event_id': pwa_event.id,
                    'primary_source': 'PWA',
                    'pwa_data': pwa_event,
                    'liveheats_data': None
                })

        # Add LiveHeats-only events
        for lh_event in events['liveheats']:
            if not self.is_already_matched(lh_event, matched):
                matched.append({
                    'event_id': lh_event.id,
                    'primary_source': 'Live Heats',
                    'pwa_data': None,
                    'liveheats_data': lh_event
                })

        logging.info(f"  Total matched events: {len(matched)}")
        return matched

    def update_event(self, event: Dict):
        """Update all data for a single event"""
        event_id = event['event_id']
        primary_source = event['primary_source']

        logging.info(f"Updating event {event_id} (source: {primary_source})...")

        # Upsert event metadata with PRIMARY SOURCE
        self.db_loader.upsert_event(
            event_id=event_id,
            source=primary_source,  # CRITICAL: Use determined source
            data=event['pwa_data'] or event['liveheats_data']
        )

        # Load results from all sources
        if event['pwa_data'] and event['pwa_data'].has_results:
            self.load_results(event_id, 'PWA', event['pwa_data'])

        if event['liveheats_data'] and event['liveheats_data'].has_results:
            self.load_results(event_id, 'Live Heats', event['liveheats_data'])

        # Load heat data (usually from LiveHeats)
        if event['liveheats_data'] and event['liveheats_data'].has_heats:
            self.load_heat_data(event_id, event['liveheats_data'])

    def determine_primary_source(self, event: Dict) -> str:
        """
        Determine which source should be the PRIMARY source for this event

        CRITICAL: This prevents cross-source mismatch issues
        """
        pwa = event.get('pwa_data')
        lh = event.get('liveheats_data')

        if not pwa:
            return 'Live Heats'
        if not lh:
            return 'PWA'

        # Score data completeness
        score_pwa = 0
        score_lh = 0

        # Results
        if pwa.get('results'):
            score_pwa += len(pwa['results'])
        if lh.get('results'):
            score_lh += len(lh['results'])

        # Heat data (heavily weighted)
        if pwa.get('heat_scores'):
            score_pwa += len(pwa['heat_scores']) * 10
        if lh.get('heat_scores'):
            score_lh += len(lh['heat_scores']) * 10

        # Return source with more complete data
        return 'Live Heats' if score_lh > score_pwa else 'PWA'

    def run_quality_checks(self) -> List:
        """
        Run data quality checks after update

        Catches issues early before they affect users
        """
        logging.info("Running data quality checks...")

        issues = []

        # Check 1: Cross-source mismatches
        cursor.execute("""
            SELECT e.event_id, e.source as event_source,
                   GROUP_CONCAT(DISTINCT r.source) as result_sources
            FROM PWA_IWT_EVENTS e
            INNER JOIN PWA_IWT_RESULTS r ON e.event_id = r.event_id
            GROUP BY e.event_id, e.source
            HAVING event_source NOT IN (result_sources)
        """)

        mismatches = cursor.fetchall()
        if mismatches:
            for event_id, event_src, result_src in mismatches:
                issue = f"Event {event_id}: source mismatch ({event_src} vs {result_src})"
                issues.append(issue)
                logging.warning(issue)

        # Check 2: Events with results but no heat data
        # Check 3: Missing athlete mappings
        # ... etc

        if issues:
            logging.warning(f"Found {len(issues)} data quality issues")
        else:
            logging.info("All quality checks passed")

        return issues

    def log_summary(self, events: List, issues: List):
        """Log daily update summary"""
        logging.info("="*80)
        logging.info("DAILY UPDATE SUMMARY")
        logging.info("="*80)
        logging.info(f"  Events processed: {len(events)}")
        logging.info(f"  Data quality issues: {len(issues)}")

        if issues:
            logging.info("\nIssues found:")
            for issue in issues:
                logging.info(f"  - {issue}")
```

---

## Key Recommendations for Daily Updates

### 1. Event Matching Strategy

**Matching Criteria (in priority order):**
1. **Exact event_id match** (if LiveHeats uses PWA IDs)
2. **Date range overlap** (±3 days)
3. **Location match** (country code)
4. **Name similarity** (fuzzy matching with 80% threshold)

**Implementation:**
```python
def is_same_event(pwa_event, lh_event):
    """Determine if two events from different sources are the same"""

    # Date overlap?
    date_overlap = (
        pwa_event.start_date <= lh_event.end_date and
        pwa_event.end_date >= lh_event.start_date
    )

    # Location match?
    location_match = pwa_event.country_code == lh_event.country_code

    # Name similarity?
    name_similarity = fuzz.ratio(pwa_event.name, lh_event.name)

    # Consider it a match if 2/3 criteria met
    score = sum([date_overlap, location_match, name_similarity > 80])
    return score >= 2
```

### 2. Data Deduplication

**Problem**: Same event may have results from both PWA and LiveHeats

**Solution**: Define merge strategy

```python
def merge_results(pwa_results, lh_results):
    """
    Merge results from both sources

    Strategy: Prefer LiveHeats if available (more complete),
              but keep PWA as backup
    """

    # Group by athlete
    by_athlete = {}

    for result in pwa_results:
        athlete_key = result.athlete_id
        by_athlete[athlete_key] = {
            'pwa': result,
            'liveheats': None,
            'primary': 'PWA'
        }

    for result in lh_results:
        athlete_key = result.athlete_id

        if athlete_key in by_athlete:
            # Both sources have this athlete - use LiveHeats
            by_athlete[athlete_key]['liveheats'] = result
            by_athlete[athlete_key]['primary'] = 'Live Heats'
        else:
            # Only LiveHeats has this athlete
            by_athlete[athlete_key] = {
                'pwa': None,
                'liveheats': result,
                'primary': 'Live Heats'
            }

    # Return merged results
    return [data[data['primary'].lower()] for data in by_athlete.values()]
```

### 3. Source Assignment Best Practices

**Rule 1**: Event source = source of MAJORITY data
```python
# If 90% of data is LiveHeats, set source='Live Heats'
# If 60% PWA / 40% LiveHeats, set source='PWA'
```

**Rule 2**: Update source if data composition changes
```python
# Event initially had PWA results only → source='PWA'
# Later LiveHeats adds heat scores → update to source='Live Heats'
```

**Rule 3**: Document source in metadata
```python
event_metadata = {
    'primary_source': 'Live Heats',
    'secondary_sources': ['PWA'],
    'data_breakdown': {
        'results_source': 'Live Heats',
        'heats_source': 'Live Heats',
        'metadata_source': 'PWA'
    }
}
```

### 4. Error Handling & Alerts

**Critical Errors** (send immediate alert):
- Cross-source mismatch detected after update
- Event with results but source='PWA' and data from LiveHeats
- Database constraint violations

**Warnings** (log for review):
- Event without heat data
- Athlete without unified mapping
- Missing division codes

**Monitoring Queries:**
```sql
-- Check for cross-source mismatches
SELECT e.event_id, e.source, GROUP_CONCAT(DISTINCT r.source)
FROM PWA_IWT_EVENTS e
INNER JOIN PWA_IWT_RESULTS r ON e.event_id = r.event_id
GROUP BY e.event_id, e.source
HAVING e.source NOT IN (r.source);

-- Check for orphaned athletes
SELECT DISTINCT r.athlete_id
FROM PWA_IWT_RESULTS r
LEFT JOIN ATHLETE_SOURCE_IDS asi
  ON r.source = asi.source
  AND r.athlete_id = asi.source_id
WHERE asi.athlete_id IS NULL;
```

---

## Scheduling & Deployment

### Recommended Schedule

```bash
# Cron job (runs at 2 AM daily)
0 2 * * * cd /path/to/project && python src/update/daily_update.py

# Or use systemd timer
[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true
```

### Environment Setup

```bash
# .env.production
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jfa_heatwave_db
DB_USER=updater_user
DB_PASSWORD=***

# Alert settings
ALERT_EMAIL=your@email.com
ALERT_WEBHOOK=https://hooks.slack.com/...

# Scraping settings
PWA_TIMEOUT=60
LIVEHEATS_RATE_LIMIT=10  # requests per minute
```

---

## Testing Strategy

### Before Deploying Daily Updates

1. **Dry Run Mode**
   ```python
   def run_daily_update(dry_run=True):
       if dry_run:
           logging.info("[DRY RUN] Would update X events...")
           # Don't actually write to database
   ```

2. **Validate Against Known Good State**
   ```python
   # Run update on test database first
   # Compare results with production
   # Ensure no data loss or corruption
   ```

3. **Monitor First Week Closely**
   - Check logs daily
   - Verify data quality reports
   - Watch for cross-source mismatches

---

## Summary: Preventing Future Cross-Source Issues

### ✅ DO:
1. **Match events across sources before scraping**
2. **Determine primary source based on data completeness**
3. **Set `PWA_IWT_EVENTS.source` to match primary data source**
4. **Run data quality checks after each update**
5. **Log all source assignments for audit trail**

### ❌ DON'T:
1. **Use source as a JOIN key** (use event_id + athlete_id only)
2. **Assume source='PWA' means all data is from PWA**
3. **Scrape sources independently** (match first, then scrape)
4. **Let event metadata source differ from data source**

### 🎯 Goal:
**Source field tracks data lineage for auditing, but NEVER constrains business logic or data relationships**

---

## Files to Create

```
src/update/
├── daily_update.py              # Main orchestrator
├── event_matcher.py             # Cross-source event matching
├── data_merger.py               # Merge strategies for duplicate data
├── quality_checks.py            # Post-update validation
└── alerts.py                    # Notification system

logs/
└── daily_update_YYYYMMDD.log    # Daily update logs

config/
└── update_config.yaml           # Configuration (thresholds, priorities)
```

---

**Last Updated**: 2025-11-14 (After fixing cross-source mismatch issues)
