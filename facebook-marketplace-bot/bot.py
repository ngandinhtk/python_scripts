import os
import time
import json
import gspread
import requests
import subprocess
import traceback
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

class FacebookMarketplaceBot:
    """
    A bot to automate posting rental listings on Facebook Marketplace.
    """

    def __init__(self):
        self.email = os.getenv("FACEBOOK_EMAIL")
        self.password = os.getenv("FACEBOOK_PASSWORD")
        self.google_sheets_url = os.getenv("GOOGLE_SHEETS_URL")
        self.google_creds_file = os.path.join(os.path.dirname(__file__), os.getenv("GOOGLE_CREDS_FILE", "credentials.json"))
        self.profile_dir = os.getenv("CHROME_USER_DATA_DIR", os.path.join(os.getcwd(), "chrome_profile"))
        self.cookie_file = os.getenv("FB_COOKIE_FILE", "fb_cookies.json")

        self._validate_env_vars()
        
        self.driver = None
        self._initialize_driver()
        self.wait = WebDriverWait(self.driver, 20)
    
    def _initialize_driver(self):
        """Initialize the Chrome WebDriver with proper error handling."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Initializing Chrome WebDriver (attempt {attempt + 1}/{max_retries})...")
                
                options = webdriver.ChromeOptions()
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("start-maximized")
                options.add_argument("disable-infobars")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                
                # Use separate temp profile to avoid conflicts with existing profile
                os.makedirs(self.profile_dir, exist_ok=True)
                options.add_argument(f"--user-data-dir={self.profile_dir}")

                self.driver = webdriver.Chrome(
                    service=ChromeService(ChromeDriverManager().install()), 
                    options=options
                )
                print("✓ Chrome WebDriver initialized successfully.")
                return
                
            except Exception as e:
                print(f"✗ Attempt {attempt + 1} failed: {str(e)[:200]}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    raise Exception(f"Failed to initialize Chrome after {max_retries} attempts: {e}")

    def _validate_env_vars(self):
        if not self.email or not self.password:
            raise ValueError("Error: FACEBOOK_EMAIL and FACEBOOK_PASSWORD must be set in the .env file.")
        if not self.google_sheets_url:
            raise ValueError("Error: GOOGLE_SHEETS_URL must be set in the .env file.")
        if not os.path.exists(self.google_creds_file):
            raise FileNotFoundError(f"Error: Google credentials file '{self.google_creds_file}' not found.")

    def get_listings_from_google_sheets(self):
        """Fetches rental listing data from the Google Sheet."""
        print("Fetching listings from Google Sheets...")
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = Credentials.from_service_account_file(self.google_creds_file, scopes=scope)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_url(self.google_sheets_url)
            
            # Get the first worksheet
            sheet = spreadsheet.worksheets()[0]
            print(f"Using worksheet: '{sheet.title}'")
            
            records = sheet.get_all_records()
            print(f"Found {len(records)} total records in sheet.")
            
            if not records:
                print("No records found in Google Sheet.")
                return []
            
            # Filter ONLY for 'in progress' status
            if 'Status' not in records[0]:
                print("⚠️  WARNING: 'Status' column not found in sheet!")
                print("Please add a 'Status' column with 'in progress' values.")
                return []
            
            filtered_records = [record for record in records if record.get('Status', '').lower().strip() == 'inprogress']
            print(f"Found {len(records)} total listings. Filtering: {len(filtered_records)} listings with 'inprogress' status.")
            
            if not filtered_records:
                print("⚠️  No listings with 'in progress' status found.")
            
            return filtered_records
        except Exception as e:
            print(f"Error fetching data from Google Sheets: {e}")
            traceback.print_exc()
            return []

    def login_to_facebook(self):
        """Logs in to Facebook if not already logged in."""
        self.driver.get("https://www.facebook.com")
        if self._is_logged_in():
            print("Already logged in.")
            return

        print("Logging in to Facebook...")
        try:
            email_input = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            password_input = self.driver.find_element(By.ID, "pass")
            email_input.send_keys(self.email)
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            self.wait.until(EC.url_contains("facebook.com"))
            print("Login successful.")
        except TimeoutException:
            print("Login fields not found. Assuming already logged in.")

    def _is_logged_in(self):
        """Checks if the user is logged in."""
        try:
            self.driver.find_element(By.XPATH, "//a[@aria-label='Home']")
            return True
        except NoSuchElementException:
            return False

    def post_rental_listing(self, listing):
        """Posts a single rental listing to Facebook Marketplace."""
        self.driver.get("https://www.facebook.com/marketplace/create/rental")
        time.sleep(5) # Wait for page to load

        try:
            print(f"Listing data before filling form: {listing}")
            self._upload_image(listing.get("ImagePath"))
            self._fill_form(listing)
            self._submit_listing()
            print(f"Successfully posted: {listing.get('Rental description')}")
            return True
        except Exception as e:
            print(f"Error posting listing '{listing.get('Rental description')}': {e}")
            self.driver.save_screenshot(f"error_{listing.get('Rental description', 'untitled')}.png")
            return False

    def _fill_form(self, listing):
        """Fills out the rental listing form."""
        # Validate that we have required fields
        if not listing.get("Rental description"):
            raise ValueError("Listing missing required field: Rental description")
        
        # Support both "Location" and "Column 7" column names
        location = listing.get("Location") or listing.get("Column 7")
        
        self._select_dropdown("Rental type", listing.get("Rental type"))
        self._safe_fill_input("Date available", listing.get("Date available"))
        self._safe_fill_input("Number of bedrooms", listing.get("Number of bedrooms"))
        self._safe_fill_input("Number of bathrooms", listing.get("Number of bathrooms"))
        self._safe_fill_input("Price per month", listing.get("Price per month"))
        self._safe_fill_input("Rental description", listing.get("Rental description"))
        self._fill_location(listing.get("Location"))


    def _safe_fill_input(self, label, value):
        """Safely finds and fills a text input."""
        if not value:
            return
        try:
            xpath = f"//label[contains(., '{label}')]//input | //span[contains(text(), '{label}')]/..//..//input"
            if label == "Rental description":
                xpath = f"//label[contains(., '{label}')]//textarea"
           
            element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            element.click()
            element.clear()
            element.send_keys(value)
            print(f"Filled '{label}': {value}")
            time.sleep(1)
        except TimeoutException:
            print(f"Could not find input for '{label}'")

    def _fill_location(self, location_value):
        """Fills location field and selects from dropdown suggestions."""
        if not location_value:
            return

        try:
            location_input = None
            
            # Method 1: Find by CSS selector for combobox inputs
            try:
                location_input = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[role='textbox'][aria-label*='Location' i]"))
                )
                print("✓ Found location input via role='textbox'")
            except TimeoutException:
                pass
            
            # Method 2: Find by placeholder containing "address" or "location"  
            if not location_input:
                try:
                    location_input = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'address') or contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'location')]"))
                    )
                    print("✓ Found location input via placeholder")
                except TimeoutException:
                    pass
            
            # Method 3: Find by aria-label
            if not location_input:
                try:
                    location_input = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'location') or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'address')]"))
                    )
                    print("✓ Found location input via aria-label")
                except TimeoutException:
                    pass
            
            # Method 4: Find by proximity to map icon
            if not location_input:
                try:
                    location_input = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//svg[contains(@viewBox, '10')]/ancestor::div[@role='presentation' or @role='menuitem']/following-sibling::div//input"))
                    )
                    print("✓ Found location input via icon proximity")
                except TimeoutException:
                    pass
            
            # Method 5: Generic search - all text inputs and find the one that works
            if not location_input:
                try:
                    all_inputs = self.driver.find_elements(By.XPATH, "//input[@type='text' or (not(@type) and parent::div)]")
                    # Take inputs after the description field
                    if len(all_inputs) >= 6:
                        location_input = all_inputs[5]  # Usually location is the 6th input
                        print("✓ Found location input via position (6th input)")
                except (TimeoutException, IndexError):
                    pass
            
            if not location_input:
                print("⚠️  WARNING: Could not find location input - will skip location")
                return
            
            print(f"DEBUG: Location input found - Placeholder: {location_input.get_attribute('placeholder')}")
            
            # Click on the input to activate it
            self.driver.execute_script("arguments[0].click();", location_input)
            time.sleep(0.5)
            
            # Clear existing content
            location_input.clear()
            time.sleep(0.3)
            
            # Type the location
            location_input.send_keys(location_value)
            print(f"Typed location: {location_value}")
            time.sleep(2)
            
            # Wait for dropdown and select first option
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[@role='option']")))
                first_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//*[@role='option'])[1]")))
                first_option.click()
                print("✓ Selected first location suggestion")
                time.sleep(1)
            except TimeoutException:
                print("⚠️  No suggestions found - proceeding with typed location")
                
        except Exception as e:
            print(f"⚠️  Location fill error (non-blocking): {str(e)[:100]}")




    def _select_dropdown(self, label, value):
        """Selects an option from a dropdown."""
        if not value:
            return
        try:
            xpath = f"//label[@role='combobox' and .//span[contains(text(), '{label}')]]"
            combobox = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            combobox.click()
            time.sleep(1)
            option_xpath = f"//*[@role='option' and (normalize-space(.)='{value}' or .//span[normalize-space(.)='{value}'])]"
            option = self.wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            option.click()
            print(f"Selected '{label}': {value}")
            time.sleep(1)
        except TimeoutException:
            print(f"Could not select dropdown for '{label}'")

    def _upload_image(self, image_path):
        """Uploads an image to Facebook. Handles both local paths and URLs."""
        if not image_path:
            return

        try:
            # Check if it's a local file path
            if os.path.exists(image_path):
                # Local file exists, use it directly
                absolute_path = os.path.abspath(image_path)
                upload_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                upload_input.send_keys(absolute_path)
                print(f"Uploaded image from local path: {image_path}")
                time.sleep(5)  # Wait for image to upload
            elif image_path.startswith('http'):
                # It's a URL, download and upload
                response = requests.get(image_path, stream=True, timeout=10)
                if response.status_code == 200:
                    image_filename = "temp_image.jpg"
                    with open(image_filename, 'wb') as f:
                        f.write(response.content)

                    absolute_path = os.path.abspath(image_filename)
                    upload_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                    upload_input.send_keys(absolute_path)
                    print(f"Uploaded image from URL: {image_path}")
                    time.sleep(5)  # Wait for image to upload
                    os.remove(image_filename)
                else:
                    print(f"Failed to download image from {image_path}. Status code: {response.status_code}")
            else:
                print(f"⚠️  Image path not found and is not a valid URL: {image_path}")
        except Exception as e:
            print(f"Error uploading image: {e}")

    def _submit_listing(self):
        """Clicks the 'Next' and 'Publish' buttons to submit the listing."""
        try:
            next_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Next')]")))
            next_button.click()
            print("Clicked 'Next'")
            time.sleep(2)

            publish_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Publish')]")))
            publish_button.click()
            print("Clicked 'Publish'")
            time.sleep(5) # Wait for listing to be published
        except TimeoutException:
            raise Exception("Could not find 'Next' or 'Publish' button.")

    def run(self):
        """Main method to run the bot."""
        try:
            listings = self.get_listings_from_google_sheets()
            
            if not listings:
                print("✗ No listings to process.")
                return
            
            # Validate data structure before logging in to Facebook
            print(f"\n{'='*60}")
            print(f"Validating data structure...")
            print(f"{'='*60}")
            invalid_listings = []
            for idx, listing in enumerate(listings, 1):
                if not listing.get("Rental description"):
                    invalid_listings.append(idx)
                    print(f"⚠️  Listing {idx}: Missing required field 'Rental description' - cannot post")
            
            if len(invalid_listings) == len(listings):
                print(f"\n✗ ERROR: All {len(listings)} listings are missing required fields!")
                print("Please ensure your Google Sheet has this column:")
                print("  - Rental description: Full property description")
                return
            
            valid_listings = [l for i, l in enumerate(listings, 1) if i not in invalid_listings]
            print(f"\n✓ Data validation complete: {len(valid_listings)} valid listings, {len(invalid_listings)} invalid")
            
            if not valid_listings:
                print("No valid listings to post.")
                return
            
            # Now login and post
            self.login_to_facebook()
            
            print(f"\n{'='*60}")
            print(f"Starting to post {len(valid_listings)} listings...")
            print(f"{'='*60}")
            posted_count = 0
            
            for idx, listing in enumerate(valid_listings, 1):
                try:
                    print(f"\n{'='*60}")
                    print(f"Processing listing {idx}/{len(valid_listings)}: {listing.get('Title', 'Untitled')}")
                    print(f"{'='*60}")
                    success = self.post_rental_listing(listing)
                    if success:
                        posted_count += 1
                    print("-" * 60)
                    time.sleep(10)  # Wait between posts to avoid being flagged
                except Exception as e:
                    print(f"✗ Error processing listing {idx}: {str(e)[:100]}")
                    traceback.print_exc()
                    continue
            
            print(f"\n{'='*60}")
            print(f"Posting complete! Posted {posted_count}/{len(valid_listings)} listings successfully.")
            print(f"{'='*60}")
        
        except Exception as e:
            print(f"Fatal error in bot.run(): {e}")
            traceback.print_exc()
        
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                    print("Browser closed successfully.")
            except Exception as e:
                print(f"Error closing browser: {e}")


if __name__ == "__main__":
    try:
        bot = FacebookMarketplaceBot()
        bot.run()
    except (ValueError, FileNotFoundError) as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()