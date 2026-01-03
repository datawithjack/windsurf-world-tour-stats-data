"""
Comprehensive investigation of ALL remaining NULL athlete names
"""

import mysql.connector
import csv

# Read env from .env.production
env_vars = {}
with open('.env.production') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

def get_connection():
    """Create connection to production database"""
    conn = mysql.connector.connect(
        host='10.0.151.92',
        port=3306,
        database='jfa_heatwave_db',
        user=env_vars['DB_USER'],
        password=env_vars['DB_PASSWORD'],
        connect_timeout=30
    )
    return conn

def extract_name_and_sail(athlete_id):
    """Extract name and sail number from PWA athlete_id pattern 'Name_Sail'"""
    if '_' not in athlete_id:
        return None, None
    parts = athlete_id.split('_', 1)
    return parts[0], parts[1] if len(parts) > 1 else None

def main():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    print("=" * 120)
    print("COMPREHENSIVE INVESTIGATION OF ALL REMAINING NULL ATHLETE NAMES")
    print("=" * 120)

    # Get ALL distinct athlete_ids with NULL names
    cursor.execute("""
        SELECT DISTINCT
            esv.source,
            esv.athlete_id,
            MIN(esv.sail_number) as sail_number,
            COUNT(*) as score_count,
            MIN(esv.event_year) as first_year,
            MAX(esv.event_year) as last_year
        FROM EVENT_STATS_VIEW esv
        WHERE esv.athlete_name IS NULL
        GROUP BY esv.source, esv.athlete_id
        ORDER BY score_count DESC
    """)

    null_athletes = cursor.fetchall()

    print(f"\n📊 Found {len(null_athletes)} distinct athlete_ids with NULL names")
    print(f"   Total scores affected: {sum(a['score_count'] for a in null_athletes)}")
    print("=" * 120)

    # Analyze each one
    results = []

    for idx, athlete in enumerate(null_athletes, 1):
        source = athlete['source']
        athlete_id = athlete['athlete_id']
        sail_number = athlete['sail_number']
        score_count = athlete['score_count']
        years = f"{athlete['first_year']}-{athlete['last_year']}"

        print(f"\n[{idx}/{len(null_athletes)}] {source}: {athlete_id} (Sail: {sail_number}, {score_count} scores, {years})")

        # Extract name from athlete_id for PWA
        name_part, sail_from_id = extract_name_and_sail(athlete_id)

        # Check if mapping exists in ATHLETE_SOURCE_IDS
        cursor.execute("""
            SELECT asi.source, asi.source_id, asi.athlete_id,
                   a.primary_name, a.pwa_sail_number
            FROM ATHLETE_SOURCE_IDS asi
            LEFT JOIN ATHLETES a ON asi.athlete_id = a.id
            WHERE asi.source_id = %s
        """, (athlete_id,))

        existing_mappings = cursor.fetchall()

        if existing_mappings:
            print(f"  ⚠️  MAPPING EXISTS but not matching:")
            for m in existing_mappings:
                print(f"     Source: {m['source']} (should be 'PWA_heat' or 'PWA')")
                print(f"     → {m['primary_name']} (ID: {m['athlete_id']}, Sail: {m['pwa_sail_number']})")

            results.append({
                'athlete_id': athlete_id,
                'source': source,
                'sail_number': sail_number,
                'score_count': score_count,
                'status': 'MAPPING_SOURCE_MISMATCH',
                'existing_source': existing_mappings[0]['source'],
                'matched_athlete_id': existing_mappings[0]['athlete_id'],
                'matched_name': existing_mappings[0]['primary_name'],
                'action': f"Source '{existing_mappings[0]['source']}' should work but doesn't"
            })
            continue

        # Try to find matches in ATHLETES table
        potential_matches = []

        if source == 'PWA' and name_part:
            # Search by name pattern
            name_search = name_part.replace(' ', '')
            cursor.execute("""
                SELECT id, primary_name, pwa_name, pwa_athlete_id, pwa_sail_number
                FROM ATHLETES
                WHERE REPLACE(LOWER(primary_name), ' ', '') LIKE LOWER(%s)
                   OR REPLACE(LOWER(pwa_name), ' ', '') LIKE LOWER(%s)
                LIMIT 5
            """, (f"%{name_search}%", f"%{name_search}%"))

            potential_matches = cursor.fetchall()

        if potential_matches:
            print(f"  🔍 Potential matches in ATHLETES table:")
            best_match = None

            for match in potential_matches:
                match_score = 0
                reasons = []

                # Score the match quality
                if name_search.lower() in match['primary_name'].lower().replace(' ', ''):
                    match_score += 3
                    reasons.append("name match")

                if sail_number and match['pwa_sail_number'] == sail_number:
                    match_score += 5
                    reasons.append("exact sail match")
                elif sail_number and match['pwa_sail_number'] and \
                     sail_number.replace('-', '').upper() in match['pwa_sail_number'].replace('-', '').upper():
                    match_score += 2
                    reasons.append("partial sail match")

                print(f"     [{match_score}] {match['primary_name']} (ID: {match['id']}, Sail: {match['pwa_sail_number']}) - {', '.join(reasons)}")

                if best_match is None or match_score > best_match[1]:
                    best_match = (match, match_score)

            if best_match and best_match[1] >= 5:  # High confidence match
                match = best_match[0]
                results.append({
                    'athlete_id': athlete_id,
                    'source': source,
                    'sail_number': sail_number,
                    'score_count': score_count,
                    'status': 'HIGH_CONFIDENCE_MATCH',
                    'matched_athlete_id': match['id'],
                    'matched_name': match['primary_name'],
                    'match_score': best_match[1],
                    'action': f"CREATE MAPPING: source='PWA_heat', source_id='{athlete_id}', athlete_id={match['id']}"
                })
                print(f"  ✅ HIGH CONFIDENCE: Can map to {match['primary_name']} (ID: {match['id']})")
            else:
                results.append({
                    'athlete_id': athlete_id,
                    'source': source,
                    'sail_number': sail_number,
                    'score_count': score_count,
                    'status': 'NEEDS_MANUAL_REVIEW',
                    'matched_athlete_id': best_match[0]['id'] if best_match else None,
                    'matched_name': best_match[0]['primary_name'] if best_match else None,
                    'match_score': best_match[1] if best_match else 0,
                    'action': 'Manual review needed - uncertain match'
                })
                print(f"  ⚠️  UNCERTAIN: Manual review needed")
        else:
            print(f"  ❌ No matches found in ATHLETES table")
            results.append({
                'athlete_id': athlete_id,
                'source': source,
                'sail_number': sail_number,
                'score_count': score_count,
                'status': 'NO_ATHLETE_RECORD',
                'matched_athlete_id': None,
                'matched_name': None,
                'action': 'Athlete not in ATHLETES table - data quality issue'
            })

    # Summary
    print("\n" + "=" * 120)
    print("SUMMARY BY STATUS")
    print("=" * 120)

    from collections import Counter
    status_counts = Counter(r['status'] for r in results)

    for status, count in status_counts.most_common():
        pct = (count / len(results) * 100) if results else 0
        total_scores = sum(r['score_count'] for r in results if r['status'] == status)
        print(f"{status:<30} {count:>4} athletes ({pct:>5.1f}%), {total_scores:>6} scores affected")

    # Save detailed report
    output_file = '/tmp/null_athletes_detailed_report.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['athlete_id', 'source', 'sail_number', 'score_count', 'status',
                      'matched_athlete_id', 'matched_name', 'action']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in fieldnames})

    print(f"\n✅ Detailed report saved to: {output_file}")

    # Generate SQL for high-confidence mappings
    high_confidence = [r for r in results if r['status'] == 'HIGH_CONFIDENCE_MATCH']
    if high_confidence:
        print(f"\n" + "=" * 120)
        print(f"SUGGESTED SQL INSERTS FOR {len(high_confidence)} HIGH-CONFIDENCE MATCHES")
        print("=" * 120)
        print("\nINSERT INTO ATHLETE_SOURCE_IDS (athlete_id, source, source_id) VALUES")
        for i, r in enumerate(high_confidence):
            comma = "," if i < len(high_confidence) - 1 else ";"
            print(f"  ({r['matched_athlete_id']}, 'PWA_heat', '{r['athlete_id']}'){comma}  -- {r['matched_name']}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
