"""
Merge all athlete data into final unified tables.

This script combines:
- High-confidence matches (>=90%)
- Manual review decisions
- PWA-only athletes
- LiveHeats-only athletes

Outputs:
- athletes_final.csv: Master athlete list with unified IDs
- athlete_ids_link.csv: Link table mapping unified IDs to source IDs
"""

import pandas as pd
import os

def load_manual_decisions():
    """
    Load manual match decisions if file exists.

    Returns:
        DataFrame with manual decisions or empty DataFrame
    """
    manual_file = 'data/processed/athletes/manual_match_decisions.csv'

    if os.path.exists(manual_file):
        df = pd.read_csv(manual_file)
        print(f"[OK] Loaded manual decisions: {len(df)} records")
        return df
    else:
        print("  No manual decisions file found (this is OK if first run)")
        return pd.DataFrame(columns=['lh_athlete_id', 'pwa_athlete_id', 'lh_name', 'pwa_name', 'score', 'stage', 'decision'])

def merge_athlete_data(matches_df, pwa_df, lh_df):
    """
    Merge matched athletes with full profile data from both sources.

    Args:
        matches_df: DataFrame with matches
        pwa_df: PWA athletes DataFrame
        lh_df: LiveHeats athletes DataFrame

    Returns:
        DataFrame with merged athlete data
    """
    print("\nMerging athlete profile data...")

    # Join matches with LiveHeats data
    merged = matches_df.merge(
        lh_df,
        left_on='lh_athlete_id',
        right_on='athlete_id',
        how='left',
        suffixes=('', '_lh')
    )

    # Join with PWA data
    merged = merged.merge(
        pwa_df,
        left_on='pwa_athlete_id',
        right_on='athlete_id',
        how='left',
        suffixes=('_lh', '_pwa')
    )

    # Select and rename key columns
    final = pd.DataFrame({
        'lh_athlete_id': merged['lh_athlete_id'],
        'pwa_athlete_id': merged['pwa_athlete_id'],
        'lh_name': merged['lh_name'],
        'pwa_name': merged['pwa_name'],
        'match_score': merged['score'],
        'match_stage': merged['stage'],

        # LiveHeats data
        'lh_image_url': merged.get('image_url'),
        'lh_dob': merged.get('dob'),
        'lh_nationality': merged.get('nationality_lh'),
        'lh_year_of_birth': merged.get('year_of_birth_lh'),

        # PWA data
        'pwa_sail_number': merged.get('sail_number'),
        'pwa_profile_url': merged.get('profile_url'),
        'pwa_nationality': merged.get('nationality_pwa'),
        'pwa_sponsors': merged.get('sponsors'),
        'pwa_year_of_birth': merged.get('year_of_birth_pwa'),
    })

    # Determine primary name (prefer LiveHeats if available, fallback to PWA)
    final['primary_name'] = final['lh_name'].fillna(final['pwa_name'])

    # Determine best year of birth (prefer LiveHeats DOB-based, fallback to PWA calculated)
    final['year_of_birth'] = final['lh_year_of_birth'].fillna(final['pwa_year_of_birth'])

    # Determine best nationality (prefer LiveHeats)
    final['nationality'] = final['lh_nationality'].fillna(final['pwa_nationality'])

    return final

def create_pwa_only_records(pwa_only_df):
    """
    Create athlete records for PWA-only athletes (not matched to LiveHeats).

    Args:
        pwa_only_df: DataFrame with unmatched PWA athletes

    Returns:
        DataFrame with athlete records
    """
    print(f"\nCreating records for {len(pwa_only_df)} PWA-only athletes...")

    records = pd.DataFrame({
        'lh_athlete_id': None,
        'pwa_athlete_id': pwa_only_df['athlete_id'],
        'lh_name': None,
        'pwa_name': pwa_only_df['name'],
        'match_score': None,
        'match_stage': 'PWA_only',

        # LiveHeats data (all None)
        'lh_image_url': None,
        'lh_dob': None,
        'lh_nationality': None,
        'lh_year_of_birth': None,

        # PWA data
        'pwa_sail_number': pwa_only_df['sail_number'],
        'pwa_profile_url': pwa_only_df['profile_url'],
        'pwa_nationality': pwa_only_df['nationality'],
        'pwa_sponsors': pwa_only_df.get('sponsors'),
        'pwa_year_of_birth': pwa_only_df.get('year_of_birth'),

        # Primary fields
        'primary_name': pwa_only_df['name'],
        'year_of_birth': pwa_only_df.get('year_of_birth'),
        'nationality': pwa_only_df['nationality'],
    })

    return records

def create_liveheats_only_records(lh_only_df):
    """
    Create athlete records for LiveHeats-only athletes (not matched to PWA).

    Args:
        lh_only_df: DataFrame with unmatched LiveHeats athletes

    Returns:
        DataFrame with athlete records
    """
    print(f"\nCreating records for {len(lh_only_df)} LiveHeats-only athletes...")

    records = pd.DataFrame({
        'lh_athlete_id': lh_only_df['athlete_id'],
        'pwa_athlete_id': None,
        'lh_name': lh_only_df['name'],
        'pwa_name': None,
        'match_score': None,
        'match_stage': 'LiveHeats_only',

        # LiveHeats data
        'lh_image_url': lh_only_df.get('image_url'),
        'lh_dob': lh_only_df.get('dob'),
        'lh_nationality': lh_only_df.get('nationality'),
        'lh_year_of_birth': lh_only_df.get('year_of_birth'),

        # PWA data (all None)
        'pwa_sail_number': None,
        'pwa_profile_url': None,
        'pwa_nationality': None,
        'pwa_sponsors': None,
        'pwa_year_of_birth': None,

        # Primary fields
        'primary_name': lh_only_df['name'],
        'year_of_birth': lh_only_df.get('year_of_birth'),
        'nationality': lh_only_df.get('nationality'),
    })

    return records

def create_link_table(athletes_df):
    """
    Create link table mapping unified athlete IDs to source-specific IDs.

    Args:
        athletes_df: DataFrame with final athlete records (must have 'id' column)

    Returns:
        DataFrame in long format with columns: athlete_id, source, source_id
    """
    print("\nCreating link table...")

    links = []

    for _, row in athletes_df.iterrows():
        athlete_id = row['id']

        # Add LiveHeats ID if present
        if pd.notna(row['lh_athlete_id']):
            links.append({
                'athlete_id': athlete_id,
                'source': 'Live Heats',
                'source_id': str(row['lh_athlete_id'])
            })

        # Add PWA ID if present
        if pd.notna(row['pwa_athlete_id']):
            links.append({
                'athlete_id': athlete_id,
                'source': 'PWA',
                'source_id': str(row['pwa_athlete_id'])
            })

        # Add PWA sail number if different from athlete_id
        if pd.notna(row['pwa_sail_number']) and str(row['pwa_sail_number']) != str(row['pwa_athlete_id']):
            links.append({
                'athlete_id': athlete_id,
                'source': 'PWA_sail_number',
                'source_id': str(row['pwa_sail_number'])
            })

    link_df = pd.DataFrame(links)
    print(f"  [OK] Created {len(link_df)} link records")

    return link_df

def main():
    """Main execution function"""
    print("Merging Final Athlete Data")
    print("=" * 50)

    # Load input files
    matches_file = 'data/processed/athletes/athletes_matched.csv'
    pwa_file = 'data/raw/athletes/pwa_athletes_clean.csv'
    lh_file = 'data/raw/athletes/liveheats_athletes_clean.csv'
    pwa_only_file = 'data/processed/athletes/athletes_pwa_only.csv'
    lh_only_file = 'data/processed/athletes/athletes_liveheats_only.csv'

    # Check required files exist
    for file in [matches_file, pwa_file, lh_file, pwa_only_file, lh_only_file]:
        if not os.path.exists(file):
            print(f"ERROR: Required file not found: {file}")
            print("Please run previous scripts first.")
            return

    matches_df = pd.read_csv(matches_file)
    pwa_df = pd.read_csv(pwa_file)
    lh_df = pd.read_csv(lh_file)
    pwa_only_df = pd.read_csv(pwa_only_file)
    lh_only_df = pd.read_csv(lh_only_file)

    print(f"[OK] Loaded matches: {len(matches_df)}")
    print(f"[OK] Loaded PWA athletes: {len(pwa_df)}")
    print(f"[OK] Loaded LiveHeats athletes: {len(lh_df)}")
    print(f"[OK] Loaded PWA-only: {len(pwa_only_df)}")
    print(f"[OK] Loaded LiveHeats-only: {len(lh_only_df)}")

    # Load manual decisions
    manual_decisions = load_manual_decisions()

    # Filter matches based on score and manual decisions
    # Accept high-confidence matches (>=90%)
    high_confidence = matches_df[matches_df['score'] >= 90].copy()
    print(f"\n[OK] High-confidence matches (>=90%): {len(high_confidence)}")

    # Process manual decisions if any
    if len(manual_decisions) > 0:
        # Add accepted manual matches
        accepted_manual = manual_decisions[manual_decisions['decision'] == 'accept'].copy()
        if len(accepted_manual) > 0:
            print(f"[OK] Accepted manual matches: {len(accepted_manual)}")
            # Remove decision column before concatenating
            accepted_manual = accepted_manual.drop(columns=['decision'])
            all_matches = pd.concat([high_confidence, accepted_manual], ignore_index=True)
        else:
            all_matches = high_confidence
    else:
        all_matches = high_confidence

    print(f"\nTotal accepted matches: {len(all_matches)}")

    # Merge matched athletes with profile data
    matched_athletes = merge_athlete_data(all_matches, pwa_df, lh_df)

    # Create records for unmatched athletes
    pwa_only_records = create_pwa_only_records(pwa_only_df)
    lh_only_records = create_liveheats_only_records(lh_only_df)

    # Combine all athlete records
    all_athletes = pd.concat([
        matched_athletes,
        pwa_only_records,
        lh_only_records
    ], ignore_index=True)

    # Assign unified athlete IDs (auto-increment starting from 1)
    all_athletes['id'] = range(1, len(all_athletes) + 1)

    # Reorder columns to put id first
    cols = ['id'] + [col for col in all_athletes.columns if col != 'id']
    all_athletes = all_athletes[cols]

    # Create link table
    link_table = create_link_table(all_athletes)

    # Save outputs
    output_dir = 'data/processed/athletes'
    os.makedirs(output_dir, exist_ok=True)

    final_file = f'{output_dir}/athletes_final.csv'
    link_file = f'{output_dir}/athlete_ids_link.csv'

    all_athletes.to_csv(final_file, index=False)
    link_table.to_csv(link_file, index=False)

    print(f"\n[OK] Final athletes saved: {final_file} ({len(all_athletes)} records)")
    print(f"[OK] Link table saved: {link_file} ({len(link_table)} records)")

    # Print summary
    print("\n" + "=" * 50)
    print("FINAL ATHLETE DATABASE SUMMARY")
    print("=" * 50)
    print(f"Total athletes: {len(all_athletes)}")
    print(f"  - Matched (both sources): {len(matched_athletes)}")
    print(f"  - PWA-only: {len(pwa_only_records)}")
    print(f"  - LiveHeats-only: {len(lh_only_records)}")
    print(f"\nLink table entries: {len(link_table)}")

    # Show sample
    print("\nSample athlete records:")
    print(all_athletes[['id', 'primary_name', 'nationality', 'year_of_birth', 'match_stage']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
