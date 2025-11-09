"""
Match PWA and LiveHeats athletes using fuzzy string matching.

This script uses a 4-stage matching strategy to link athletes across both sources:
1. Exact match + fuzzy >=91%
2. Year of birth +/-1 + fuzzy >=80%
3. Country match + fuzzy >=90%
4. Mark as unmatched

Borderline matches (80-89) are flagged for manual review.
"""

import pandas as pd
import os
from fuzzywuzzy import process
import re

# Manual name corrections (from old script)
NAME_CORRECTIONS = {
    'Coraline Foveau': 'Coco Foveau',
    'Justyna A. Sniady': 'Justyna Snaidy',
    'Michael Friedl (M)': 'Mike Friedl (sr)'
}

def load_country_mapping():
    """
    Load country mapping CSV to normalize country names between PWA and LiveHeats.

    Returns:
        DataFrame with country mapping data
    """
    country_file = 'ATHLETE DATABASE SCRIPTS OLD/Clean Data/country_info_v2.csv'

    if not os.path.exists(country_file):
        print(f"WARNING: Country mapping file not found: {country_file}")
        print("Country-based matching will be limited.")
        return None

    df = pd.read_csv(country_file)
    print(f"[OK] Loaded country mapping: {len(df)} countries")
    return df

def apply_name_corrections(name):
    """Apply manual name corrections"""
    if pd.notna(name) and name in NAME_CORRECTIONS:
        return NAME_CORRECTIONS[name]
    return name

def normalize_pwa_data(pwa_df, country_df):
    """
    Normalize PWA athlete data and join with country mapping.

    Args:
        pwa_df: PWA athletes DataFrame
        country_df: Country mapping DataFrame

    Returns:
        Normalized PWA DataFrame
    """
    print("\nNormalizing PWA data...")

    df = pwa_df.copy()

    # Apply name corrections
    df['name'] = df['name'].apply(apply_name_corrections)

    # Join with country data to get standardized country info
    if country_df is not None:
        # Match PWA nationality (demonym) to country mapping
        df = df.merge(
            country_df[['pwa_demonyms', 'Name', 'ISO Alpha-3', 'live_heats_nationality']],
            left_on='nationality',
            right_on='pwa_demonyms',
            how='left'
        )
        print(f"  Matched {df['Name'].notna().sum()}/{len(df)} athletes to countries")
    else:
        df['Name'] = None
        df['ISO Alpha-3'] = None
        df['live_heats_nationality'] = None

    return df

def normalize_liveheats_data(lh_df):
    """
    Normalize LiveHeats athlete data.

    Args:
        lh_df: LiveHeats athletes DataFrame

    Returns:
        Normalized LiveHeats DataFrame
    """
    print("\nNormalizing LiveHeats data...")

    df = lh_df.copy()

    # Apply name corrections
    df['name'] = df['name'].apply(apply_name_corrections)

    return df

def match_stage1_exact_and_fuzzy(lh_df, pwa_df, threshold=91):
    """
    Stage 1: Exact match + high-confidence fuzzy match (>=91%)

    Args:
        lh_df: LiveHeats DataFrame
        pwa_df: PWA DataFrame
        threshold: Minimum fuzzy match score (default 91)

    Returns:
        Tuple of (matches_df, matched_pwa_indices, matched_lh_indices)
    """
    print(f"\nStage 1: Exact + Fuzzy Match (>={threshold}%)")

    matches = []
    matched_pwa_idx = set()
    matched_lh_idx = set()

    pwa_names = pwa_df['name'].tolist()
    pwa_available = pwa_df.copy()

    for idx, lh_row in lh_df.iterrows():
        lh_name = lh_row['name']

        if pd.isna(lh_name):
            continue

        # Try exact match first
        exact_match = pwa_available[pwa_available['name'] == lh_name]

        if not exact_match.empty:
            pwa_row = exact_match.iloc[0]
            matches.append({
                'lh_athlete_id': lh_row['athlete_id'],
                'lh_name': lh_name,
                'pwa_athlete_id': pwa_row['athlete_id'],
                'pwa_name': pwa_row['name'],
                'score': 100,
                'stage': 'Exact'
            })
            matched_pwa_idx.add(pwa_row.name)
            matched_lh_idx.add(idx)
            pwa_available = pwa_available[pwa_available.index != pwa_row.name]
            continue

        # Try fuzzy match
        if len(pwa_available) > 0:
            available_names = pwa_available['name'].dropna().tolist()
            if len(available_names) > 0:
                best_match, score = process.extractOne(lh_name, available_names)

                if score >= threshold:
                    pwa_row = pwa_available[pwa_available['name'] == best_match].iloc[0]
                    matches.append({
                        'lh_athlete_id': lh_row['athlete_id'],
                        'lh_name': lh_name,
                        'pwa_athlete_id': pwa_row['athlete_id'],
                        'pwa_name': best_match,
                        'score': score,
                        'stage': f'Fuzzy{threshold}'
                    })
                    matched_pwa_idx.add(pwa_row.name)
                    matched_lh_idx.add(idx)
                    pwa_available = pwa_available[pwa_available.index != pwa_row.name]

    print(f"  [OK] Found {len(matches)} matches")
    return pd.DataFrame(matches), matched_pwa_idx, matched_lh_idx

def match_stage2_yob(lh_df, pwa_df, matched_pwa_idx, matched_lh_idx, threshold=80):
    """
    Stage 2: Year of birth +/-1 + fuzzy match (>=80%)

    Args:
        lh_df: LiveHeats DataFrame
        pwa_df: PWA DataFrame
        matched_pwa_idx: Set of already matched PWA indices
        matched_lh_idx: Set of already matched LiveHeats indices
        threshold: Minimum fuzzy match score (default 80)

    Returns:
        Tuple of (matches_df, new_matched_pwa_indices, new_matched_lh_indices)
    """
    print(f"\nStage 2: Year of Birth +/-1 + Fuzzy Match (>={threshold}%)")

    matches = []
    new_matched_pwa = set()
    new_matched_lh = set()

    pwa_available = pwa_df[~pwa_df.index.isin(matched_pwa_idx)].copy()
    lh_available = lh_df[~lh_df.index.isin(matched_lh_idx)].copy()

    for idx, lh_row in lh_available.iterrows():
        lh_name = lh_row['name']
        lh_yob = lh_row.get('year_of_birth')

        if pd.isna(lh_name) or pd.isna(lh_yob):
            continue

        # Filter PWA athletes with YOB +/-1
        pwa_yob_match = pwa_available[
            (pwa_available['year_of_birth'].notna()) &
            (abs(pwa_available['year_of_birth'] - lh_yob) <= 1)
        ]

        if len(pwa_yob_match) > 0:
            yob_names = pwa_yob_match['name'].dropna().tolist()
            if len(yob_names) > 0:
                best_match, score = process.extractOne(lh_name, yob_names)

                if score >= threshold:
                    pwa_row = pwa_yob_match[pwa_yob_match['name'] == best_match].iloc[0]
                    matches.append({
                        'lh_athlete_id': lh_row['athlete_id'],
                        'lh_name': lh_name,
                        'pwa_athlete_id': pwa_row['athlete_id'],
                        'pwa_name': best_match,
                        'score': score,
                        'stage': 'YOB+/-1'
                    })
                    new_matched_pwa.add(pwa_row.name)
                    new_matched_lh.add(idx)

    print(f"  [OK] Found {len(matches)} matches")
    return pd.DataFrame(matches), new_matched_pwa, new_matched_lh

def match_stage3_country(lh_df, pwa_df, matched_pwa_idx, matched_lh_idx, threshold=90):
    """
    Stage 3: Country match + fuzzy name match (>=90%)

    Args:
        lh_df: LiveHeats DataFrame
        pwa_df: PWA DataFrame with normalized country data
        matched_pwa_idx: Set of already matched PWA indices
        matched_lh_idx: Set of already matched LiveHeats indices
        threshold: Minimum fuzzy match score (default 90)

    Returns:
        Tuple of (matches_df, new_matched_pwa_indices, new_matched_lh_indices)
    """
    print(f"\nStage 3: Country + Name Match (>={threshold}%)")

    matches = []
    new_matched_pwa = set()
    new_matched_lh = set()

    pwa_available = pwa_df[~pwa_df.index.isin(matched_pwa_idx)].copy()
    lh_available = lh_df[~lh_df.index.isin(matched_lh_idx)].copy()

    for idx, lh_row in lh_available.iterrows():
        lh_name = lh_row['name']
        lh_nationality = lh_row.get('nationality')

        if pd.isna(lh_name) or pd.isna(lh_nationality):
            continue

        # Filter PWA athletes from same country
        pwa_country_match = pwa_available[
            (pwa_available['live_heats_nationality'] == lh_nationality) |
            (pwa_available['nationality'] == lh_nationality)
        ]

        if len(pwa_country_match) > 0:
            country_names = pwa_country_match['name'].dropna().tolist()
            if len(country_names) > 0:
                best_match, score = process.extractOne(lh_name, country_names)

                if score >= threshold:
                    pwa_row = pwa_country_match[pwa_country_match['name'] == best_match].iloc[0]
                    matches.append({
                        'lh_athlete_id': lh_row['athlete_id'],
                        'lh_name': lh_name,
                        'pwa_athlete_id': pwa_row['athlete_id'],
                        'pwa_name': best_match,
                        'score': score,
                        'stage': 'CountryMatch'
                    })
                    new_matched_pwa.add(pwa_row.name)
                    new_matched_lh.add(idx)

    print(f"  [OK] Found {len(matches)} matches")
    return pd.DataFrame(matches), new_matched_pwa, new_matched_lh

def create_output_files(all_matches_df, pwa_df, lh_df, matched_pwa_idx, matched_lh_idx):
    """
    Create output CSV files for different match categories.

    Args:
        all_matches_df: DataFrame with all matches
        pwa_df: PWA athletes DataFrame
        lh_df: LiveHeats athletes DataFrame
        matched_pwa_idx: Set of matched PWA indices
        matched_lh_idx: Set of matched LiveHeats indices
    """
    print("\nCreating output files...")

    output_dir = 'data/processed/athletes'
    os.makedirs(output_dir, exist_ok=True)

    # 1. All matches
    matches_file = f'{output_dir}/athletes_matched.csv'
    all_matches_df.to_csv(matches_file, index=False)
    print(f"  [OK] All matches: {matches_file} ({len(all_matches_df)} records)")

    # 2. Borderline matches (80-89) for manual review
    needs_review = all_matches_df[
        (all_matches_df['score'] >= 80) &
        (all_matches_df['score'] < 90)
    ].copy()
    review_file = f'{output_dir}/athletes_needs_review.csv'
    needs_review.to_csv(review_file, index=False)
    print(f"  [OK] Needs review (80-89%): {review_file} ({len(needs_review)} records)")

    # 3. PWA-only athletes (unmatched)
    pwa_only = pwa_df[~pwa_df.index.isin(matched_pwa_idx)].copy()
    pwa_only_file = f'{output_dir}/athletes_pwa_only.csv'
    pwa_only.to_csv(pwa_only_file, index=False)
    print(f"  [OK] PWA-only: {pwa_only_file} ({len(pwa_only)} records)")

    # 4. LiveHeats-only athletes (unmatched)
    lh_only = lh_df[~lh_df.index.isin(matched_lh_idx)].copy()
    lh_only_file = f'{output_dir}/athletes_liveheats_only.csv'
    lh_only.to_csv(lh_only_file, index=False)
    print(f"  [OK] LiveHeats-only: {lh_only_file} ({len(lh_only)} records)")

def main():
    """Main execution function"""
    print("PWA <-> LiveHeats Athlete Matching")
    print("=" * 50)

    # Load cleaned athlete data
    pwa_file = 'data/raw/athletes/pwa_athletes_clean.csv'
    lh_file = 'data/raw/athletes/liveheats_athletes_clean.csv'

    if not os.path.exists(pwa_file):
        print(f"ERROR: PWA file not found: {pwa_file}")
        print("Please run scrape_pwa_athlete_profiles.py first.")
        return

    if not os.path.exists(lh_file):
        print(f"ERROR: LiveHeats file not found: {lh_file}")
        print("Please run scrape_liveheats_athlete_profiles.py first.")
        return

    pwa_df = pd.read_csv(pwa_file)
    lh_df = pd.read_csv(lh_file)

    print(f"\n[OK] Loaded PWA athletes: {len(pwa_df)}")
    print(f"[OK] Loaded LiveHeats athletes: {len(lh_df)}")

    # Load country mapping
    country_df = load_country_mapping()

    # Normalize data
    pwa_df = normalize_pwa_data(pwa_df, country_df)
    lh_df = normalize_liveheats_data(lh_df)

    # Run matching stages
    all_matches = []
    matched_pwa_idx = set()
    matched_lh_idx = set()

    # Stage 1: Exact + Fuzzy >=91%
    stage1_matches, new_pwa, new_lh = match_stage1_exact_and_fuzzy(lh_df, pwa_df, threshold=91)
    all_matches.append(stage1_matches)
    matched_pwa_idx.update(new_pwa)
    matched_lh_idx.update(new_lh)

    # Stage 2: YOB +/-1 + Fuzzy >=80%
    stage2_matches, new_pwa, new_lh = match_stage2_yob(lh_df, pwa_df, matched_pwa_idx, matched_lh_idx, threshold=80)
    all_matches.append(stage2_matches)
    matched_pwa_idx.update(new_pwa)
    matched_lh_idx.update(new_lh)

    # Stage 3: Country + Fuzzy >=90%
    stage3_matches, new_pwa, new_lh = match_stage3_country(lh_df, pwa_df, matched_pwa_idx, matched_lh_idx, threshold=90)
    all_matches.append(stage3_matches)
    matched_pwa_idx.update(new_pwa)
    matched_lh_idx.update(new_lh)

    # Combine all matches
    all_matches_df = pd.concat(all_matches, ignore_index=True)

    # Create output files
    create_output_files(all_matches_df, pwa_df, lh_df, matched_pwa_idx, matched_lh_idx)

    # Print summary
    print("\n" + "=" * 50)
    print("MATCHING SUMMARY")
    print("=" * 50)
    print(f"Total matches: {len(all_matches_df)}")
    print(f"  - Exact: {len(all_matches_df[all_matches_df['stage'] == 'Exact'])}")
    print(f"  - Fuzzy91: {len(all_matches_df[all_matches_df['stage'] == 'Fuzzy91'])}")
    print(f"  - YOB+/-1: {len(all_matches_df[all_matches_df['stage'] == 'YOB+/-1'])}")
    print(f"  - CountryMatch: {len(all_matches_df[all_matches_df['stage'] == 'CountryMatch'])}")
    print(f"\nNeeds manual review (80-89%): {len(all_matches_df[(all_matches_df['score'] >= 80) & (all_matches_df['score'] < 90)])}")
    print(f"Unmatched PWA: {len(pwa_df) - len(matched_pwa_idx)}")
    print(f"Unmatched LiveHeats: {len(lh_df) - len(matched_lh_idx)}")

if __name__ == "__main__":
    main()
