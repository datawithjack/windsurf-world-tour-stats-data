"""
Data Quality Analysis Script for Windsurf World Tour Stats Database

This script performs READ-ONLY analysis to identify data quality issues,
completeness gaps, and inconsistencies across all tables.

Usage:
    python analyze_data_quality.py

Output:
    - Console report with findings
    - CSV reports in data/reports/ directory
    - Recommendations for data cleaning
"""

import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime
import csv
from collections import defaultdict

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

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*100)
    print(title)
    print("="*100)

def print_subsection(title):
    """Print formatted subsection header"""
    print("\n" + "-"*100)
    print(title)
    print("-"*100)

def analyze_table_summary(cursor):
    """Get basic statistics for all tables"""
    print_section("1. DATABASE SUMMARY STATISTICS")

    tables = [
        'PWA_IWT_EVENTS',
        'PWA_IWT_RESULTS',
        'PWA_IWT_HEAT_PROGRESSION',
        'PWA_IWT_HEAT_RESULTS',
        'PWA_IWT_HEAT_SCORES',
        'ATHLETES',
        'ATHLETE_SOURCE_IDS'
    ]

    summary = {}

    for table in tables:
        print_subsection(f"Table: {table}")

        # Total count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total = cursor.fetchone()[0]
        print(f"  Total Records: {total:,}")

        summary[table] = {'total': total}

        # Source breakdown (if table has source column)
        if table != 'ATHLETES':
            cursor.execute(f"""
                SELECT source, COUNT(*) as count
                FROM {table}
                GROUP BY source
            """)
            sources = cursor.fetchall()
            print(f"  By Source:")
            for source, count in sources:
                print(f"    {source}: {count:,}")

        # Year breakdown for event-related tables
        if table in ['PWA_IWT_EVENTS', 'PWA_IWT_RESULTS']:
            year_col = 'year' if table == 'PWA_IWT_EVENTS' else 'year'
            cursor.execute(f"""
                SELECT {year_col}, COUNT(*) as count
                FROM {table}
                GROUP BY {year_col}
                ORDER BY {year_col} DESC
                LIMIT 5
            """)
            years = cursor.fetchall()
            print(f"  Recent Years:")
            for year, count in years:
                print(f"    {year}: {count:,}")

    return summary

def analyze_event_coverage(cursor):
    """Analyze data completeness for each event"""
    print_section("2. EVENT COVERAGE ANALYSIS")

    # Get all events
    cursor.execute("""
        SELECT
            e.id,
            e.source as event_source,
            e.event_id,
            e.event_name,
            e.year,
            e.stars
        FROM PWA_IWT_EVENTS e
        ORDER BY e.year DESC, e.event_id
    """)

    events = cursor.fetchall()

    print(f"\nAnalyzing {len(events)} events...\n")

    coverage_data = []
    issues = []

    for event_db_id, event_source, event_id, event_name, year, stars in events:

        # Check PWA_IWT_RESULTS
        cursor.execute("""
            SELECT COUNT(DISTINCT source) as source_count,
                   GROUP_CONCAT(DISTINCT source) as sources,
                   COUNT(*) as result_count
            FROM PWA_IWT_RESULTS
            WHERE event_id = %s
        """, (event_id,))
        results_data = cursor.fetchone()
        has_results = results_data[2] > 0
        result_sources = results_data[1] if results_data[1] else ''
        result_count = results_data[2]

        # Check PWA_IWT_HEAT_PROGRESSION
        cursor.execute("""
            SELECT COUNT(*) FROM PWA_IWT_HEAT_PROGRESSION
            WHERE pwa_event_id = %s
        """, (event_id,))
        heat_prog_count = cursor.fetchone()[0]
        has_heat_prog = heat_prog_count > 0

        # Check PWA_IWT_HEAT_RESULTS
        cursor.execute("""
            SELECT COUNT(*) FROM PWA_IWT_HEAT_RESULTS
            WHERE pwa_event_id = %s
        """, (event_id,))
        heat_results_count = cursor.fetchone()[0]
        has_heat_results = heat_results_count > 0

        # Check PWA_IWT_HEAT_SCORES
        cursor.execute("""
            SELECT COUNT(*) FROM PWA_IWT_HEAT_SCORES
            WHERE pwa_event_id = %s
        """, (event_id,))
        heat_scores_count = cursor.fetchone()[0]
        has_heat_scores = heat_scores_count > 0

        # Calculate completeness
        completeness_pct = sum([has_results, has_heat_prog, has_heat_results, has_heat_scores]) / 4 * 100

        # Flag cross-source issues
        source_mismatch = event_source != result_sources if has_results and result_sources else False

        coverage_data.append({
            'event_id': event_id,
            'event_name': event_name,
            'year': year,
            'stars': stars,
            'event_source': event_source,
            'result_sources': result_sources,
            'source_mismatch': source_mismatch,
            'result_count': result_count,
            'heat_prog_count': heat_prog_count,
            'heat_results_count': heat_results_count,
            'heat_scores_count': heat_scores_count,
            'completeness_pct': completeness_pct
        })

        # Identify issues
        if has_results and not has_heat_results:
            issues.append({
                'severity': 'HIGH',
                'event_id': event_id,
                'event_name': event_name,
                'year': year,
                'issue': 'Has final results but no heat data',
                'details': f'{result_count} results, 0 heats'
            })

        if source_mismatch:
            issues.append({
                'severity': 'CRITICAL',
                'event_id': event_id,
                'event_name': event_name,
                'year': year,
                'issue': 'Cross-source mismatch',
                'details': f'Event source: {event_source}, Results source: {result_sources}'
            })

        if has_heat_results and not has_heat_scores:
            issues.append({
                'severity': 'MEDIUM',
                'event_id': event_id,
                'event_name': event_name,
                'year': year,
                'issue': 'Has heat results but no individual scores',
                'details': f'{heat_results_count} heat results, 0 scores'
            })

    # Print summary
    print_subsection("Coverage Summary")
    complete_events = sum(1 for e in coverage_data if e['completeness_pct'] == 100)
    partial_events = sum(1 for e in coverage_data if 0 < e['completeness_pct'] < 100)
    results_only = sum(1 for e in coverage_data if e['result_count'] > 0 and e['heat_scores_count'] == 0)

    print(f"  Complete Events (all data): {complete_events}")
    print(f"  Partial Events: {partial_events}")
    print(f"  Results-Only Events: {results_only}")
    print(f"  Cross-Source Mismatches: {sum(1 for e in coverage_data if e['source_mismatch'])}")

    # Print top issues
    print_subsection("Top Coverage Issues")
    for issue in sorted(issues, key=lambda x: x['severity'])[:15]:
        print(f"  [{issue['severity']}] {issue['event_name']} ({issue['year']})")
        print(f"           {issue['issue']}: {issue['details']}")

    return coverage_data, issues

def analyze_field_consistency(cursor):
    """Check field consistency across tables"""
    print_section("3. FIELD CONSISTENCY ANALYSIS")

    issues = []

    # Division code consistency
    print_subsection("A. Division Code Consistency")

    cursor.execute("""
        SELECT
            'PWA_IWT_RESULTS' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN division_code IS NULL OR division_code = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_RESULTS
        UNION ALL
        SELECT
            'PWA_IWT_HEAT_PROGRESSION' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN pwa_division_code IS NULL OR pwa_division_code = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_HEAT_PROGRESSION
        UNION ALL
        SELECT
            'PWA_IWT_HEAT_RESULTS' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN pwa_division_code IS NULL OR pwa_division_code = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_HEAT_RESULTS
        UNION ALL
        SELECT
            'PWA_IWT_HEAT_SCORES' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN pwa_division_code IS NULL OR pwa_division_code = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_HEAT_SCORES
    """)

    div_code_results = cursor.fetchall()
    print("  Division Code NULL/Empty Counts:")
    for table, total, null_count in div_code_results:
        pct = (null_count / total * 100) if total > 0 else 0
        print(f"    {table}: {null_count:,} / {total:,} ({pct:.1f}%)")

        if pct > 50:
            issues.append({
                'severity': 'HIGH',
                'category': 'Field Consistency',
                'issue': f'{table} has {pct:.1f}% NULL division codes',
                'recommendation': 'Investigate source data and populate division codes'
            })

    # Sex field consistency
    print_subsection("B. Sex Field Population")

    cursor.execute("""
        SELECT
            'PWA_IWT_RESULTS' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN sex IS NULL OR sex = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_RESULTS
        UNION ALL
        SELECT
            'PWA_IWT_HEAT_PROGRESSION' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN sex IS NULL OR sex = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_HEAT_PROGRESSION
        UNION ALL
        SELECT
            'PWA_IWT_HEAT_RESULTS' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN sex IS NULL OR sex = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_HEAT_RESULTS
        UNION ALL
        SELECT
            'PWA_IWT_HEAT_SCORES' as table_name,
            COUNT(*) as total,
            SUM(CASE WHEN sex IS NULL OR sex = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_HEAT_SCORES
    """)

    sex_results = cursor.fetchall()
    print("  Sex Field NULL/Empty Counts:")
    for table, total, null_count in sex_results:
        pct = (null_count / total * 100) if total > 0 else 0
        print(f"    {table}: {null_count:,} / {total:,} ({pct:.1f}%)")

    # Score type classification
    print_subsection("C. Score Type Classification (Wave/Jump)")

    cursor.execute("""
        SELECT
            type,
            COUNT(*) as count,
            COUNT(DISTINCT pwa_event_id) as event_count
        FROM PWA_IWT_HEAT_SCORES
        GROUP BY type
    """)

    type_results = cursor.fetchall()
    print("  Score Types:")
    for score_type, count, event_count in type_results:
        type_label = score_type if score_type else 'NULL/Unclassified'
        print(f"    {type_label}: {count:,} scores across {event_count} events")

        if not score_type:
            issues.append({
                'severity': 'MEDIUM',
                'category': 'Score Classification',
                'issue': f'{count:,} heat scores have NULL type',
                'recommendation': 'Classify scores as Wave or Jump based on source data'
            })

    # Athlete name population
    print_subsection("D. Athlete Name Population")

    cursor.execute("""
        SELECT
            source,
            COUNT(*) as total,
            SUM(CASE WHEN athlete_name IS NULL OR athlete_name = '' THEN 1 ELSE 0 END) as null_count
        FROM PWA_IWT_RESULTS
        GROUP BY source
    """)

    name_results = cursor.fetchall()
    print("  Athlete Names in PWA_IWT_RESULTS:")
    for source, total, null_count in name_results:
        pct = (null_count / total * 100) if total > 0 else 0
        print(f"    {source}: {null_count:,} / {total:,} missing ({pct:.1f}%)")

        if pct > 80:
            issues.append({
                'severity': 'MEDIUM',
                'category': 'Athlete Names',
                'issue': f'{source} results have {pct:.1f}% missing athlete names',
                'recommendation': 'Populate names from ATHLETES table via mapping'
            })

    return issues

def analyze_athlete_quality(cursor):
    """Analyze athlete data quality"""
    print_section("4. ATHLETE DATA QUALITY")

    issues = []

    # Orphaned source IDs
    print_subsection("A. Athlete Mapping Coverage")

    cursor.execute("""
        SELECT
            r.source,
            COUNT(DISTINCT r.athlete_id) as unique_athletes,
            COUNT(DISTINCT asi.athlete_id) as mapped_athletes
        FROM PWA_IWT_RESULTS r
        LEFT JOIN ATHLETE_SOURCE_IDS asi
            ON r.source = asi.source
            AND r.athlete_id = asi.source_id
        WHERE r.athlete_id IS NOT NULL AND r.athlete_id != ''
        GROUP BY r.source
    """)

    mapping_results = cursor.fetchall()
    print("  Athlete Mapping Success Rate:")
    for source, unique_athletes, mapped_athletes in mapping_results:
        unmapped = unique_athletes - (mapped_athletes if mapped_athletes else 0)
        pct = (mapped_athletes / unique_athletes * 100) if unique_athletes > 0 and mapped_athletes else 0
        print(f"    {source}: {mapped_athletes}/{unique_athletes} mapped ({pct:.1f}%)")

        if unmapped > 0:
            print(f"              {unmapped} orphaned athlete IDs")
            issues.append({
                'severity': 'CRITICAL',
                'category': 'Athlete Mapping',
                'issue': f'{unmapped} {source} athlete IDs not mapped to unified profiles',
                'recommendation': 'Create athlete mappings for missing source IDs'
            })

    # Athletes without names
    print_subsection("B. Athletes Without Names")

    cursor.execute("""
        SELECT COUNT(*)
        FROM ATHLETES
        WHERE primary_name IS NULL OR primary_name = ''
    """)

    unnamed_count = cursor.fetchone()[0]
    print(f"  Athletes without primary name: {unnamed_count}")

    if unnamed_count > 0:
        issues.append({
            'severity': 'HIGH',
            'category': 'Athlete Data',
            'issue': f'{unnamed_count} athletes have no primary name',
            'recommendation': 'Review athlete profiles and populate names from source data'
        })

    # Nationality coverage
    print_subsection("C. Nationality Coverage")

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN nationality IS NULL OR nationality = '' THEN 1 ELSE 0 END) as null_count
        FROM ATHLETES
    """)

    total, null_count = cursor.fetchone()
    pct = (null_count / total * 100) if total > 0 else 0
    print(f"  Athletes without nationality: {null_count}/{total} ({pct:.1f}%)")

    return issues

def analyze_specific_issues(cursor):
    """Investigate specific known issues"""
    print_section("5. SPECIFIC ISSUE INVESTIGATION")

    issues = []

    # Chile 2025 Men - Heat wins but no wave scores
    print_subsection("A. Chile 2025 Men's Division (Event ID 370)")

    cursor.execute("""
        SELECT
            COUNT(DISTINCT hr.athlete_id) as athletes_with_heats,
            COUNT(DISTINCT hs.athlete_id) as athletes_with_scores,
            SUM(CASE WHEN hr.place = 1 THEN 1 ELSE 0 END) as total_heat_wins
        FROM PWA_IWT_HEAT_RESULTS hr
        LEFT JOIN PWA_IWT_HEAT_SCORES hs
            ON hr.pwa_event_id = hs.pwa_event_id
            AND hr.athlete_id = hs.athlete_id
        WHERE hr.pwa_event_id = 370
    """)

    chile_data = cursor.fetchone()
    print(f"  Athletes with heat results: {chile_data[0]}")
    print(f"  Athletes with heat scores: {chile_data[1]}")
    print(f"  Total heat wins recorded: {chile_data[2]}")

    # Check if scores exist but don't match
    cursor.execute("""
        SELECT COUNT(DISTINCT hs.athlete_id)
        FROM PWA_IWT_HEAT_SCORES hs
        WHERE hs.pwa_event_id = 370
    """)
    scores_exist = cursor.fetchone()[0]
    print(f"  Unique athletes with scores in database: {scores_exist}")

    if scores_exist > 0 and scores_exist != chile_data[1]:
        issues.append({
            'severity': 'HIGH',
            'category': 'Data Joining',
            'issue': f'Chile 2025: {scores_exist} athletes have scores but only {chile_data[1]} join to heat results',
            'recommendation': 'Check athlete_id format and joining logic'
        })

    # Tenerife 2025
    print_subsection("B. Tenerife 2025 (Event ID 376)")

    cursor.execute("""
        SELECT
            COUNT(*) as result_count,
            COUNT(DISTINCT division_code) as division_count
        FROM PWA_IWT_RESULTS
        WHERE event_id = 376
    """)

    tenerife_results = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) as heat_count
        FROM PWA_IWT_HEAT_RESULTS
        WHERE pwa_event_id = 376
    """)

    tenerife_heats = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) as score_count
        FROM PWA_IWT_HEAT_SCORES
        WHERE pwa_event_id = 376
    """)

    tenerife_scores = cursor.fetchone()[0]

    print(f"  Final results: {tenerife_results[0]} across {tenerife_results[1]} divisions")
    print(f"  Heat results: {tenerife_heats}")
    print(f"  Heat scores: {tenerife_scores}")

    if tenerife_results[0] > 0 and tenerife_heats == 0:
        issues.append({
            'severity': 'MEDIUM',
            'category': 'Missing Data',
            'issue': f'Tenerife 2025: Has {tenerife_results[0]} final results but no heat data',
            'recommendation': 'Scrape heat data from source or mark as results-only event'
        })

    return issues

def generate_recommendations(all_issues):
    """Generate prioritized recommendations"""
    print_section("6. PRIORITIZED RECOMMENDATIONS")

    # Group by severity
    by_severity = defaultdict(list)
    for issue in all_issues:
        by_severity[issue['severity']].append(issue)

    severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

    for severity in severity_order:
        if severity in by_severity:
            print_subsection(f"{severity} Priority Issues ({len(by_severity[severity])})")
            for issue in by_severity[severity]:
                print(f"\n  Issue: {issue['issue']}")
                print(f"  Category: {issue.get('category', 'General')}")
                print(f"  Recommendation: {issue.get('recommendation', 'Manual review required')}")

    # Summary counts
    print_subsection("Summary")
    print(f"  Total Issues Found: {len(all_issues)}")
    for severity in severity_order:
        count = len(by_severity.get(severity, []))
        if count > 0:
            print(f"    {severity}: {count}")

def save_reports(coverage_data, all_issues):
    """Save analysis results to CSV files"""
    print_section("7. SAVING REPORTS")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = "data/reports"

    # Ensure reports directory exists
    os.makedirs(reports_dir, exist_ok=True)

    # Save event coverage matrix
    coverage_file = os.path.join(reports_dir, f"event_coverage_matrix_{timestamp}.csv")
    with open(coverage_file, 'w', newline='', encoding='utf-8') as f:
        if coverage_data:
            writer = csv.DictWriter(f, fieldnames=coverage_data[0].keys())
            writer.writeheader()
            writer.writerows(coverage_data)
    print(f"  Event coverage matrix saved: {coverage_file}")

    # Save issues report
    issues_file = os.path.join(reports_dir, f"data_quality_issues_{timestamp}.csv")
    with open(issues_file, 'w', newline='', encoding='utf-8') as f:
        if all_issues:
            fieldnames = ['severity', 'category', 'issue', 'recommendation']
            # Add optional fields
            for issue in all_issues:
                for key in issue.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_issues)
    print(f"  Issues report saved: {issues_file}")

def main():
    """Main execution"""
    print("="*100)
    print("WINDSURF WORLD TOUR STATS - DATA QUALITY ANALYSIS")
    print("="*100)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print("[OK] Connected successfully")

        all_issues = []

        # Run analyses
        summary = analyze_table_summary(cursor)
        coverage_data, coverage_issues = analyze_event_coverage(cursor)
        all_issues.extend(coverage_issues)

        field_issues = analyze_field_consistency(cursor)
        all_issues.extend(field_issues)

        athlete_issues = analyze_athlete_quality(cursor)
        all_issues.extend(athlete_issues)

        specific_issues = analyze_specific_issues(cursor)
        all_issues.extend(specific_issues)

        # Generate recommendations
        generate_recommendations(all_issues)

        # Save reports
        save_reports(coverage_data, all_issues)

        print("\n" + "="*100)
        print("ANALYSIS COMPLETE")
        print("="*100)
        print(f"\nTotal Issues Identified: {len(all_issues)}")
        print("Review the generated CSV reports in data/reports/ for detailed analysis")

    except mysql.connector.Error as err:
        print(f"\n[ERROR] DATABASE ERROR: {err}")
        return

    except Exception as e:
        print(f"\n[ERROR] {e}")
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
    main()
