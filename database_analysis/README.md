# Database Analysis Scripts

This folder contains critical scripts for analyzing and validating the database.

## Scripts

### `test_db_connection.py`
**Purpose**: Test database connectivity
**Usage**: `python database_analysis/test_db_connection.py`
**When to use**: Before running any database operations to verify connection is working

### `analyze_data_quality.py`
**Purpose**: Comprehensive data quality analysis across all tables
**Usage**: `python database_analysis/analyze_data_quality.py`
**Output**:
- Console report with findings
- CSV reports in `data/reports/` directory
- Prioritized recommendations

**When to use**:
- After loading new data
- When investigating data issues
- Periodic health checks

### `find_missing_heat_data.py`
**Purpose**: Identify events that have final results but no heat-by-heat data
**Usage**: `python database_analysis/find_missing_heat_data.py`
**Output**: List of events missing heat progression/results/scores

**When to use**:
- Planning data collection efforts
- Identifying gaps in coverage
- Prioritizing scraping tasks

## Prerequisites

All scripts require:
- SSH tunnel to database running
- `.env` file configured with database credentials
- Python dependencies installed (`mysql-connector-python`, `python-dotenv`)

## Output Locations

Analysis reports are saved to:
- `data/reports/event_coverage_matrix_TIMESTAMP.csv`
- `data/reports/data_quality_issues_TIMESTAMP.csv`
