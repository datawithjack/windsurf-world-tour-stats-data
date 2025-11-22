# Critical Data Quality Issues - Deep Dive Summary

## Overview
3 events have **cross-source mismatches** where event metadata comes from PWA but actual competition data (results, heats, scores) comes from LiveHeats.

---

## The 3 Affected Events

### 1. **Chile 2025 World Cup** (Event ID: 370)
- **Event metadata source**: PWA
- **Results source**: Live Heats (77 results, 2 divisions)
- **Heat data source**: Live Heats (1,015 scores, 63 heats)
- **Impact**: ALL data is from LiveHeats except event metadata

### 2. **Sylt 2025 Grand Slam** (Event ID: 378)
- **Event metadata source**: PWA
- **Results sources**: MIXED - LiveHeats (31 results) + PWA (9 results)
- **Heat data sources**: MIXED - Both LiveHeats and PWA data exists
- **Impact**: This is a DUAL-SOURCE event with data from both platforms
- **Problem**: 9 PWA results can't join to heat data when source matching is required

### 3. **Aloha Classic 2025** (Event ID: 380)
- **Event metadata source**: PWA
- **Results source**: Live Heats (65 results, 2 divisions)
- **Heat data source**: Live Heats (867 scores, 42 heats)
- **Impact**: ALL data is from LiveHeats except event metadata

---

## Root Cause Analysis

### Why does this happen?

1. **PWA scraper runs first** → Creates event metadata with `source='PWA'`
2. **LiveHeats has more complete data** → Results and heat scores come from LiveHeats with `source='Live Heats'`
3. **Source field becomes a JOIN key** → Views/APIs require source to match, breaking the relationship

### The Real Problem

**The `source` field serves TWO conflicting purposes:**
- ✅ **Data lineage** (where did this data come from?)
- ❌ **Foreign key** (used to join tables)

When used as a foreign key, it breaks joins for legitimate cross-source scenarios.

---

## Proposed Solutions

### Option 1: Update Event Metadata Source (Quick Database Fix)

**What**: Change `PWA_IWT_EVENTS.source` to match the primary data source

```sql
-- Fix the 3 affected events
UPDATE PWA_IWT_EVENTS
SET source = 'Live Heats'
WHERE event_id IN (370, 378, 380);
```

**Pros:**
- Simple 1-line SQL fix
- Aligns metadata with actual data source
- Maintains source field as tracking mechanism

**Cons:**
- Loses historical metadata about original scrape source
- Need to repeat for future cross-source events
- Doesn't solve the architectural issue

**Recommendation**: ✅ **Do this as immediate hotfix**

---

### Option 2: Remove Source from JOIN Logic (Architecture Fix)

**What**: Don't require `source` to match when joining tables

**Before (Breaks):**
```sql
LEFT JOIN PWA_IWT_HEAT_RESULTS hr
    ON r.source = hr.source              -- ❌ Requires same source
    AND r.event_id = hr.pwa_event_id
    AND r.athlete_id = hr.athlete_id
```

**After (Works):**
```sql
LEFT JOIN PWA_IWT_HEAT_RESULTS hr
    ON r.event_id = hr.pwa_event_id      -- ✅ Join on business keys only
    AND r.athlete_id = hr.athlete_id
```

**Pros:**
- Handles ALL cross-source scenarios automatically
- No need to update event metadata
- More resilient to future data patterns
- `source` remains pure data lineage field

**Cons:**
- Could cause duplicates if same event truly exists in both sources (very rare)
- Need to update all views/queries that do source joins

**Recommendation**: ✅ **Do this as permanent architectural fix**

---

### Option 3: Add Source Priority Rules (Advanced)

**What**: Define explicit rules for which source takes precedence

**Example Logic:**
```python
SOURCE_PRIORITY = {
    'event_metadata': 'PWA',      # PWA has better event details
    'heat_scores': 'Live Heats',  # LiveHeats has more detailed scoring
    'final_results': 'both'       # Merge both sources
}
```

**Pros:**
- Explicit data governance
- Can handle complex multi-source scenarios
- Documents business rules

**Cons:**
- More complex to implement
- Needs maintenance as sources evolve
- Overkill for current needs

**Recommendation**: ⚠️ **Consider for future if you get more sources**

---

## Recommended Action Plan

### Phase 1: Immediate Fix (Today)
```sql
-- Update event metadata to match primary data source
UPDATE PWA_IWT_EVENTS
SET source = 'Live Heats'
WHERE event_id IN (370, 378, 380);
```

**Result**: All 3 events immediately start working with existing views/APIs

### Phase 2: Architecture Fix (This Sprint)

**Update all database views** to remove source matching:

1. **Views to Update:**
   - `ATHLETE_RESULTS_VIEW`
   - `ATHLETE_HEAT_RESULTS_VIEW`
   - `EVENT_STATS_VIEW`
   - Any custom views or future HEAD_TO_HEAD_VIEW

2. **JOIN Pattern:**
   ```sql
   -- Join on business keys only
   LEFT JOIN PWA_IWT_HEAT_RESULTS hr
       ON r.event_id = hr.pwa_event_id
       AND r.athlete_id = hr.athlete_id
       -- Remove: AND r.source = hr.source
   ```

3. **API Queries:**
   - Review all direct SQL queries in FastAPI routes
   - Remove source matching from WHERE/JOIN clauses

### Phase 3: Documentation (Next Sprint)

1. **Update CLAUDE.md** with:
   - "Source field is for data lineage only, not a join key"
   - "Always join on event_id + athlete_id, not source"

2. **Add inline comments** in code:
   ```python
   # Note: source tracks data origin, not used for joining
   ```

3. **Create data dictionary** documenting:
   - Purpose of `source` field
   - Cross-source scenarios
   - Join best practices

---

## Validation Tests

After applying fixes, verify these work:

```sql
-- Test 1: Chile 2025 returns results
SELECT COUNT(*) FROM ATHLETE_RESULTS_VIEW WHERE event_id = 370;
-- Expected: 77 results

-- Test 2: Chile 2025 returns heat data
SELECT COUNT(*) FROM ATHLETE_HEAT_RESULTS_VIEW WHERE event_id = 370;
-- Expected: 246 heat results

-- Test 3: Sylt 2025 returns all results (both sources)
SELECT source, COUNT(*)
FROM ATHLETE_RESULTS_VIEW
WHERE event_id = 378
GROUP BY source;
-- Expected: LiveHeats: 31, PWA: 9

-- Test 4: Aloha Classic returns data
SELECT COUNT(*) FROM ATHLETE_RESULTS_VIEW WHERE event_id = 380;
-- Expected: 65 results
```

---

## Additional Findings

### Good News
- ✅ Athlete ID matching works perfectly across sources
- ✅ All 77 Chile athletes properly mapped to unified profiles
- ✅ Heat scores exist and are accessible (just need join fix)
- ✅ No data corruption or inconsistency

### Issues Discovered
- 987/1015 Chile scores have NULL type (should classify as Wave/Jump)
- LiveHeats division codes are NULL (acceptable, divisions tracked in PWA_IWT_RESULTS)
- Sylt has duplicate data from both sources (need deduplication strategy)

---

## Long-Term Architectural Principle

**Proposed Design Rule:**

> The `source` field exists for **data lineage and audit trails only**. It tracks where we obtained data but should NEVER be used as a join condition or business logic constraint.

**Corollary:**

> Business entities (events, athletes, heats) are identified by business keys (event_id, athlete_id, heat_id), not by their source system.

This allows the system to:
- Accept data from multiple sources
- Merge complementary data (PWA metadata + LiveHeats scores)
- Remain flexible as new data sources emerge

---

## Summary

**The Fix:**
1. Update 3 event records: `UPDATE PWA_IWT_EVENTS SET source = 'Live Heats' WHERE event_id IN (370, 378, 380);`
2. Remove source matching from all JOINs: Join only on `event_id + athlete_id`

**Why This Works:**
- Source is just a tracking field, not a relationship key
- Events are uniquely identified by event_id regardless of source
- Athletes are uniquely identified by athlete_id regardless of source

**Impact:**
- ✅ Fixes 3 critical issues immediately
- ✅ Prevents future cross-source problems
- ✅ Makes system more robust and maintainable
