"""
Detect Changes Script

Compares staged CSV files with existing database records to identify actual changes.
Validates data quality before allowing database updates.

Usage:
    python src/updates/detect_changes.py --staging-dir data/staging --output data/staging/change_report.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List
import pandas as pd
import mysql.connector
from dotenv import load_dotenv


class ChangeDetector:
    """Detect and validate changes in staged data"""

    def __init__(self, staging_dir: str):
        """
        Initialize change detector

        Args:
            staging_dir: Directory containing staged CSV files
        """
        self.staging_dir = staging_dir
        self.db_conn = None
        self.validation_issues = []
        self.changes = {
            'events': {'new': 0, 'updated': 0, 'unchanged': 0},
            'results': {'new': 0, 'updated': 0},
            'heat_progression': {'new': 0, 'updated': 0},
            'heat_results': {'new': 0, 'updated': 0},
            'heat_scores': {'new': 0, 'updated': 0}
        }

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def connect_to_database(self):
        """Connect to MySQL database"""
        load_dotenv()

        self.log("Connecting to database...")
        try:
            self.db_conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '3306')),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                connect_timeout=30
            )
            self.log("Database connected")
            return True
        except mysql.connector.Error as e:
            self.log(f"ERROR: Database connection failed: {e}", "ERROR")
            return False

    def validate_events(self, df: pd.DataFrame) -> List[str]:
        """Validate events data"""
        issues = []

        if df.empty:
            return issues

        # Check for null event names
        null_names = df['event_name'].isnull().sum()
        if null_names > 0:
            issues.append(f"Events: {null_names} records with null event_name")

        # Check for invalid status codes
        # Valid statuses: 0 (TBC), 1 (Upcoming), 2 (In Progress), 3 (Completed)
        valid_statuses = [0, 1, 2, 3]
        invalid_status = df[~df['event_status'].isin(valid_statuses) & df['event_status'].notna()].shape[0]
        if invalid_status > 0:
            issues.append(f"Events: {invalid_status} records with invalid event_status")

        return issues

    def validate_results(self, df: pd.DataFrame) -> List[str]:
        """Validate results data"""
        issues = []

        if df.empty:
            return issues

        # Check for null athlete names
        null_athletes = df['athlete_name'].isnull().sum()
        if null_athletes > 0:
            issues.append(f"Results: {null_athletes} records with null athlete_name")

        # Check for null placements
        null_place = df['place'].isnull().sum()
        if null_place > 0:
            issues.append(f"Results: {null_place} records with null place")

        return issues

    def validate_heat_scores(self, df: pd.DataFrame) -> List[str]:
        """Validate heat scores data"""
        issues = []

        if df.empty:
            return issues

        # Check for scores out of range (0-10)
        if 'score' in df.columns:
            df['score'] = pd.to_numeric(df['score'], errors='coerce')
            out_of_range = df[(df['score'] < 0) | (df['score'] > 10)].shape[0]
            if out_of_range > 0:
                issues.append(f"Heat Scores: {out_of_range} records with score outside 0-10 range")

        # Check for null athlete IDs
        null_athletes = df['athlete_id'].isnull().sum()
        if null_athletes > 0:
            issues.append(f"Heat Scores: {null_athletes} records with null athlete_id")

        return issues

    def count_new_records(self, table_name: str, source_filter: str, staged_df: pd.DataFrame, id_columns: List[str]) -> Dict[str, int]:
        """
        Count new vs updated records by comparing with database

        Args:
            table_name: Database table name
            source_filter: Value for source column filter
            staged_df: DataFrame with staged data
            id_columns: List of column names that form the unique key

        Returns:
            Dict with 'new' and 'updated' counts
        """
        if staged_df.empty:
            return {'new': 0, 'updated': 0}

        try:
            cursor = self.db_conn.cursor(dictionary=True)

            # Get existing IDs from database
            id_cols_str = ', '.join(id_columns)
            query = f"SELECT {id_cols_str} FROM {table_name} WHERE source = %s"
            cursor.execute(query, (source_filter,))
            existing_records = cursor.fetchall()
            cursor.close()

            # Create set of existing tuples
            existing_keys = set()
            for record in existing_records:
                key = tuple(str(record[col]) for col in id_columns)
                existing_keys.add(key)

            # Compare with staged data
            new_count = 0
            updated_count = 0

            for _, row in staged_df.iterrows():
                key = tuple(str(row[col]) if pd.notna(row[col]) else '' for col in id_columns)
                if key in existing_keys:
                    updated_count += 1
                else:
                    new_count += 1

            return {'new': new_count, 'updated': updated_count}

        except Exception as e:
            self.log(f"ERROR counting records for {table_name}: {e}", "WARNING")
            return {'new': 0, 'updated': 0}

    def analyze_changes(self):
        """Analyze all staged files and compare with database"""
        self.log("Analyzing changes in staged files...")

        # Load and validate events
        events_file = os.path.join(self.staging_dir, 'events_incremental.csv')
        if os.path.exists(events_file):
            events_df = pd.read_csv(events_file)
            self.log(f"Loaded {len(events_df)} staged events")

            # Validate
            issues = self.validate_events(events_df)
            self.validation_issues.extend(issues)

            # Count changes
            counts = self.count_new_records(
                'PWA_IWT_EVENTS',
                'PWA',
                events_df,
                ['event_id']
            )
            self.changes['events']['new'] = counts['new']
            self.changes['events']['updated'] = counts['updated']

        # Load and validate results
        results_file = os.path.join(self.staging_dir, 'results_incremental.csv')
        if os.path.exists(results_file):
            results_df = pd.read_csv(results_file)
            self.log(f"Loaded {len(results_df)} staged results")

            # Validate
            issues = self.validate_results(results_df)
            self.validation_issues.extend(issues)

            # Count changes
            counts = self.count_new_records(
                'PWA_IWT_RESULTS',
                'PWA',
                results_df,
                ['event_id', 'division_code', 'athlete_id', 'place']
            )
            self.changes['results']['new'] = counts['new']
            self.changes['results']['updated'] = counts['updated']

        # Load and validate heat scores
        scores_file = os.path.join(self.staging_dir, 'heat_scores_incremental.csv')
        if os.path.exists(scores_file):
            scores_df = pd.read_csv(scores_file)
            self.log(f"Loaded {len(scores_df)} staged heat scores")

            # Validate
            issues = self.validate_heat_scores(scores_df)
            self.validation_issues.extend(issues)

            # Count changes (simplified for heat scores)
            self.changes['heat_scores']['new'] = len(scores_df)

    def generate_report(self, output_path: str):
        """Generate change report JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'staging_dir': self.staging_dir,
            'changes': self.changes,
            'validation_issues': self.validation_issues,
            'total_validation_issues': len(self.validation_issues),
            'total_new_records': sum(c['new'] for c in self.changes.values() if 'new' in c),
            'total_updated_records': sum(c['updated'] for c in self.changes.values() if 'updated' in c)
        }

        # Calculate issue percentage
        total_records = report['total_new_records'] + report['total_updated_records']
        if total_records > 0:
            issue_percentage = (len(self.validation_issues) / total_records) * 100
            report['issue_percentage'] = round(issue_percentage, 2)
        else:
            report['issue_percentage'] = 0.0

        # Save report
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        self.log(f"Change report saved to: {output_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("CHANGE DETECTION SUMMARY")
        print("=" * 60)
        print(f"Total new records: {report['total_new_records']}")
        print(f"Total updated records: {report['total_updated_records']}")
        print(f"Validation issues: {report['total_validation_issues']}")
        if report['total_validation_issues'] > 0:
            print("\nIssues found:")
            for issue in self.validation_issues:
                print(f"  - {issue}")
        print(f"\nIssue percentage: {report['issue_percentage']}%")
        print("=" * 60)

        # Check quality gate (10% threshold)
        if report['issue_percentage'] > 10.0:
            self.log(f"QUALITY GATE FAILED: {report['issue_percentage']}% > 10% threshold", "ERROR")
            return False

        self.log("Quality gate passed", "INFO")
        return True

    def run(self, output_path: str):
        """
        Run change detection

        Args:
            output_path: Path to save change report JSON

        Returns:
            bool: True if quality gate passed, False otherwise
        """
        try:
            if not self.connect_to_database():
                return False

            self.analyze_changes()
            passed = self.generate_report(output_path)

            return passed

        except Exception as e:
            self.log(f"ERROR during change detection: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.db_conn:
                self.db_conn.close()
                self.log("Database connection closed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Detect and validate changes in staged data'
    )
    parser.add_argument(
        '--staging-dir',
        type=str,
        default='data/staging',
        help='Directory with staged CSV files (default: data/staging)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/staging/change_report.json',
        help='Output path for change report JSON (default: data/staging/change_report.json)'
    )

    args = parser.parse_args()

    detector = ChangeDetector(args.staging_dir)
    success = detector.run(args.output)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
