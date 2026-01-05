"""
Generate Summary Script

Generates a human-readable summary of the daily update process for emails
and GitHub issue notifications.

Usage:
    python src/updates/generate_summary.py --staging-dir data/staging --output data/staging/update_summary.txt
"""

import argparse
import json
import os
import sys
from datetime import datetime


def load_json_file(file_path: str) -> dict:
    """Load JSON file, return empty dict if not found"""
    if not os.path.exists(file_path):
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_summary(staging_dir: str) -> str:
    """
    Generate summary text from staging directory files

    Args:
        staging_dir: Directory containing staging JSON files

    Returns:
        Formatted summary string
    """
    # Load all JSON files
    events_update = load_json_file(os.path.join(staging_dir, 'events_to_update.json'))
    change_report = load_json_file(os.path.join(staging_dir, 'change_report.json'))
    update_log = load_json_file(os.path.join(staging_dir, 'update_log.json'))
    scraping_errors = load_json_file(os.path.join(staging_dir, 'scraping_errors.json'))

    # Build summary
    lines = []
    lines.append("=" * 70)
    lines.append(f"PWA DAILY UPDATE SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    # Events to update
    total_events = events_update.get('total_events', 0)
    lines.append(f"EVENTS CHECKED: {total_events}")

    if total_events > 0:
        lines.append("")
        lines.append("Events updated:")
        for event in events_update.get('events', [])[:10]:  # Show first 10
            lines.append(f"  - [{event['year']}] {event['event_name']} (ID: {event['event_id']}) - {event['reason']}")

        if total_events > 10:
            lines.append(f"  ... and {total_events - 10} more")

    # Changes detected
    if change_report:
        lines.append("")
        lines.append("CHANGES DETECTED:")
        changes = change_report.get('changes', {})

        for data_type, counts in changes.items():
            if 'new' in counts and (counts['new'] > 0 or counts.get('updated', 0) > 0):
                lines.append(f"  {data_type.upper()}:")
                lines.append(f"    New: {counts['new']}")
                if 'updated' in counts:
                    lines.append(f"    Updated: {counts.get('updated', 0)}")

        # Validation issues
        validation_issues = change_report.get('total_validation_issues', 0)
        if validation_issues > 0:
            lines.append("")
            lines.append(f"VALIDATION WARNINGS: {validation_issues}")
            for issue in change_report.get('validation_issues', []):
                lines.append(f"  - {issue}")

    # Database updates
    if update_log:
        lines.append("")
        lines.append("DATABASE UPDATES:")

        for table, stats in update_log.get('tables_updated', {}).items():
            lines.append(f"  {table}:")
            lines.append(f"    Records before: {stats['records_before']}")
            lines.append(f"    Records after: {stats['records_after']}")
            lines.append(f"    New records: {stats['new']}")
            lines.append(f"    Execution time: {stats['execution_time_seconds']}s")

        # Errors
        db_errors = update_log.get('errors', [])
        if db_errors:
            lines.append("")
            lines.append(f"DATABASE ERRORS: {len(db_errors)}")
            for error in db_errors:
                lines.append(f"  - {error['table']}: {error['error']}")

    # Scraping errors
    if scraping_errors:
        total_errors = scraping_errors.get('total_errors', 0)
        if total_errors > 0:
            lines.append("")
            lines.append(f"SCRAPING ERRORS: {total_errors}")
            for error in scraping_errors.get('errors', []):
                lines.append(f"  - {error['stage']}: {error['error']}")

    # Overall status
    lines.append("")
    lines.append("=" * 70)

    has_errors = (
        scraping_errors.get('total_errors', 0) > 0 or
        len(update_log.get('errors', [])) > 0 or
        change_report.get('issue_percentage', 0) > 10
    )

    if has_errors:
        lines.append("STATUS: COMPLETED WITH ERRORS ⚠️")
    elif total_events == 0:
        lines.append("STATUS: NO UPDATES NEEDED ✓")
    else:
        lines.append("STATUS: SUCCESS ✓")

    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate update summary for notifications'
    )
    parser.add_argument(
        '--staging-dir',
        type=str,
        default='data/staging',
        help='Directory with staging JSON files (default: data/staging)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/staging/update_summary.txt',
        help='Output path for summary text (default: data/staging/update_summary.txt)'
    )

    args = parser.parse_args()

    # Generate summary
    summary = generate_summary(args.staging_dir)

    # Save to file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(summary)

    # Print to console
    print(summary)

    sys.exit(0)


if __name__ == '__main__':
    main()
