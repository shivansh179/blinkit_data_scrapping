import requests
import csv
import datetime
import logging
import time
import pandas as pd
from urllib.parse import urljoin

# --- Configuration ---
# Input files
LOCATIONS_FILE = 'blinkit_locations.csv'
CATEGORIES_FILE = 'blinkit_categories.csv'
SCHEMA_FILE = 'Scraping Task _ Schema - Schema.csv'

# Output file
OUTPUT_FILE = 'blinkit_scraped_data.csv'
LOG_FILE = 'scraper.log'

# API Configuration
BASE_URL = 'https://blinkit.com/'
API_ENDPOINT = 'v1/layout/listing_widgets'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Origin': 'https://blinkit.com',
    'Referer': 'https://blinkit.com/',
    'app_client': 'consumer_web',
    'app_version': '1010101010', # A placeholder version
    'platform': 'desktop_web'
}
REQUEST_DELAY_SECONDS = 1 # Delay between requests to be polite to the server

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def read_schema_columns(filename):
    """Reads the required column headers from the schema CSV file."""
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            # Skip the first line which is a title
            next(f) 
            reader = csv.reader(f)
            # The first column of each subsequent row is the field name
            return [row[0] for row in reader if row]
    except FileNotFoundError:
        logging.error(f"Schema file not found: {filename}")
        return []

def parse_product_snippet(snippet, category_info, scrape_date):
    """Extracts and maps product data from a single JSON snippet to the required schema."""
    data = snippet.get('data', {})
    if not data or snippet.get('widget_type') != 'product_card_snippet_type_2':
        return None

    # Use .get() with default values to prevent errors on missing keys
    product_id = data.get('product_id')
    merchant_id = data.get('meta', {}).get('merchant_id')
    
    # Extract data, mapping to the schema fields
    product_data = {
        'date': scrape_date,
        'l1_category': category_info['l1_category'],
        'l1_category_id': category_info['l1_category_id'],
        'l2_category': category_info['l2_category'],
        'l2_category_id': category_info['l2_category_id'],
        'store_id': merchant_id,
        'variant_id': product_id,
        'variant_name': data.get('name', {}).get('text'),
        'group_id': data.get('group_id'),
        'selling_price': data.get('atc_action', {}).get('add_to_cart', {}).get('cart_item', {}).get('price'),
        'mrp': data.get('atc_action', {}).get('add_to_cart', {}).get('cart_item', {}).get('mrp'),
        'in_stock': not data.get('is_sold_out', True),
        'inventory': data.get('inventory'),
        'is_sponsored': data.get('is_sponsored', False), # Defaulting to False as not observed in API
        'image_url': data.get('image', {}).get('url'),
        'brand_id': None, # Not found in the API response
        'brand': data.get('brand_name', {}).get('text')
    }

    # Only return data if we have the essential identifiers
    if product_data['variant_id'] and product_data['variant_name']:
        return product_data
    return None

def scrape_category_for_location(session, location, category, csv_writer):
    """Scrapes all pages for a given category/location combination and writes to CSV."""
    lat = location['latitude']
    lon = location['longitude']
    l1_id = category['l1_category_id']
    l2_id = category['l2_category_id']
    
    # Set location headers for this session of requests
    session.headers.update({'lat': str(lat), 'lon': str(lon)})

    # Initial API URL construction
    params = {
        'offset': 0,
        'limit': 24, # A reasonable limit
        'l0_cat': l1_id,
        'l1_cat': l2_id,
        'page_index': 1
    }
    next_url = urljoin(BASE_URL, f"{API_ENDPOINT}?{'&'.join([f'{k}={v}' for k, v in params.items()])}")
    
    page_count = 1
    products_scraped_count = 0

    while next_url:
        logging.info(f"Scraping Page {page_count} for '{category['l2_category']}' at Lat: {lat}, Lon: {lon}")
        
        try:
            response = session.post(next_url, json={"applied_filters": None, "is_subsequent_page": page_count > 1})
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()

            snippets = data.get('response', {}).get('snippets', [])
            if not snippets:
                logging.info("No more product snippets found. Moving to next category.")
                break

            scrape_date = datetime.date.today().isoformat()
            
            for snippet in snippets:
                product = parse_product_snippet(snippet, category, scrape_date)
                if product:
                    csv_writer.writerow(product)
                    products_scraped_count += 1
            
            # Check for next page
            pagination = data.get('response', {}).get('pagination', {})
            next_page_path = pagination.get('next_url')
            
            if next_page_path:
                next_url = urljoin(BASE_URL, next_page_path)
                page_count += 1
                time.sleep(REQUEST_DELAY_SECONDS) # Be polite
            else:
                next_url = None # End of pagination

        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for URL {next_url}: {e}")
            break # Stop trying for this category/location on error
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

    logging.info(f"Finished scraping '{category['l2_category']}'. Found {products_scraped_count} products.")


def main():
    """Main function to orchestrate the scraping process."""
    logging.info("--- Starting Blinkit Scraper ---")
    
    try:
        # Load input data
        locations = pd.read_csv(LOCATIONS_FILE).to_dict('records')
        categories = pd.read_csv(CATEGORIES_FILE).to_dict('records')
        schema_columns = read_schema_columns(SCHEMA_FILE)
        
        if not schema_columns:
            logging.error("Could not read schema columns. Exiting.")
            return

        logging.info(f"Loaded {len(locations)} locations and {len(categories)} categories.")
        
    except FileNotFoundError as e:
        logging.error(f"Input file not found: {e}. Please ensure all CSV files are present.")
        return

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=schema_columns)
        writer.writeheader()

        with requests.Session() as session:
            session.headers.update(HEADERS)
            
            for location in locations:
                for category in categories:
                    scrape_category_for_location(session, location, category, writer)
                    logging.info("-" * 20)

    logging.info(f"--- Scraping Complete. Data saved to {OUTPUT_FILE} ---")

if __name__ == "__main__":
    main()