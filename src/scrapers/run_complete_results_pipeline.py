"""
Complete Wave Results Pipeline
Orchestrates the full process of scraping and merging wave results

Steps:
1. Scrape PWA wave results (if needed/updated)
2. Match PWA events to Live Heats (if needed/updated)
3. Scrape Live Heats matched results
4. Merge PWA + Live Heats results into unified dataset

Usage:
    python run_complete_results_pipeline.py [--skip-pwa] [--skip-matching] [--skip-liveheats]
"""

import os
import sys
import argparse
from datetime import datetime


def log(message, level="INFO"):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def run_pwa_scraper():
    """Run PWA results scraper"""
    log("\n" + "="*80)
    log("STEP 1: SCRAPING PWA WAVE RESULTS")
    log("="*80 + "\n")

    try:
        from pwa_results_scraper import main as pwa_main
        pwa_main()
        log("\n[OK] PWA scraping completed", "SUCCESS")
        return True
    except Exception as e:
        log(f"ERROR in PWA scraping: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def run_event_matching():
    """Run PWA to Live Heats event matching"""
    log("\n" + "="*80)
    log("STEP 2: MATCHING PWA EVENTS TO LIVE HEATS")
    log("="*80 + "\n")

    try:
        from match_pwa_to_liveheats import main as match_main
        match_main()
        log("\n[OK] Event matching completed", "SUCCESS")
        return True
    except Exception as e:
        log(f"ERROR in event matching: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def run_liveheats_scraper():
    """Run Live Heats results scraper"""
    log("\n" + "="*80)
    log("STEP 3: SCRAPING LIVE HEATS RESULTS")
    log("="*80 + "\n")

    try:
        from scrape_liveheats_matched_results import main as lh_main
        lh_main()
        log("\n[OK] Live Heats scraping completed", "SUCCESS")
        return True
    except Exception as e:
        log(f"ERROR in Live Heats scraping: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def run_merge():
    """Run results merger"""
    log("\n" + "="*80)
    log("STEP 4: MERGING PWA + LIVE HEATS RESULTS")
    log("="*80 + "\n")

    try:
        from merge_wave_results import main as merge_main
        merge_main()
        log("\n[OK] Results merge completed", "SUCCESS")
        return True
    except Exception as e:
        log(f"ERROR in merge: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Run complete wave results scraping and merge pipeline'
    )
    parser.add_argument(
        '--skip-pwa',
        action='store_true',
        help='Skip PWA results scraping (use existing data)'
    )
    parser.add_argument(
        '--skip-matching',
        action='store_true',
        help='Skip event matching (use existing matching report)'
    )
    parser.add_argument(
        '--skip-liveheats',
        action='store_true',
        help='Skip Live Heats scraping (use existing data)'
    )

    args = parser.parse_args()

    print("\n")
    print("="*80)
    print("COMPLETE WAVE RESULTS PIPELINE")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    results = {
        'pwa_scraping': None,
        'event_matching': None,
        'liveheats_scraping': None,
        'merge': None
    }

    # Step 1: PWA Scraping
    if args.skip_pwa:
        log("\n[SKIPPED] PWA scraping (using existing data)", "INFO")
        results['pwa_scraping'] = 'skipped'
    else:
        results['pwa_scraping'] = 'success' if run_pwa_scraper() else 'failed'

    # Step 2: Event Matching
    if args.skip_matching:
        log("\n[SKIPPED] Event matching (using existing report)", "INFO")
        results['event_matching'] = 'skipped'
    else:
        results['event_matching'] = 'success' if run_event_matching() else 'failed'

    # Step 3: Live Heats Scraping
    if args.skip_liveheats:
        log("\n[SKIPPED] Live Heats scraping (using existing data)", "INFO")
        results['liveheats_scraping'] = 'skipped'
    else:
        results['liveheats_scraping'] = 'success' if run_liveheats_scraper() else 'failed'

    # Step 4: Merge (always run unless all previous steps failed)
    if all(v == 'failed' for v in results.values() if v is not None):
        log("\n[ABORTED] All previous steps failed, skipping merge", "ERROR")
        results['merge'] = 'aborted'
    else:
        results['merge'] = 'success' if run_merge() else 'failed'

    # Print final summary
    print("\n")
    print("="*80)
    print("PIPELINE EXECUTION SUMMARY")
    print("="*80)
    print(f"PWA Scraping:         {results['pwa_scraping'].upper()}")
    print(f"Event Matching:       {results['event_matching'].upper()}")
    print(f"Live Heats Scraping:  {results['liveheats_scraping'].upper()}")
    print(f"Results Merge:        {results['merge'].upper()}")
    print("="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Exit code
    if results['merge'] == 'success':
        print("\n✓ PIPELINE COMPLETED SUCCESSFULLY")
        sys.exit(0)
    else:
        print("\n✗ PIPELINE COMPLETED WITH ERRORS")
        sys.exit(1)


if __name__ == "__main__":
    main()
