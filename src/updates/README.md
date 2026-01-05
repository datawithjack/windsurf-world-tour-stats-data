# PWA Daily Update System

Automated system for checking PWA website for new events and updates, then incrementally updating the database.

## Overview

The daily update system runs automatically every day at 2 AM UTC via GitHub Actions. It:

1. **Checks** for new/updated events (last 60 days)
2. **Scrapes** only the changed events (not full re-scrape)
3. **Validates** data quality (< 10% issues threshold)
4. **Updates** database automatically (using upserts)
5. **Notifies** via email with summary + GitHub issues on failure

## Components

### 1. `check_for_updates.py` - Event Update Checker

Identifies which PWA events need updating by comparing database records with current PWA website data.

**Usage:**
```bash
python src/updates/check_for_updates.py --lookback-days 60 --output data/staging/events_to_update.json
```

**Output:** `data/staging/events_to_update.json`
```json
{
  "timestamp": "2026-01-05T02:00:00Z",
  "total_events": 5,
  "events": [
    {
      "event_id": 1234,
      "event_name": "Chile 2025",
      "reason": "status_change",
      "old_status": 2,
      "new_status": 3
    }
  ]
}
```

### 2. `incremental_scraper.py` - Targeted Scraper

Scrapes only the events identified by check_for_updates.py using modified scrapers with event_ids filtering.

**Usage:**
```bash
python src/updates/incremental_scraper.py \
  --events-json data/staging/events_to_update.json \
  --output-dir data/staging
```

**Outputs:**
- `events_incremental.csv`
- `results_incremental.csv`
- `heat_progression_incremental.csv`
- `heat_results_incremental.csv`
- `heat_scores_incremental.csv`

### 3. `detect_changes.py` - Change Detector & Validator

Compares staged data with existing database records and validates data quality.

**Usage:**
```bash
python src/updates/detect_changes.py \
  --staging-dir data/staging \
  --output data/staging/change_report.json
```

**Quality Gate:**
- If validation issues > 10% of records → HALT and create GitHub issue
- Otherwise proceed to database update

**Output:** `data/staging/change_report.json`

### 4. `update_database.py` - Database Updater

Applies validated changes to database using existing loader logic with transaction safety.

**Usage:**
```bash
python src/updates/update_database.py \
  --staging-dir data/staging \
  --change-report data/staging/change_report.json \
  --output data/staging/update_log.json
```

**Features:**
- Transaction-based updates (rollback on error)
- Reuses existing upsert logic
- Logs before/after record counts

### 5. `generate_summary.py` - Summary Generator

Creates human-readable summary for email notifications and GitHub issues.

**Usage:**
```bash
python src/updates/generate_summary.py \
  --staging-dir data/staging \
  --output data/staging/update_summary.txt
```

## Modified Scrapers

All PWA scrapers now support event_ids filtering for incremental scraping:

### `pwa_event_scraper.py`
```python
scraper = PWAEventScraper(event_ids=[1234, 1235])  # Only scrape these events
```

### `pwa_results_scraper.py`
```python
scraper = PWAResultsScraper(events_df=filtered_df)  # Use DataFrame instead of CSV
```

### `pwa_heat_scraper.py`
```python
scraper = PWAHeatScraper(tracking_csv_path, event_ids=[1234, 1235])  # Filter by event IDs
```

## GitHub Actions Workflow

**File:** `.github/workflows/daily-update.yml`

**Schedule:** Daily at 2 AM UTC (cron: `0 2 * * *`)

**Manual Trigger:** Yes (workflow_dispatch)

### Required GitHub Secrets

Set these in your repository settings → Secrets and variables → Actions:

```
SSH_PRIVATE_KEY       # SSH private key for Oracle Cloud VM
SSH_HOST              # SSH host IP (e.g., 129.151.153.128)
DB_NAME               # jfa_heatwave_db
DB_USER               # admin
DB_PASSWORD           # Database password
EMAIL_USERNAME        # Gmail account for sending emails
EMAIL_PASSWORD        # Gmail app password
NOTIFICATION_EMAIL    # Email address to receive notifications
```

### Workflow Steps

1. **Setup**: Checkout, Python 3.11, install dependencies, Chromium
2. **SSH Tunnel**: Create tunnel to Oracle MySQL (localhost:3306)
3. **Check Updates**: Run `check_for_updates.py --lookback-days 60`
4. **Scrape**: Run `incremental_scraper.py` (only if events found)
5. **Validate**: Run `detect_changes.py` (enforce 10% quality gate)
6. **Update DB**: Run `update_database.py` (with transactions)
7. **Notify**: Email summary + create GitHub issue on failure
8. **Cleanup**: Kill SSH tunnel, upload artifacts

## Manual Testing

### Test Locally (Before Pushing)

```bash
# 1. Create SSH tunnel to database
ssh -L 3306:10.0.151.92:3306 -i ~/.ssh/ssh-key-2025-08-30.key ubuntu@129.151.153.128

# 2. Check for updates (test with last 7 days)
python src/updates/check_for_updates.py --lookback-days 7 --output data/staging/events_to_update.json

# 3. Review events_to_update.json
cat data/staging/events_to_update.json

# 4. Scrape (if events found)
python src/updates/incremental_scraper.py \
  --events-json data/staging/events_to_update.json \
  --output-dir data/staging

# 5. Validate changes
python src/updates/detect_changes.py \
  --staging-dir data/staging \
  --output data/staging/change_report.json

# 6. Review change report
cat data/staging/change_report.json

# 7. Update database (optional - test on dev DB first!)
# python src/updates/update_database.py \
#   --staging-dir data/staging \
#   --change-report data/staging/change_report.json \
#   --output data/staging/update_log.json

# 8. Generate summary
python src/updates/generate_summary.py \
  --staging-dir data/staging \
  --output data/staging/update_summary.txt

cat data/staging/update_summary.txt
```

### Test GitHub Actions Workflow

```bash
# Trigger workflow manually from GitHub UI
# Go to Actions → PWA Daily Update → Run workflow

# Or use GitHub CLI
gh workflow run daily-update.yml
```

## Performance

### Before (Full Scrape)
- **Time**: ~47 minutes for all 118 events
- **Frequency**: Manual only

### After (Incremental Updates)
- **Time**: ~5-10 minutes for 2-5 recent events
- **Frequency**: Automated daily
- **Efficiency**: **5x faster**

## Monitoring

### Daily Email Summary

You'll receive an email every day with:
- Number of events checked/updated
- New records added to database
- Any validation warnings
- Execution time
- Overall status (SUCCESS/FAILURE)

### GitHub Issues (Failures Only)

If the workflow fails:
- Automatic issue created with `daily-update` and `error` labels
- Includes summary, error logs, and link to workflow run
- Artifacts available for 30 days for debugging

### View Workflow Runs

```
https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

## Troubleshooting

### Issue: SSH tunnel fails to connect

**Solution:**
1. Check `SSH_PRIVATE_KEY` secret is correct
2. Verify `SSH_HOST` secret has correct IP
3. Check Oracle Cloud VM firewall rules

### Issue: Quality gate fails (>10% validation issues)

**Solution:**
1. Review `change_report.json` in workflow artifacts
2. Check PWA website for data anomalies
3. Fix validation rules if false positive

### Issue: Database update fails

**Solution:**
1. Check `update_log.json` in workflow artifacts
2. Verify database credentials in secrets
3. Check SSH tunnel is active
4. Review transaction rollback errors

## Future Enhancements

- [ ] Add LiveHeats update checks
- [ ] Implement heat data upsert logic (currently placeholder)
- [ ] Add retry logic for transient failures
- [ ] Create dashboard for update history
- [ ] Add Slack notifications option
