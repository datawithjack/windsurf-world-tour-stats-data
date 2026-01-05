"""
PWA Wave Events Scraper
Scrapes event metadata from PWA World Tour website (2016-2025)
Output: CSV with comprehensive event details
"""

import time
import csv
import re
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException


class PWAEventScraper:
    """Scraper for PWA World Tour events"""

    def __init__(self, start_year=2016, headless=True, event_ids=None):
        """
        Initialize the scraper

        Args:
            start_year: Earliest year to scrape (default: 2016)
            headless: Run browser in headless mode (default: True)
            event_ids: Optional list of event IDs to filter (default: None = scrape all)
        """
        self.start_year = start_year
        self.event_ids_filter = set(map(int, event_ids)) if event_ids else None
        self.base_url = "https://www.pwaworldtour.com/index.php?id=2337"

        # Set up Chrome WebDriver
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        if headless:
            chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 90)

        self.events_data = []
        self.scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, message):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def get_year_urls(self):
        """
        Extract all year URLs from the dropdown menu

        Returns:
            List of dicts with 'year' and 'id' keys
        """
        self.log("Navigating to PWA events page...")
        self.driver.get(self.base_url)

        # Wait for dropdown to be present (important for slow connections)
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".nav-sub.select-box .label"))
            )
            self.log("Dropdown element found, waiting for page to stabilize...")
            time.sleep(2)  # Additional wait for page stability
        except Exception as e:
            self.log(f"ERROR: Dropdown element not found after {self.wait._timeout}s: {e}")
            return []

        # Click the dropdown toggle using JavaScript
        dropdown_toggle_js = """
        var dropdown = document.querySelector('.nav-sub.select-box .label');
        if (dropdown) {
            dropdown.click();
            return true;
        } else {
            return false;
        }
        """

        dropdown_toggled = self.driver.execute_script(dropdown_toggle_js)

        if not dropdown_toggled:
            self.log("ERROR: Dropdown not found")
            return []

        self.log("Dropdown clicked successfully")
        time.sleep(3)  # Wait for options to load

        # Wait for dropdown options to be visible
        dropdown_options = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".nav-sub.select-box ul"))
        )

        # Find all year links
        year_elements = dropdown_options.find_elements(By.TAG_NAME, "a")

        year_data = []
        for year_element in year_elements:
            year_text = year_element.text.strip()
            try:
                year_int = int(year_text)
            except ValueError:
                continue  # Skip if conversion fails

            # Only add years >= start_year
            if year_int < self.start_year:
                continue

            href = year_element.get_attribute("href")
            year_id = href.split("id=")[-1]
            year_data.append({"year": year_text, "id": year_id})

        self.log(f"Found {len(year_data)} years to scrape (from {self.start_year})")
        return year_data

    def extract_star_rating(self, event_name):
        """
        Extract star rating from event name

        Args:
            event_name: Event name string

        Returns:
            Number of stars (int) or None if not found
        """
        # Count asterisks in the event name
        asterisks = re.findall(r'\*+', event_name)
        if asterisks:
            return len(asterisks[0])
        return None

    def parse_date(self, date_str, year):
        """
        Parse date string to YYYY-MM-DD format

        Args:
            date_str: Date string like "Sep 27" or "Oct 06"
            year: Year as string

        Returns:
            Date in YYYY-MM-DD format or None if parsing fails
        """
        try:
            # Parse "Sep 27" format
            date_obj = datetime.strptime(f"{date_str} {year}", "%b %d %Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None

    def extract_event_data(self, event_card, year, section_title):
        """
        Extract all data from a single event card

        Args:
            event_card: Selenium WebElement for the event card
            year: Year string
            section_title: "Upcoming events" or "Completed events"

        Returns:
            Dict with event data
        """
        try:
            # Get the event link element
            event_link = event_card.find_element(By.CLASS_NAME, "event-calendar-link")
            event_href = event_link.get_attribute("href")

            # Extract event_id from href
            try:
                event_id = event_href.split('%5BshowUid%5D=')[-1].split('&')[0]
            except IndexError:
                self.log(f"WARNING: Could not extract event_id from href: {event_href}")
                event_id = None

            # If event_ids filter is set, skip events not in the filter
            if self.event_ids_filter and event_id:
                try:
                    if int(event_id) not in self.event_ids_filter:
                        return None  # Skip this event
                except (ValueError, TypeError):
                    pass  # Continue if event_id can't be converted to int

            # Extract event title
            try:
                # Use JavaScript to get text content directly (more reliable than .text for slow loading)
                event_title_js = """
                var titleElement = arguments[0].querySelector('.event-title');
                return titleElement ? titleElement.textContent.trim() : '';
                """
                event_title = self.driver.execute_script(event_title_js, event_card)

                # Debug: Log if title is empty
                if not event_title:
                    self.log(f"  WARNING: event_title is empty for event_id {event_id} (textContent is empty)")
            except Exception as e:
                # Log why event title extraction failed
                self.log(f"  WARNING: Could not extract event_title for event_id {event_id}: {type(e).__name__}")
                event_title = ""

            # Extract event date
            try:
                # Use JavaScript to get text content directly (more reliable than .text for slow loading)
                event_date_js = """
                var dateElement = arguments[0].querySelector('.event-date');
                return dateElement ? dateElement.textContent.trim() : '';
                """
                event_date = self.driver.execute_script(event_date_js, event_card)
            except:
                event_date = ""

            # Parse start and end dates
            start_date = None
            end_date = None
            day_window = None
            if event_date and " - " in event_date:
                date_parts = event_date.split(" - ")
                start_date = self.parse_date(date_parts[0], year)
                end_date = self.parse_date(date_parts[1], year)

                # Calculate day window
                if start_date and end_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        day_window = (end_dt - start_dt).days
                    except:
                        pass

            # Extract discipline icons
            disciplines = []
            has_wave = False
            try:
                discipline_container = event_card.find_element(By.CLASS_NAME, "event-disciplines")
                discipline_icons = discipline_container.find_elements(By.TAG_NAME, "i")
                for icon in discipline_icons:
                    icon_class = icon.get_attribute("class")
                    # Extract number from "icon-discipline-1"
                    match = re.search(r'icon-discipline-(\d+)', icon_class)
                    if match:
                        discipline_num = match.group(1)
                        disciplines.append(discipline_num)
                        if discipline_num == "1":  # Wave discipline
                            has_wave = True
            except:
                pass

            # Extract country flag
            country_flag = ""
            country_code = ""
            try:
                flag_img = event_card.find_element(By.CSS_SELECTOR, ".event-country-flag img")
                country_flag = flag_img.get_attribute("title") or flag_img.get_attribute("alt") or ""

                # Extract country code from filename (e.g., "GER.png" -> "GER")
                flag_src = flag_img.get_attribute("src")
                match = re.search(r'/([A-Z]{2,3})\.png', flag_src)
                if match:
                    country_code = match.group(1)
            except:
                pass

            # Extract event image URL
            event_image_url = ""
            try:
                image = event_card.find_element(By.CSS_SELECTOR, ".event-image img")
                event_image_url = image.get_attribute("src")
            except:
                pass

            # Extract event status and competition state from classes
            event_status = ""
            competition_state = ""
            try:
                card_classes = event_card.get_attribute("class")
                status_match = re.search(r'event-status-(\d+)', card_classes)
                if status_match:
                    event_status = status_match.group(1)

                state_match = re.search(r'event-competition-state-(\d+)', card_classes)
                if state_match:
                    competition_state = state_match.group(1)
            except:
                pass

            # Extract star rating
            stars = self.extract_star_rating(event_title)

            # Build event data dict
            event_data = {
                'source': 'PWA',
                'scraped_at': self.scraped_at,
                'year': year,
                'event_id': event_id,
                'event_name': event_title,
                'event_url': event_href,
                'event_date': event_date,
                'start_date': start_date,
                'end_date': end_date,
                'day_window': day_window,
                'event_section': section_title,
                'event_status': event_status,
                'competition_state': competition_state,
                'has_wave_discipline': has_wave,
                'all_disciplines': ','.join(disciplines) if disciplines else '',
                'country_flag': country_flag,
                'country_code': country_code,
                'stars': stars,
                'event_image_url': event_image_url
            }

            return event_data

        except Exception as e:
            self.log(f"ERROR extracting event data: {e}")
            return None

    def scrape_year(self, year, year_id):
        """
        Scrape all events for a given year

        Args:
            year: Year string
            year_id: URL ID for the year
        """
        year_url = f"https://www.pwaworldtour.com/index.php?id={year_id}"
        self.log(f"Scraping year {year}...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver.get(year_url)

                # Wait for event sections to be visible
                sections = self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".event-calendar-grid"))
                )

                events_found = 0

                # Process each section (Upcoming/Completed)
                for section in sections:
                    try:
                        # Get section title
                        section_title = section.find_element(By.TAG_NAME, "h3").text.strip()

                        # Find all event cards in this section
                        event_cards = section.find_elements(By.CLASS_NAME, "event-calendar-item")

                        self.log(f"  {section_title}: Found {len(event_cards)} events")

                        for event_card in event_cards:
                            event_data = self.extract_event_data(event_card, year, section_title)
                            if event_data:
                                self.events_data.append(event_data)
                                events_found += 1

                    except Exception as e:
                        self.log(f"  ERROR processing section: {e}")
                        continue

                self.log(f"  Total events extracted for {year}: {events_found}")
                break  # Success, exit retry loop

            except TimeoutException:
                if attempt < max_retries - 1:
                    self.log(f"  Timeout on attempt {attempt + 1}, retrying...")
                    time.sleep(5)
                else:
                    self.log(f"  ERROR: Failed to load year {year} after {max_retries} attempts")

            except Exception as e:
                self.log(f"  ERROR scraping year {year}: {e}")
                break

    def scrape_all_years(self):
        """Scrape events from all years"""
        year_urls = self.get_year_urls()

        if not year_urls:
            self.log("ERROR: No years found to scrape")
            return

        total_years = len(year_urls)

        for idx, year_info in enumerate(year_urls, 1):
            self.log(f"\n--- Processing year {idx}/{total_years} ---")
            self.scrape_year(year_info['year'], year_info['id'])
            time.sleep(2)  # Be nice to the server

        self.log(f"\n=== Scraping Complete ===")
        self.log(f"Total events scraped: {len(self.events_data)}")

    def save_to_csv(self, output_path):
        """
        Save scraped data to CSV

        Args:
            output_path: Path to output CSV file
        """
        if not self.events_data:
            self.log("WARNING: No data to save")
            return

        df = pd.DataFrame(self.events_data)

        # Ensure columns are in the desired order
        column_order = [
            'source', 'scraped_at', 'year', 'event_id', 'event_name', 'event_url',
            'event_date', 'start_date', 'end_date', 'day_window', 'event_section',
            'event_status', 'competition_state', 'has_wave_discipline',
            'all_disciplines', 'country_flag', 'country_code', 'stars', 'event_image_url'
        ]

        df = df[column_order]

        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        self.log(f"Data saved to: {output_path}")

        # Print summary statistics
        self.log("\n=== Summary Statistics ===")
        self.log(f"Total events: {len(df)}")
        self.log(f"Wave events: {df['has_wave_discipline'].sum()}")
        self.log(f"Years covered: {df['year'].nunique()}")
        self.log(f"Unique event IDs: {df['event_id'].nunique()}")

    def close(self):
        """Close the browser"""
        self.driver.quit()
        self.log("Browser closed")


def main():
    """Main execution function"""
    # Initialize scraper
    scraper = PWAEventScraper(start_year=2016, headless=True)

    try:
        # Scrape all events
        scraper.scrape_all_years()

        # Save to CSV
        output_path = "data/raw/pwa/pwa_events_raw.csv"
        scraper.save_to_csv(output_path)

    except Exception as e:
        scraper.log(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Always close the browser
        scraper.close()


if __name__ == "__main__":
    main()
