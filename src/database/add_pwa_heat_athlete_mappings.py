"""
Add PWA Heat Composite Athlete IDs to ATHLETE_SOURCE_IDS table.

This script matches composite athlete_ids from PWA_IWT_HEAT_SCORES
(format: "SURNAME_SAILNUMBER") to unified athlete profiles in ATHLETES table.
New entries are added to ATHLETE_SOURCE_IDS to enable EVENT_STATS_VIEW joins.

Three-Stage Matching Strategy:

1. Exact Composite Match: Construct IDs from ATHLETES.pwa_name + pwa_sail_number
   - Extract surname (last word) from pwa_name
   - Combine with pwa_sail_number: "{surname}_{sail_number}"
   - Match exactly to PWA heat composite IDs
   - Example: "Warchol_POL-111" matches "Warchol_POL-111" (100%)

1.5. Sail Number + Fuzzy Surname: Handle spelling variations
   - Match exact sail number (e.g., "POL-1111")
   - Fuzzy match surnames (e.g., "Sniady" vs "Snaidy")
   - Auto-match if surname fuzzy score >= 80%
   - Example: "Sniady_POL-1111" matches "Snaidy_POL-1111" (83% surname match)

2. General Fuzzy Match (fallback): For athletes without PWA data
   - Fuzzy match full athlete names to unified ATHLETES table
   - Auto-match with >= 80% confidence
   - Flag < 80% for manual review

Result: Maximizes automatic matching while maintaining high accuracy
"""

import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
from fuzzywuzzy import fuzz

# Load environment variables
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

def normalize_name(name):
    """
    Normalize athlete name for fuzzy matching.

    Args:
        name: Athlete name string

    Returns:
        Normalized name (uppercase, no spaces/hyphens)
    """
    if pd.isna(name) or not name:
        return ''
    # Remove spaces, hyphens, convert to uppercase
    return name.replace(' ', '').replace('-', '').upper()

def get_pwa_heat_athletes(cursor):
    """
    Query unique PWA composite athlete_ids from heat scores.

    Args:
        cursor: Database cursor

    Returns:
        DataFrame with composite_id, athlete_name, sail_number
    """
    print("\nQuerying PWA heat score athlete IDs...")

    query = """
        SELECT DISTINCT
            athlete_id AS composite_id,
            athlete_name,
            sail_number
        FROM PWA_IWT_HEAT_SCORES
        WHERE source = 'PWA'
          AND athlete_id IS NOT NULL
          AND athlete_id != ''
        ORDER BY athlete_name
    """

    cursor.execute(query)
    results = cursor.fetchall()

    df = pd.DataFrame(results, columns=['composite_id', 'athlete_name', 'sail_number'])
    print(f"  [OK] Found {len(df)} unique PWA heat athletes")

    return df

def get_unified_athletes(cursor):
    """
    Query unified ATHLETES table with PWA data.

    Args:
        cursor: Database cursor

    Returns:
        DataFrame with athlete_id, primary_name, pwa_name, pwa_sail_number
    """
    print("\nQuerying unified ATHLETES table...")

    query = """
        SELECT
            id AS athlete_id,
            primary_name,
            pwa_name,
            pwa_sail_number
        FROM ATHLETES
        ORDER BY primary_name
    """

    cursor.execute(query)
    results = cursor.fetchall()

    df = pd.DataFrame(results, columns=['athlete_id', 'primary_name', 'pwa_name', 'pwa_sail_number'])
    print(f"  [OK] Found {len(df)} unified athletes")

    return df

def construct_composite_id(pwa_name, pwa_sail_number):
    """
    Construct composite athlete_id in same format as PWA heat data.

    Format: "{surname}_{sail_number}"

    Args:
        pwa_name: Full PWA athlete name (e.g., "Adam Warchol")
        pwa_sail_number: PWA sail number (e.g., "POL-111")

    Returns:
        Composite ID string or None if data missing
    """
    if pd.isna(pwa_name) or pd.isna(pwa_sail_number):
        return None

    # Extract surname (last word)
    name_parts = str(pwa_name).strip().split()
    if not name_parts:
        return None

    surname = name_parts[-1]

    # Construct composite ID
    composite_id = f"{surname}_{pwa_sail_number}"

    return composite_id

def create_athlete_lookup(athletes_df):
    """
    Create lookup dictionary mapping composite IDs to athlete IDs.

    Args:
        athletes_df: DataFrame of ATHLETES table

    Returns:
        Dict mapping composite_id -> (athlete_id, matched_name, match_method)
    """
    print("\nBuilding composite ID lookup from ATHLETES table...")

    lookup = {}
    constructed_count = 0

    for _, athlete in athletes_df.iterrows():
        # Construct composite ID from PWA data
        composite_id = construct_composite_id(athlete['pwa_name'], athlete['pwa_sail_number'])

        if composite_id:
            lookup[composite_id] = (
                athlete['athlete_id'],
                athlete['pwa_name'],
                'exact_composite'
            )
            constructed_count += 1

    print(f"  [OK] Built lookup for {constructed_count} athletes with PWA data")

    return lookup

def find_match_by_sail_and_surname(composite_id, sail_number, athletes_df, threshold=80):
    """
    Match by exact sail number + fuzzy surname matching.

    Catches spelling variations like Sniady/Snaidy where sail number matches
    but surname spelling differs slightly.

    Args:
        composite_id: "SURNAME_SAILNUMBER" format from heat scores
        sail_number: Sail number from heat scores
        athletes_df: DataFrame of ATHLETES table
        threshold: Minimum fuzzy match score for surname (default 80)

    Returns:
        Dict with match results or None if no match
    """
    # Extract surname from composite ID (before underscore)
    if '_' not in composite_id:
        return None

    heat_surname = composite_id.split('_')[0]

    # Filter athletes with exact matching sail number
    matching_sail = athletes_df[athletes_df['pwa_sail_number'] == sail_number].copy()

    if len(matching_sail) == 0:
        return None

    best_match_id = None
    best_matched_name = None
    best_score = 0

    # For each athlete with matching sail number, fuzzy match surnames
    for _, athlete in matching_sail.iterrows():
        if pd.isna(athlete['pwa_name']):
            continue

        # Extract surname from pwa_name (last word)
        name_parts = str(athlete['pwa_name']).strip().split()
        if not name_parts:
            continue

        athlete_surname = name_parts[-1]

        # Fuzzy match the surnames
        score = fuzz.ratio(normalize_name(heat_surname), normalize_name(athlete_surname))

        if score > best_score:
            best_score = score
            best_match_id = athlete['athlete_id']
            best_matched_name = athlete['pwa_name']

    # Only return if score meets threshold
    if best_score >= threshold:
        return {
            'athlete_id': best_match_id,
            'matched_name': best_matched_name,
            'match_score': best_score,
            'match_method': 'sail_fuzzy_surname'
        }

    return None

def find_best_match(composite_id, athlete_name, sail_number, athletes_df):
    """
    Match composite ID to unified athlete using fuzzy name matching.

    Args:
        composite_id: "SURNAME_SAILNUMBER" format
        athlete_name: Full name from heat scores
        sail_number: Sail number
        athletes_df: DataFrame of ATHLETES table

    Returns:
        Dict with match results: {
            'athlete_id': unified athlete ID (or None),
            'matched_name': matched athlete name,
            'match_score': fuzzy match confidence (0-100),
            'match_method': 'pwa_name' or 'primary_name'
        }
    """
    # Normalize search name
    search_name = normalize_name(athlete_name)

    best_match_id = None
    best_matched_name = None
    best_score = 0
    best_method = None

    for _, athlete in athletes_df.iterrows():
        # Try PWA name first (more likely to match PWA heat data)
        if pd.notna(athlete['pwa_name']):
            score = fuzz.ratio(search_name, normalize_name(athlete['pwa_name']))
            if score > best_score:
                best_score = score
                best_match_id = athlete['athlete_id']
                best_matched_name = athlete['pwa_name']
                best_method = 'pwa_name'

        # Try primary name as fallback
        if pd.notna(athlete['primary_name']):
            score = fuzz.ratio(search_name, normalize_name(athlete['primary_name']))
            if score > best_score:
                best_score = score
                best_match_id = athlete['athlete_id']
                best_matched_name = athlete['primary_name']
                best_method = 'primary_name'

    return {
        'athlete_id': best_match_id,
        'matched_name': best_matched_name,
        'match_score': best_score,
        'match_method': best_method
    }

def match_pwa_heat_athletes(heat_athletes_df, unified_athletes_df, composite_lookup, threshold=80):
    """
    Match all PWA heat athletes to unified athletes.

    Uses three-stage matching:
    1. Exact match on constructed composite ID (surname_sailnumber)
    1.5. Sail number match + fuzzy surname (for spelling variations)
    2. Fuzzy name matching (fallback)

    Args:
        heat_athletes_df: DataFrame of PWA heat athletes
        unified_athletes_df: DataFrame of unified ATHLETES
        composite_lookup: Dict mapping composite_id -> (athlete_id, name, method)
        threshold: Auto-match threshold for fuzzy matching (default 80)

    Returns:
        DataFrame with matching results
    """
    print(f"\nMatching PWA heat athletes to unified athletes...")
    print(f"  Stage 1: Exact composite ID match")
    print(f"  Stage 1.5: Sail number + fuzzy surname match")
    print(f"  Stage 2: Fuzzy name match (threshold={threshold}%)")

    matches = []
    exact_matches = 0
    sail_fuzzy_matches = 0
    fuzzy_matches = 0

    for idx, row in heat_athletes_df.iterrows():
        composite_id = row['composite_id']
        athlete_name = row['athlete_name']
        sail_number = row['sail_number']

        # Stage 1: Try exact composite ID match
        if composite_id in composite_lookup:
            athlete_id, matched_name, match_method = composite_lookup[composite_id]
            match = {
                'athlete_id': athlete_id,
                'matched_name': matched_name,
                'match_score': 100,
                'match_method': match_method
            }
            exact_matches += 1
        else:
            # Stage 1.5: Try sail number + fuzzy surname match
            match = find_match_by_sail_and_surname(composite_id, sail_number, unified_athletes_df, threshold=80)

            if match and match['match_score'] >= 80:
                sail_fuzzy_matches += 1
            else:
                # Stage 2: Fall back to general fuzzy matching
                match = find_best_match(composite_id, athlete_name, sail_number, unified_athletes_df)
                if match['match_score'] >= threshold:
                    fuzzy_matches += 1

        # Determine match status
        if match['match_score'] >= threshold:
            match_status = 'auto_matched'
        elif match['match_score'] > 0:
            match_status = 'needs_review'
        else:
            match_status = 'no_match'

        matches.append({
            'composite_athlete_id': composite_id,
            'heat_scores_name': athlete_name,
            'sail_number': sail_number,
            'matched_athlete_id': match['athlete_id'],
            'matched_primary_name': match['matched_name'],
            'match_score': match['match_score'],
            'match_method': match['match_method'],
            'match_status': match_status
        })

    matches_df = pd.DataFrame(matches)

    # Print summary
    auto_matched = len(matches_df[matches_df['match_status'] == 'auto_matched'])
    needs_review = len(matches_df[matches_df['match_status'] == 'needs_review'])
    no_match = len(matches_df[matches_df['match_status'] == 'no_match'])

    print(f"  [OK] Matching complete:")
    print(f"    - Exact composite matches: {exact_matches}")
    print(f"    - Sail + fuzzy surname matches: {sail_fuzzy_matches}")
    print(f"    - General fuzzy matches (>={threshold}%): {fuzzy_matches}")
    print(f"    - Total auto-matched: {auto_matched}")
    print(f"    - Needs review (<{threshold}%): {needs_review}")
    print(f"    - No match: {no_match}")

    return matches_df

def insert_mappings_to_db(cursor, matches_df, dry_run=False):
    """
    Insert matched composite IDs into ATHLETE_SOURCE_IDS table.

    Args:
        cursor: Database cursor
        matches_df: DataFrame with matching results
        dry_run: If True, print SQL without executing (default False)

    Returns:
        Number of rows inserted
    """
    # Filter to auto-matched only (>= 80% confidence)
    auto_matched = matches_df[matches_df['match_status'] == 'auto_matched'].copy()

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(auto_matched)} mappings to ATHLETE_SOURCE_IDS")
        print("\nSample SQL (first 5):")
        for _, row in auto_matched.head(5).iterrows():
            print(f"  INSERT IGNORE INTO ATHLETE_SOURCE_IDS")
            print(f"    (athlete_id, source, source_id)")
            print(f"    VALUES ({row['matched_athlete_id']}, 'PWA', '{row['composite_athlete_id']}');")
        return 0

    print(f"\nInserting {len(auto_matched)} mappings to ATHLETE_SOURCE_IDS...")

    insert_query = """
        INSERT IGNORE INTO ATHLETE_SOURCE_IDS
        (athlete_id, source, source_id)
        VALUES (%s, %s, %s)
    """

    # Prepare batch insert data
    insert_data = [
        (int(row['matched_athlete_id']), 'PWA', row['composite_athlete_id'])
        for _, row in auto_matched.iterrows()
    ]

    # Execute batch insert
    cursor.executemany(insert_query, insert_data)
    rows_inserted = cursor.rowcount

    print(f"  [OK] Inserted {rows_inserted} new mappings")

    return rows_inserted

def save_matching_report(matches_df, output_file='data/reports/pwa_heat_athlete_mapping_report.csv'):
    """
    Save matching report CSV for manual review.

    Args:
        matches_df: DataFrame with matching results
        output_file: Output CSV file path
    """
    print(f"\nSaving matching report to {output_file}...")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Sort by match status and score
    matches_df_sorted = matches_df.sort_values(
        by=['match_status', 'match_score'],
        ascending=[True, False]
    )

    # Save to CSV
    matches_df_sorted.to_csv(output_file, index=False)

    print(f"  [OK] Report saved: {len(matches_df)} records")

def verify_mappings(cursor):
    """
    Verify new mappings in ATHLETE_SOURCE_IDS and EVENT_STATS_VIEW.

    Args:
        cursor: Database cursor
    """
    print("\n" + "="*50)
    print("VERIFYING MAPPINGS")
    print("="*50)

    # Check composite ID mappings
    print("\n1. Composite ID mappings in ATHLETE_SOURCE_IDS:")
    cursor.execute("""
        SELECT COUNT(*)
        FROM ATHLETE_SOURCE_IDS
        WHERE source = 'PWA'
          AND source_id LIKE '%_%'
    """)
    composite_count = cursor.fetchone()[0]
    print(f"   Total composite IDs mapped: {composite_count}")

    # Sample composite mappings
    print("\n   Sample composite ID mappings:")
    cursor.execute("""
        SELECT
            asi.source_id AS composite_id,
            a.primary_name
        FROM ATHLETE_SOURCE_IDS asi
        JOIN ATHLETES a ON asi.athlete_id = a.id
        WHERE asi.source = 'PWA'
          AND asi.source_id LIKE '%_%'
        ORDER BY a.primary_name
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"     {row[0]} -> {row[1]}")

    # Check EVENT_STATS_VIEW athlete names for PWA
    print("\n2. EVENT_STATS_VIEW athlete names for PWA:")
    cursor.execute("""
        SELECT
            CASE
                WHEN athlete_name IS NOT NULL THEN 'Has Name'
                ELSE 'NULL Name'
            END AS status,
            COUNT(*) as count
        FROM EVENT_STATS_VIEW
        WHERE source = 'PWA'
        GROUP BY status
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} scores")

    # Sample PWA scores with athlete names
    print("\n   Sample PWA scores with athlete names:")
    cursor.execute("""
        SELECT
            event_name,
            athlete_name,
            sex,
            score,
            move_type
        FROM EVENT_STATS_VIEW
        WHERE source = 'PWA'
          AND athlete_name IS NOT NULL
        ORDER BY score DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        event = row[0][:25] if row[0] else 'N/A'
        print(f"     {row[1]} ({row[2]}) - {event} - {row[3]} ({row[4]})")

def main(dry_run=False):
    """
    Main execution function.

    Args:
        dry_run: If True, perform matching and generate report without inserting to DB
    """
    print("Add PWA Heat Composite Athlete IDs to ATHLETE_SOURCE_IDS")
    print("="*50)

    if dry_run:
        print("\n*** DRY RUN MODE - No database changes will be made ***\n")

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print("  [OK] Connected successfully")

        # Step 1: Get PWA heat athletes
        heat_athletes_df = get_pwa_heat_athletes(cursor)

        # Step 2: Get unified athletes
        unified_athletes_df = get_unified_athletes(cursor)

        # Step 3: Build composite ID lookup
        composite_lookup = create_athlete_lookup(unified_athletes_df)

        # Step 4: Match athletes (exact composite match + fuzzy fallback)
        matches_df = match_pwa_heat_athletes(heat_athletes_df, unified_athletes_df, composite_lookup, threshold=80)

        # Step 5: Save matching report
        save_matching_report(matches_df)

        # Step 6: Insert mappings (or show dry run)
        rows_inserted = insert_mappings_to_db(cursor, matches_df, dry_run=dry_run)

        if not dry_run:
            # Commit changes
            conn.commit()
            print("\n[OK] Database changes committed")

            # Step 7: Verify mappings
            verify_mappings(cursor)

        # Print final summary
        print("\n" + "="*50)
        if dry_run:
            print("DRY RUN COMPLETE - Review the matching report")
        else:
            print("SUCCESS - PWA heat athlete mappings added!")
        print("="*50)

        print("\nSummary:")
        print(f"  - Total PWA heat athletes: {len(heat_athletes_df)}")
        print(f"  - Auto-matched (>= 80%): {len(matches_df[matches_df['match_status'] == 'auto_matched'])}")
        print(f"  - Needs review (< 80%): {len(matches_df[matches_df['match_status'] == 'needs_review'])}")
        print(f"  - No match: {len(matches_df[matches_df['match_status'] == 'no_match'])}")
        if not dry_run:
            print(f"  - Rows inserted to ATHLETE_SOURCE_IDS: {rows_inserted}")

        print("\nNext steps:")
        if dry_run:
            print("  1. Review matching report: data/reports/pwa_heat_athlete_mapping_report.csv")
            print("  2. Run script without --dry-run to insert mappings")
        else:
            print("  1. Review matching report: data/reports/pwa_heat_athlete_mapping_report.csv")
            print("  2. Manually review 'needs_review' matches")
            print("  3. Query EVENT_STATS_VIEW to verify athlete names are populated")

    except mysql.connector.Error as err:
        print(f"\n[ERROR] DATABASE ERROR: {err}")
        return

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    import sys

    # Check for --dry-run flag
    dry_run = '--dry-run' in sys.argv

    main(dry_run=dry_run)
