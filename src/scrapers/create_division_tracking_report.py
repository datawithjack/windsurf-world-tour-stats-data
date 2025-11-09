"""
Create Division Results Tracking Report
Generates comprehensive CSV showing status of all PWA wave division codes
"""

import pandas as pd
from datetime import datetime


def parse_division_codes_and_labels(row):
    """
    Parse comma-separated division codes and labels from CSV row

    Args:
        row: DataFrame row with 'division_codes' and 'division_labels' columns

    Returns:
        List of dicts with code and label pairs
    """
    divisions = []

    # Skip if no division codes
    if pd.isna(row['division_codes']) or str(row['division_codes']).strip() == '':
        return divisions

    # Parse codes and labels
    codes = [c.strip() for c in str(row['division_codes']).split(',')]
    labels = [l.strip() for l in str(row['division_labels']).split(',')]

    # Match them up (they should be same length)
    for i in range(len(codes)):
        label = labels[i] if i < len(labels) else 'Unknown'

        # Determine sex from label
        sex = 'Women' if 'women' in label.lower() else 'Men'

        divisions.append({
            'division_code': codes[i],
            'division_label': label,
            'sex': sex
        })

    return divisions


def create_tracking_report():
    """Create comprehensive division tracking report"""

    print("="*80)
    print("PWA WAVE DIVISION RESULTS TRACKING REPORT")
    print("="*80)
    print()

    # Load divisions data
    print("Loading division data...")
    div_df = pd.read_csv('data/raw/pwa/pwa_wave_divisions_raw.csv')

    # Load results data
    print("Loading results data...")
    res_df = pd.read_csv('data/raw/pwa/pwa_wave_results_raw.csv')

    # Load original events data for additional context
    print("Loading events data...")
    events_df = pd.read_csv('data/raw/pwa/pwa_events_raw.csv')

    # Get division codes that have actual results
    # Convert division_code to string for matching
    res_df['division_code'] = res_df['division_code'].astype(str)
    result_counts = res_df.groupby('division_code').size().to_dict()
    divisions_with_results = set(res_df['division_code'].unique())

    print(f"\nFound {len(divisions_with_results)} division codes with extracted results")

    # Parse all division codes from divisions CSV
    all_divisions = []

    for idx, row in div_df.iterrows():
        # Get event details
        event_id = row['event_id']
        year = row['year']
        event_name = row['event_name']
        has_div_results = row['has_results']

        # Get event status from original events
        event_row = events_df[events_df['event_id'] == event_id]
        event_status = event_row['event_section'].values[0] if not event_row.empty else ''
        stars = event_row['stars'].values[0] if not event_row.empty else None

        # Parse divisions for this event
        divisions = parse_division_codes_and_labels(row)

        for div in divisions:
            division_code = div['division_code']

            # Check if this division has results
            has_results = division_code in divisions_with_results
            result_count = result_counts.get(division_code, 0)

            # Determine notes/reason if no results
            notes = ''
            if not has_results:
                if 'youth' in event_name.lower() or 'junior' in event_name.lower():
                    notes = 'Youth event'
                elif 'upcoming' in event_status.lower():
                    notes = 'Future event'
                elif year in [2020, 2021]:
                    notes = 'COVID era'
                elif pd.isna(stars):
                    notes = 'Older event (pre-star rating)'
                else:
                    notes = 'No results published'

            all_divisions.append({
                'division_code': division_code,
                'event_id': event_id,
                'year': year,
                'event_name': event_name,
                'division_label': div['division_label'],
                'sex': div['sex'],
                'stars': stars,
                'event_status': event_status,
                'has_results': has_results,
                'result_count': result_count,
                'notes': notes,
                'checked_at': datetime.now().strftime("%Y-%m-%d")
            })

    # Create DataFrame
    tracking_df = pd.DataFrame(all_divisions)

    # Sort by year (descending), then event_id, then sex
    tracking_df = tracking_df.sort_values(
        by=['year', 'event_id', 'sex'],
        ascending=[False, True, False]
    )

    # Save to CSV
    output_path = 'data/raw/pwa/pwa_division_results_tracking.csv'
    tracking_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"\n{'='*80}")
    print("TRACKING REPORT CREATED")
    print(f"{'='*80}")
    print(f"Output: {output_path}")
    print()

    # Print summary statistics
    print(f"{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Total division codes: {len(tracking_df)}")
    print(f"Divisions with results: {tracking_df['has_results'].sum()}")
    print(f"Divisions without results: {(~tracking_df['has_results']).sum()}")
    print()

    print("--- By Year ---")
    year_stats = tracking_df.groupby('year').agg({
        'has_results': ['count', 'sum']
    })
    year_stats.columns = ['Total', 'With Results']
    year_stats['Without Results'] = year_stats['Total'] - year_stats['With Results']
    print(year_stats.sort_index(ascending=False))
    print()

    print("--- By Sex ---")
    sex_stats = tracking_df.groupby('sex').agg({
        'has_results': ['count', 'sum']
    })
    sex_stats.columns = ['Total', 'With Results']
    sex_stats['Without Results'] = sex_stats['Total'] - sex_stats['With Results']
    print(sex_stats)
    print()

    print("--- Result Count Distribution ---")
    results_with_data = tracking_df[tracking_df['has_results']]
    if not results_with_data.empty:
        print(f"Average athletes per division: {results_with_data['result_count'].mean():.1f}")
        print(f"Min athletes: {results_with_data['result_count'].min()}")
        print(f"Max athletes: {results_with_data['result_count'].max()}")
        print(f"Median athletes: {results_with_data['result_count'].median():.1f}")
    print()

    print("--- Missing Results by Reason ---")
    missing = tracking_df[~tracking_df['has_results']]
    if not missing.empty:
        print(missing['notes'].value_counts())
    print()

    print(f"{'='*80}\n")

    return tracking_df


if __name__ == "__main__":
    create_tracking_report()
