# Load Wave Results to Oracle MySQL Database

## Prerequisites

### 1. Start SSH Tunnel to Oracle Cloud
You must have an active SSH tunnel to your Oracle Cloud MySQL Heatwave instance.

**Command (example - adjust to your setup):**
```bash
ssh -L 3306:localhost:3306 your-oracle-cloud-server
```

Or use your preferred SSH client (PuTTY, etc.) to forward port 3306.

### 2. Verify .env Configuration
Ensure your `.env` file has these settings:
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jfa_heatwave_db
DB_USER=admin
DB_PASSWORD=your_password
```

---

## Step-by-Step Instructions

### Step 1: Test Database Connection
```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"
python test_db_connection.py
```

**Expected Output:**
```
[OK] Connection successful!
```

---

### Step 2: Create PWA_IWT_RESULTS Table

This will create (or recreate) the `PWA_IWT_RESULTS` table in your database.

**⚠️ WARNING:** This will **DROP** the existing table if it exists!

```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"
python src/database/create_tables.py
```

**Expected Output:**
```
[OK] PWA_IWT_EVENTS table created successfully
[OK] PWA_IWT_RESULTS table created successfully
[OK] All tables created successfully!
```

---

### Step 3: Load Merged Wave Results

This will load all 1,896 wave results from the merged CSV into the database.

```bash
cd "c:\Users\jackf\OneDrive\Documents\Projects\Windsurf World Tour Stats"
python src/database/load_wave_results.py
```

**Expected Output:**
```
[OK] Loaded 1896 records from CSV
Inserting 1896 records in 19 batches...
[OK] Database operations complete
[SUCCESS] Wave results loaded successfully!
```

---

## Table Schema: PWA_IWT_RESULTS

```sql
CREATE TABLE PWA_IWT_RESULTS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(50) NOT NULL,              -- 'PWA' or 'Live Heats'
    scraped_at DATETIME NOT NULL,
    event_id INT NOT NULL,
    year INT NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    division_label VARCHAR(100) NOT NULL,     -- e.g., 'Wave Men', 'Wave Women'
    division_code VARCHAR(50),                -- Division ID/code
    sex VARCHAR(20),                          -- 'Men' or 'Women'
    place VARCHAR(10) NOT NULL,               -- Placement (e.g., '1', '5', '9')
    athlete_name VARCHAR(255),                -- Full name
    sail_number VARCHAR(50),                  -- Sail number (e.g., 'G-44')
    athlete_id VARCHAR(50),                   -- Athlete ID (PWA or Live Heats)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes for performance
    INDEX idx_source (source),
    INDEX idx_event_id (event_id),
    INDEX idx_year (year),
    INDEX idx_sex (sex),
    INDEX idx_athlete_id (athlete_id),
    INDEX idx_athlete_name (athlete_name),

    -- Prevent duplicates
    UNIQUE KEY unique_result (source, event_id, division_code, athlete_id, place)
)
```

---

## Verify Data After Loading

### Connect to MySQL and run queries:

```sql
-- Total records
SELECT COUNT(*) FROM PWA_IWT_RESULTS;

-- Records by source
SELECT source, COUNT(*) as count
FROM PWA_IWT_RESULTS
GROUP BY source;

-- Records by year
SELECT year, COUNT(*) as count
FROM PWA_IWT_RESULTS
WHERE year > 0
GROUP BY year
ORDER BY year DESC;

-- Top athletes (by number of results)
SELECT athlete_name, COUNT(*) as events
FROM PWA_IWT_RESULTS
WHERE athlete_name != ''
GROUP BY athlete_name
ORDER BY events DESC
LIMIT 20;

-- Recent events
SELECT DISTINCT year, event_name, division_label
FROM PWA_IWT_RESULTS
WHERE year = 2025
ORDER BY event_name;
```

---

## Troubleshooting

### Error: "Can't connect to MySQL server on localhost:3306"
**Solution:** Start your SSH tunnel to Oracle Cloud server first.

### Error: "Access denied for user 'admin'"
**Solution:** Check your DB_PASSWORD in the `.env` file.

### Error: "Unknown database 'jfa_heatwave_db'"
**Solution:** Verify DB_NAME in `.env` matches your actual database name.

### Error: "Duplicate entry"
**Solution:** This is expected if re-running the load script. The script uses `ON DUPLICATE KEY UPDATE` to handle duplicates gracefully.

---

## Data Notes

1. **Live Heats Records**: May have empty `athlete_name` and `sail_number` fields due to API limitations. These can be populated later via athlete ID mapping.

2. **Duplicates**: Event 378 (2025 Sylt) appears in both PWA and Live Heats sources. The merge script prioritizes PWA data.

3. **Data Freshness**: Remember to re-run the scraping pipeline periodically to get new results:
   ```bash
   python src/scrapers/run_complete_results_pipeline.py
   python src/database/load_wave_results.py
   ```

---

## Quick Command Summary

```bash
# 1. Test connection (requires SSH tunnel active)
python test_db_connection.py

# 2. Create tables
python src/database/create_tables.py

# 3. Load data
python src/database/load_wave_results.py
```

---

**Last Updated:** 2025-10-20
