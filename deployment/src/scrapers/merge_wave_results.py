"""
Merge Wave Results from PWA and Live Heats Sources
Combines PWA results and Live Heats results into unified dataset
Handles deduplication and prioritization
Output: Unified wave results CSV matching pwa_wave_results_updated format
"""

import os
import pandas as pd
from datetime import datetime


class WaveResultsMerger:
    """Merge wave results from PWA and Live Heats sources"""

    def __init__(self, pwa_results_path, liveheats_results_path):
        """
        Initialize merger

        Args:
            pwa_results_path: Path to PWA results CSV
            liveheats_results_path: Path to Live Heats results CSV
        """
        self.pwa_results_path = pwa_results_path
        self.liveheats_results_path = liveheats_results_path
        self.merged_data = None

        self.stats = {
            'pwa_records': 0,
            'liveheats_records': 0,
            'total_merged': 0,
            'pwa_only_events': 0,
            'liveheats_only_events': 0,
            'overlapping_events': 0,
            'duplicates_removed': 0
        }

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_pwa_results(self):
        """
        Load PWA results

        Returns:
            DataFrame of PWA results
        """
        self.log("Loading PWA results...")

        if not os.path.exists(self.pwa_results_path):
            self.log(f"PWA results file not found: {self.pwa_results_path}", "WARNING")
            return pd.DataFrame()

        df = pd.read_csv(self.pwa_results_path)
        self.stats['pwa_records'] = len(df)
        self.log(f"Loaded {len(df)} PWA result records")

        return df

    def load_liveheats_results(self):
        """
        Load Live Heats results

        Returns:
            DataFrame of Live Heats results
        """
        self.log("Loading Live Heats results...")

        if not os.path.exists(self.liveheats_results_path):
            self.log(f"Live Heats results file not found: {self.liveheats_results_path}", "WARNING")
            return pd.DataFrame()

        df = pd.read_csv(self.liveheats_results_path)
        self.stats['liveheats_records'] = len(df)
        self.log(f"Loaded {len(df)} Live Heats result records")

        return df

    def standardize_columns(self, df, source):
        """
        Ensure all required columns exist and are in correct order

        Args:
            df: DataFrame to standardize
            source: 'PWA' or 'Live Heats'

        Returns:
            Standardized DataFrame
        """
        # Required columns in target format
        required_cols = [
            'source', 'scraped_at', 'event_id', 'year', 'event_name',
            'division_label', 'division_code', 'sex', 'place',
            'athlete_name', 'sail_number', 'athlete_id'
        ]

        # Add missing columns
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
                self.log(f"Added missing column '{col}' to {source} results", "WARNING")

        # Ensure correct order
        df = df[required_cols]

        # Clean data types
        df['event_id'] = df['event_id'].astype(str)
        df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
        df['place'] = df['place'].astype(str)
        df['athlete_id'] = df['athlete_id'].astype(str)

        return df

    def identify_overlapping_divisions(self, pwa_df, lh_df):
        """
        Identify divisions (event_id + sex) that exist in both PWA and Live Heats
        Determine which source has more data for each overlapping division

        Args:
            pwa_df: PWA results DataFrame
            lh_df: Live Heats results DataFrame

        Returns:
            Dict mapping (event_id, sex) to preferred source ('pwa' or 'liveheats')
        """
        # Create unique division keys: (event_id, sex)
        pwa_df['division_key'] = pwa_df['event_id'] + '_' + pwa_df['sex']
        lh_df['division_key'] = lh_df['event_id'] + '_' + lh_df['sex']

        pwa_divisions = set(pwa_df['division_key'].unique())
        lh_divisions = set(lh_df['division_key'].unique())

        overlapping = pwa_divisions.intersection(lh_divisions)

        self.stats['pwa_only_events'] = len(pwa_divisions - lh_divisions)
        self.stats['liveheats_only_events'] = len(lh_divisions - pwa_divisions)
        self.stats['overlapping_events'] = len(overlapping)

        # For each overlapping division, determine which source has more data
        division_preferences = {}

        if overlapping:
            self.log(f"\nFound {len(overlapping)} divisions in BOTH sources:")
            for div_key in sorted(overlapping):
                pwa_div = pwa_df[pwa_df['division_key'] == div_key]
                lh_div = lh_df[lh_df['division_key'] == div_key]

                pwa_count = len(pwa_div)
                lh_count = len(lh_div)

                event_id = pwa_div['event_id'].iloc[0]
                sex = pwa_div['sex'].iloc[0]
                event_name = pwa_div['event_name'].iloc[0]

                # Prefer the source with more data
                if lh_count > pwa_count:
                    preferred = 'liveheats'
                    self.log(f"  Event {event_id} {sex}: LIVE HEATS ({lh_count} vs {pwa_count} results)")
                else:
                    preferred = 'pwa'
                    self.log(f"  Event {event_id} {sex}: PWA ({pwa_count} vs {lh_count} results)")

                self.log(f"    {event_name}")

                division_preferences[div_key] = preferred

        return division_preferences

    def merge_results(self, pwa_df, lh_df, division_preferences):
        """
        Merge PWA and Live Heats results with smart deduplication by division

        Strategy:
        - For overlapping divisions (event_id + sex), use whichever source has MORE data
        - Include all unique divisions from both sources

        Args:
            pwa_df: PWA results DataFrame (with division_key column)
            lh_df: Live Heats results DataFrame (with division_key column)
            division_preferences: Dict mapping division_key to preferred source

        Returns:
            Merged DataFrame
        """
        self.log("\nMerging results with smart deduplication by division...")

        # Division keys to exclude from each source
        pwa_exclude = set()
        lh_exclude = set()

        for div_key, preferred in division_preferences.items():
            if preferred == 'liveheats':
                pwa_exclude.add(div_key)
                self.log(f"  Division {div_key}: Using Live Heats data")
            else:
                lh_exclude.add(div_key)
                self.log(f"  Division {div_key}: Using PWA data")

        # Filter out excluded divisions
        pwa_to_keep = pwa_df[~pwa_df['division_key'].isin(pwa_exclude)].copy()
        lh_to_keep = lh_df[~lh_df['division_key'].isin(lh_exclude)].copy()

        # Calculate stats
        pwa_removed = len(pwa_df) - len(pwa_to_keep)
        lh_removed = len(lh_df) - len(lh_to_keep)
        self.stats['duplicates_removed'] = pwa_removed + lh_removed

        self.log(f"\n  Removed {pwa_removed} PWA records (inferior to Live Heats)")
        self.log(f"  Removed {lh_removed} Live Heats records (inferior to PWA)")

        # Drop the division_key column before merging
        pwa_to_keep = pwa_to_keep.drop(columns=['division_key'])
        lh_to_keep = lh_to_keep.drop(columns=['division_key'])

        # Merge the filtered dataframes
        merged_df = pd.concat([pwa_to_keep, lh_to_keep], ignore_index=True)

        self.stats['total_merged'] = len(merged_df)

        return merged_df

    def sort_results(self, df):
        """
        Sort merged results by year, event, division, place

        Args:
            df: Merged DataFrame

        Returns:
            Sorted DataFrame
        """
        self.log("Sorting results...")

        # Convert place to numeric for sorting (handle ties like "5" and "5")
        df['place_numeric'] = pd.to_numeric(df['place'], errors='coerce')

        # Sort by: year (desc), event_id, division_label, place
        df = df.sort_values(
            by=['year', 'event_id', 'division_label', 'place_numeric'],
            ascending=[False, True, True, True]
        )

        # Drop temporary column
        df = df.drop(columns=['place_numeric'])

        return df

    def run_merge(self):
        """
        Execute complete merge process with smart deduplication

        Returns:
            Merged DataFrame
        """
        self.log("\n" + "="*80)
        self.log("WAVE RESULTS MERGE - STARTING")
        self.log("="*80 + "\n")

        # Step 1: Load data
        pwa_df = self.load_pwa_results()
        lh_df = self.load_liveheats_results()

        if pwa_df.empty and lh_df.empty:
            self.log("ERROR: No data to merge!", "ERROR")
            return None

        # Step 2: Standardize columns
        if not pwa_df.empty:
            pwa_df = self.standardize_columns(pwa_df, 'PWA')

        if not lh_df.empty:
            lh_df = self.standardize_columns(lh_df, 'Live Heats')

        # Step 3: Identify overlaps and determine best source for each division
        division_preferences = self.identify_overlapping_divisions(pwa_df, lh_df)

        # Step 4: Merge with smart deduplication by division
        merged_df = self.merge_results(pwa_df, lh_df, division_preferences)

        # Step 5: Sort
        merged_df = self.sort_results(merged_df)

        self.merged_data = merged_df

        return merged_df

    def save_merged_results(self, output_path):
        """
        Save merged results to CSV

        Args:
            output_path: Path to output CSV file
        """
        if self.merged_data is None or self.merged_data.empty:
            self.log("No merged data to save!", "WARNING")
            return

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save to CSV
        self.merged_data.to_csv(output_path, index=False, encoding='utf-8-sig')

        self.log(f"\nMerged results saved to: {output_path}")
        self.log(f"Total rows: {len(self.merged_data)}")

    def print_summary(self):
        """Print merge statistics"""
        self.log("\n" + "="*80)
        self.log("MERGE SUMMARY STATISTICS")
        self.log("="*80)
        self.log(f"PWA Records Loaded: {self.stats['pwa_records']}")
        self.log(f"Live Heats Records Loaded: {self.stats['liveheats_records']}")
        self.log(f"")
        self.log(f"PWA-Only Events: {self.stats['pwa_only_events']}")
        self.log(f"Live Heats-Only Events: {self.stats['liveheats_only_events']}")
        self.log(f"Overlapping Events: {self.stats['overlapping_events']}")
        self.log(f"Duplicate Records Removed: {self.stats['duplicates_removed']}")
        self.log(f"")
        self.log(f"TOTAL MERGED RECORDS: {self.stats['total_merged']}")
        self.log("="*80 + "\n")

        if self.merged_data is not None:
            # Event breakdown by source
            source_counts = self.merged_data['source'].value_counts()
            self.log("Records by Source:")
            for source, count in source_counts.items():
                self.log(f"  {source}: {count}")

            # Year breakdown
            year_counts = self.merged_data['year'].value_counts().sort_index(ascending=False)
            self.log("\nRecords by Year:")
            for year, count in year_counts.items():
                if year > 0:  # Skip invalid years
                    self.log(f"  {int(year)}: {count}")

            # Division breakdown
            div_counts = self.merged_data.groupby(['division_label', 'sex']).size()
            self.log("\nRecords by Division:")
            for (div, sex), count in div_counts.items():
                self.log(f"  {div} ({sex}): {count}")


def main():
    """Main execution"""
    print("="*80)
    print("WAVE RESULTS MERGER - PWA + LIVE HEATS")
    print("="*80)
    print()

    # Get project root (assuming script is in src/scrapers/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Input paths
    pwa_results = os.path.join(project_root, 'data', 'raw', 'pwa', 'pwa_wave_results_updated.csv')
    lh_results = os.path.join(project_root, 'data', 'raw', 'liveheats', 'liveheats_matched_results.csv')

    # Output path (with timestamp to avoid conflicts)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(project_root, 'data', 'processed', f'wave_results_merged_{timestamp}.csv')

    # Also save as the standard filename
    standard_output = os.path.join(project_root, 'data', 'processed', 'wave_results_merged.csv')

    # Initialize merger
    merger = WaveResultsMerger(pwa_results, lh_results)

    try:
        # Run merge with smart deduplication (keeps whichever source has more data)
        merged_df = merger.run_merge()

        if merged_df is not None:
            # Save results to timestamped file
            merger.save_merged_results(output_path)

            # Try to save to standard filename (may fail if file is open)
            try:
                merger.save_merged_results(standard_output)
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
