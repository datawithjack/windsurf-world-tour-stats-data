"""
Use existing PWA athlete data from old scraping project.

Since PWA scraping is slow and we already have clean PWA data from the previous
athlete database project, we'll use that data and merge it with our database IDs.
"""

import pandas as pd
import os

def main():
    print("Merging Old PWA Data with Current Database IDs")
    print("=" * 50)

    # Load old PWA data
    old_pwa_file = 'ATHLETE DATABASE SCRIPTS OLD/Clean Data/pwa_sailors_clean.csv'
    old_pwa = pd.read_csv(old_pwa_file)
    print(f"\nLoaded {len(old_pwa)} athletes from old PWA data")
    print(f"Columns: {old_pwa.columns.tolist()}")

    # Load current database IDs
    db_pwa_file = 'data/raw/athletes/pwa_athletes_to_scrape.csv'
    db_pwa = pd.read_csv(db_pwa_file)
    print(f"\nLoaded {len(db_pwa)} athletes from current database")

    # The old PWA data has pwa_sail_no, we need to match with athlete_id from database
    # Database athlete_id for PWA is the numeric ID, old data has pwa_sail_no
    # Let's try matching on sail number first

    # Merge on sail number
    merged = db_pwa.merge(
        old_pwa,
        left_on='sail_number',
        right_on='pwa_sail_no',
        how='left',
        suffixes=('_db', '_old')
    )

    print(f"\nMatched {merged['pwa_name'].notna().sum()}/{len(db_pwa)} athletes on sail number")

    # For unmatched athletes, we'll use the athlete_name from database
    unmatched_count = merged['pwa_name'].isna().sum()
    print(f"Using database names for {unmatched_count} unmatched athletes")

    # Create final dataset with consistent columns
    final = pd.DataFrame({
        'athlete_id': merged['athlete_id'],
        'name': merged['pwa_name'].fillna(merged['athlete_name']),
        'age': merged['pwa_age'],
        'year_of_birth': merged['pwa_yob'],
        'nationality': merged['pwa_nationality'],
        'sail_number': merged['pwa_sail_no'].fillna(merged['sail_number']),
        'sponsors': merged['pwa_current_sponsors'],
        'profile_url': merged['pwa_url'],
        'first_seen_year': merged['first_seen_year'],
        'last_seen_year': merged['last_seen_year'],
        'event_count': merged['event_count']
    })

    # Remove athletes with no name (not found in old data)
    before = len(final)
    final = final[final['name'].notna()]
    print(f"\nFinal dataset: {len(final)} athletes (removed {before-len(final)} without matches)")

    # Save outputs
    output_dir = 'data/raw/athletes'
    os.makedirs(output_dir, exist_ok=True)

    raw_output = f'{output_dir}/pwa_athletes_raw.csv'
    clean_output = f'{output_dir}/pwa_athletes_clean.csv'

    final.to_csv(raw_output, index=False)
    final.to_csv(clean_output, index=False)

    print(f"\n[OK] Saved to: {raw_output}")
    print(f"[OK] Saved to: {clean_output}")

    print("\n" + "=" * 50)
    print("PHASE 2A & 2B COMPLETE!")
    print("=" * 50)
    print(f"PWA athletes: {len(final)}")

    lh = pd.read_csv('data/raw/athletes/liveheats_athletes_clean.csv')
    print(f"LiveHeats athletes: {len(lh)}")
    print(f"Total: {len(final) + len(lh)} athletes ready for matching")

    # Show sample
    print("\nSample PWA athletes:")
    print(final[['athlete_id', 'name', 'sail_number', 'nationality', 'year_of_birth']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
