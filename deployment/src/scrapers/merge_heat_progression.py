"""
Merge Heat Progression/Structure Data from PWA and LiveHeats Sources
Combines PWA heat structure and LiveHeats heat progression into unified dataset
Output: Unified heat progression CSV
"""

import os
import pandas as pd
from datetime import datetime


class HeatProgressionMerger:
    """Merge heat progression/structure data from PWA and LiveHeats sources"""

    def __init__(self, pwa_structure_path, lh_progression_path):
        """
        Initialize merger

        Args:
            pwa_structure_path: Path to PWA heat structure CSV
            lh_progression_path: Path to LiveHeats heat progression CSV
        """
        self.pwa_structure_path = pwa_structure_path
        self.lh_progression_path = lh_progression_path
        self.merged_data = None

        self.stats = {
            'pwa_records': 0,
            'liveheats_records': 0,
            'total_merged': 0
        }

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_pwa_structure(self):
        """Load PWA heat structure data"""
        self.log("Loading PWA heat structure...")

        if not os.path.exists(self.pwa_structure_path):
            self.log(f"PWA structure file not found: {self.pwa_structure_path}", "WARNING")
            return pd.DataFrame()

        df = pd.read_csv(self.pwa_structure_path)
        self.stats['pwa_records'] = len(df)
        self.log(f"Loaded {len(df)} PWA heat structure records")

        return df

    def load_lh_progression(self):
        """Load LiveHeats heat progression data"""
        self.log("Loading LiveHeats heat progression...")

        if not os.path.exists(self.lh_progression_path):
            self.log(f"LiveHeats progression file not found: {self.lh_progression_path}", "WARNING")
            return pd.DataFrame()

        df = pd.read_csv(self.lh_progression_path)
        self.stats['liveheats_records'] = len(df)
        self.log(f"Loaded {len(df)} LiveHeats heat progression records")

        return df

    def standardize_pwa_columns(self, df):
        """
        Standardize PWA columns to unified schema

        Args:
            df: PWA DataFrame

        Returns:
            Standardized DataFrame
        """
        self.log("Standardizing PWA columns...")

        # Add missing columns for LiveHeats-specific fields
        df['pwa_year'] = df['event_id'].astype(str).str[:4].astype(int)  # Extract year from event_id
        df['pwa_event_name'] = ''  # Will be populated if needed
        df['liveheats_event_id'] = ''
        df['liveheats_division_id'] = ''
        df['division_name'] = ''

        # Rename columns to match unified schema
        df = df.rename(columns={
            'event_id': 'pwa_event_id',
            'division_code': 'pwa_division_code'
        })

        # Ensure required columns exist
        required_cols = [
            'source', 'scraped_at', 'pwa_event_id', 'pwa_year', 'pwa_event_name',
            'pwa_division_code', 'sex', 'elimination_name', 'round_name', 'round_order',
            'heat_id', 'heat_order', 'total_winners_progressing',
            'winners_progressing_to_round_order', 'total_losers_progressing',
            'losers_progressing_to_round_order', 'liveheats_event_id',
            'liveheats_division_id', 'division_name'
        ]

        # Add any missing columns
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''

        return df[required_cols]

    def standardize_lh_columns(self, df):
        """
        Standardize LiveHeats columns to unified schema

        Args:
            df: LiveHeats DataFrame

        Returns:
            Standardized DataFrame
        """
        self.log("Standardizing LiveHeats columns...")

        # Add missing columns for PWA-specific fields
        df['pwa_division_code'] = ''
        df['elimination_name'] = ''
        df['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Ensure required columns exist
        required_cols = [
            'source', 'scraped_at', 'pwa_event_id', 'pwa_year', 'pwa_event_name',
            'pwa_division_code', 'sex', 'elimination_name', 'round_name', 'round_order',
            'heat_id', 'heat_order', 'total_winners_progressing',
            'winners_progressing_to_round_order', 'total_losers_progressing',
            'losers_progressing_to_round_order', 'liveheats_event_id',
            'liveheats_division_id', 'division_name'
        ]

        # Add any missing columns
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''

        return df[required_cols]

    def merge_data(self, pwa_df, lh_df):
        """
        Merge PWA and LiveHeats data

        Args:
            pwa_df: Standardized PWA DataFrame
            lh_df: Standardized LiveHeats DataFrame

        Returns:
            Merged DataFrame
        """
        self.log("\nMerging heat progression data...")

        # Since these are different events, just concatenate
        merged_df = pd.concat([pwa_df, lh_df], ignore_index=True)

        self.stats['total_merged'] = len(merged_df)

        self.log(f"  Merged {self.stats['pwa_records']} PWA + {self.stats['liveheats_records']} LiveHeats records")
        self.log(f"  Total: {self.stats['total_merged']} records")

        return merged_df

    def sort_results(self, df):
        """
        Sort merged results by year, event, round

        Args:
            df: Merged DataFrame

        Returns:
            Sorted DataFrame
        """
        self.log("Sorting results...")

        # Convert to numeric for sorting
        df['pwa_year'] = pd.to_numeric(df['pwa_year'], errors='coerce').fillna(0).astype(int)
        df['pwa_event_id'] = pd.to_numeric(df['pwa_event_id'], errors='coerce').fillna(0).astype(int)
        df['round_order'] = pd.to_numeric(df['round_order'], errors='coerce').fillna(0).astype(int)
        df['heat_order'] = pd.to_numeric(df['heat_order'], errors='coerce').fillna(0).astype(int)

        # Sort by: year (desc), event_id, round_order, heat_order
        df = df.sort_values(
            by=['pwa_year', 'pwa_event_id', 'round_order', 'heat_order'],
            ascending=[False, True, True, True]
        )

        return df

    def run_merge(self):
        """Execute complete merge process"""
        self.log("\n" + "="*80)
        self.log("HEAT PROGRESSION MERGE - STARTING")
        self.log("="*80 + "\n")

        # Step 1: Load data
        pwa_df = self.load_pwa_structure()
        lh_df = self.load_lh_progression()

        if pwa_df.empty and lh_df.empty:
            self.log("ERROR: No data to merge!", "ERROR")
            return None

        # Step 2: Standardize columns
        if not pwa_df.empty:
            pwa_df = self.standardize_pwa_columns(pwa_df)

        if not lh_df.empty:
            lh_df = self.standardize_lh_columns(lh_df)

        # Step 3: Merge
        merged_df = self.merge_data(pwa_df, lh_df)

        # Step 4: Sort
        merged_df = self.sort_results(merged_df)

        self.merged_data = merged_df

        return merged_df

    def save_merged_data(self, output_path):
        """Save merged data to CSV"""
        if self.merged_data is None or self.merged_data.empty:
            self.log("No merged data to save!", "WARNING")
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        self.merged_data.to_csv(output_path, index=False, encoding='utf-8-sig')

        self.log(f"\nMerged heat progression saved to: {output_path}")
        self.log(f"Total rows: {len(self.merged_data)}")

    def print_summary(self):
        """Print merge statistics"""
        self.log("\n" + "="*80)
        self.log("MERGE SUMMARY STATISTICS")
        self.log("="*80)
        self.log(f"PWA Records Loaded: {self.stats['pwa_records']}")
        self.log(f"Live Heats Records Loaded: {self.stats['liveheats_records']}")
        self.log(f"")
        self.log(f"TOTAL MERGED RECORDS: {self.stats['total_merged']}")
        self.log("="*80 + "\n")

        if self.merged_data is not None:
            # Source breakdown
            source_counts = self.merged_data['source'].value_counts()
            self.log("Records by Source:")
            for source, count in source_counts.items():
                self.log(f"  {source}: {count}")

            # Year breakdown
            year_counts = self.merged_data['pwa_year'].value_counts().sort_index(ascending=False)
            self.log("\nRecords by Year:")
            for year, count in year_counts.items():
                if year > 0:
                    self.log(f"  {int(year)}: {count}")


def main():
    """Main execution"""
    print("="*80)
    print("HEAT PROGRESSION MERGER - PWA + LIVE HEATS")
    print("="*80)
    print()

    # Get project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Input paths
    pwa_structure = os.path.join(project_root, 'data', 'raw', 'pwa', 'pwa_heat_structure.csv')
    lh_progression = os.path.join(project_root, 'data', 'raw', 'liveheats', 'liveheats_heat_progression.csv')

    # Output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(project_root, 'data', 'processed', f'heat_progression_merged_{timestamp}.csv')
    standard_output = os.path.join(project_root, 'data', 'processed', 'heat_progression_merged.csv')

    # Initialize merger
    merger = HeatProgressionMerger(pwa_structure, lh_progression)

    try:
        # Run merge
        merged_df = merger.run_merge()

        if merged_df is not None:
            # Save results to timestamped file
            merger.save_merged_data(output_path)

            # Try to save to standard filename
            try:
                merger.save_merged_data(standard_output)
            except PermissionError:
                merger.log(f"Could not overwrite {standard_output} (file may be open)", "WARNING")

            # Print summary
            merger.print_summary()

        print("\n" + "="*80)
        print("MERGE COMPLETE!")
        print("="*80)

    except Exception as e:
        merger.log(f"FATAL ERROR: {e}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
