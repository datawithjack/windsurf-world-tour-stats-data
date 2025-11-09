"""
Test PWA Wave Event Results Scraper
Tests on first 3 wave events to verify functionality
"""

import sys
from pwa_results_scraper import PWAResultsScraper


def main():
    """Test on first 3 wave events"""
    # Input: PWA events CSV
    events_csv = "data/raw/pwa/pwa_events_raw.csv"

    # Outputs
    results_csv = "data/raw/pwa/pwa_wave_results_test.csv"
    divisions_csv = "data/raw/pwa/pwa_wave_divisions_test.csv"

    # Initialize scraper
    scraper = PWAResultsScraper(events_csv)

    try:
        # Load wave events
        wave_events = scraper.load_wave_events()

        if wave_events.empty:
            scraper.log("No wave events found!", "ERROR")
            return

        # Test on first 3 events
        test_events = wave_events.head(3)
        scraper.log(f"\n{'='*80}")
        scraper.log(f"TESTING MODE: Processing first 3 wave events only")
        scraper.log(f"{'='*80}\n")

        for idx, (_, event_row) in enumerate(test_events.iterrows(), 1):
            scraper.log(f"\n--- Test Event {idx}/3 ---")
            scraper.scrape_event_results(event_row)

        scraper.print_summary()

        # Save results
        scraper.save_results(results_csv, divisions_csv)

        scraper.log("\n" + "="*80)
        scraper.log("TEST COMPLETE - Review output files before running full scrape")
        scraper.log("="*80)

    except Exception as e:
        scraper.log(f"FATAL ERROR: {e}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
