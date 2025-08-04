# Blinkit Product Scraper

This project contains a Python script to scrape product data from Blinkit's public API for a given set of locations and product categories.

## Task Overview

The goal is to extract product information based on the schema provided in `Scraping Task _ Schema - Schema.csv` by iterating through various geographical coordinates and product subcategories.

## Features

- **Dynamic Scraping**: Reads locations and categories from CSV files.
- **Full Pagination**: Automatically handles multiple pages of products for each category.
- **Robust Parsing**: Safely extracts data from the JSON API response, handling missing fields gracefully.
- **Polite Scraping**: Includes a delay between requests to avoid overloading the server.
- **Comprehensive Logging**: Logs the script's progress and any errors to `scraper.log` and the console.
- **Schema-Compliant Output**: Generates a CSV file (`blinkit_scraped_data.csv`) with columns matching the required schema.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd blinkit-scraper
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

Ensure the following input files are in the same directory as the script:
- `blinkit_locations.csv`
- `blinkit_categories.csv`
- `Scraping Task _ Schema - Schema.csv`

Then, execute the script from your terminal:

```bash
python blinkit_scraper.py# blinkit_data_scrapping
