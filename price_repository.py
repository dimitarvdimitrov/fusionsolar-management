#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Price Repository for FusionSolar Power Adjustment

This module provides a repository for electricity price data, managing both 
the retrieval from online sources and local storage for historical data access.
"""

import os
import datetime
from typing import Optional, Tuple
import requests
import json
import logging
from config import (
    TIMEZONE, 
    IBEX_TIMEZONE, 
    LOCAL_STORAGE_DIR,
    STORAGE_TYPE,
    S3_BUCKET_NAME,
    S3_REGION,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY
)
from storage_interface import StorageInterface, LocalFileStorage, S3Storage

# Import the PriceData and PriceEntry classes from price_analyzer
from price_analyzer import PriceData, PriceEntry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PriceRepository:
    """
    Repository class for managing electricity price data.
    
    This class handles:
    1. Fetching current price data from online sources
    2. Storing price data locally for historical access
    3. Retrieving historical price data based on a datetime
    """
    
    def __init__(self, storage: StorageInterface):
        """
        Initialize the price repository.
        """
        # Storage implementation
        self.storage = storage

    def get_prices_for_date(self, target_date: datetime.datetime) -> Optional[PriceData]:
        """
        Get stored price data for the day containing the specified datetime.

        This method only reads from storage; it does not fetch from online sources.
        Use scrape_prices() to fetch fresh data from IBEX.

        Args:
            target_date (datetime.datetime): The datetime for which to get price data

        Returns:
            Optional[PriceData]: Price data for the day if found, None otherwise
        """
        logger.info(f"Getting stored prices for date: {target_date}")
        return self._get_stored_data(target_date)

    def scrape_prices(self) -> PriceData:
        """
        Fetch prices from the IBEX API without any storage interaction.

        This method always fetches fresh data from the online source. It does not
        check or update storage. Use persist_prices() to store the result.

        Returns:
            PriceData: The freshly fetched price data

        Raises:
            Exception: If data cannot be fetched or parsed
        """
        logger.info("Scraping prices from IBEX API")
        json_content = self._fetch_online_data()
        price_data = self._parse_price_table(json_content)
        logger.info(f"Successfully scraped price data for {price_data.get_date().strftime('%Y-%m-%d')}")
        return price_data

    def persist_prices(self, price_data: PriceData) -> None:
        """
        Store price data to storage.

        This method stores the given price data, overwriting any existing data
        for the same date.

        Args:
            price_data (PriceData): The price data to store

        Raises:
            Exception: If data cannot be stored
        """
        data_date = price_data.get_date()
        logger.info(f"Persisting price data for {data_date.strftime('%Y-%m-%d')}")

        # Serialize the price data to JSON for storage.
        parsed_json_data = price_data.to_json(indent=2)
        parsed_filename = self._generate_parsed_filename(data_date)

        if self.storage.write_text(parsed_filename, parsed_json_data):
            logger.info(f"Successfully stored price data to {parsed_filename}")
        else:
            raise Exception(f"Failed to write price data to {parsed_filename}")
    
    def _get_stored_data(self, date: datetime.datetime) -> Optional[PriceData]:
        """
        Try to get price data from storage for the specified date.
        
        Args:
            date (datetime.datetime): The date for which to retrieve data
            
        Returns:
            Optional[PriceData]: Price data if found, None otherwise
        """
        # Generate the filename from the date
        filename = self._generate_parsed_filename(date)

        try:
            # 3. Read and parse the file into a PriceData object
            json_data = self.storage.read_text(filename)
            if json_data is None:
                return None
                
            # Use dataclass_json to deserialize directly to PriceData
            price_data = PriceData.from_json(json_data)

            tz = TIMEZONE
            # Localize each entry's time if needed
            for entry in price_data.entries:
                if entry.time.tzinfo is None:
                    entry.time = tz.localize(entry.time)
                elif entry.time.tzinfo != tz:
                    entry.time = entry.time.astimezone(tz)
            
            logger.info(f"Successfully loaded stored price data from {filename}: {len(price_data.entries)} entries")
            return price_data
                
        except Exception as e:
            logger.error(f"Error loading stored price data from {filename}: {e}")
            return None
    
    def _fetch_online_data(self) -> str:
        """
        Fetch the JSON data containing electricity price information.

        Uses Playwright browser automation to bypass JavaScript-based bot protection.

        Returns:
            str: JSON content of the price data

        Raises:
            Exception: If the data cannot be fetched
        """
        from playwright.sync_api import sync_playwright

        api_url = "https://ibex.bg/Ext/IDM_Homepage/fetch_dam.php?lang=en&num=40"

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    args=["--disable-gpu", "--single-process"]
                )
                context = browser.new_context()
                page = context.new_page()

                # Navigate to the API URL - Playwright handles JS challenges automatically
                logger.info(f"Fetching price data from {api_url} using Playwright")
                page.goto(api_url, wait_until="networkidle", timeout=60000)

                # Wait for JSON content to appear (starts with '[')
                page.wait_for_function(
                    "document.body.innerText.trim().startsWith('[')",
                    timeout=30000
                )

                # Get the page content (should be JSON)
                json_content = page.inner_text("body")
                logger.info(f"Successfully fetched price data, content length: {len(json_content)} chars")

                browser.close()
                return json_content

        except Exception as e:
            logger.error(f"Failed to fetch price data with Playwright: {e}")
            raise Exception(f"Error fetching price data: {e}") from e
    
    def _parse_price_table(self, json_content: str) -> PriceData:
        """
        Parse the JSON content to extract price data.
        
        Args:
            json_content (str): JSON content containing price data array
        
        Returns:
            PriceData: Object containing structured price information
        """
        try:
            # Parse JSON content
            price_list = json.loads(json_content)
            logger.info(f"Found {len(price_list)} price entries in JSON data")
            
            tz = IBEX_TIMEZONE
            
            # Create PriceEntry objects from JSON array
            entries = []
            for item in price_list:
                try:
                    # Extract date and price from the JSON object
                    date_str = item['date']  # Format: "YYYY-MM-DD HH:MM:SS"
                    price_value = float(item['price'])
                    
                    # Parse datetime string
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    
                    # Localize the datetime to the specified timezone
                    dt = tz.localize(dt)
                    
                    # Create and add PriceEntry
                    entry = PriceEntry(time=dt, price=price_value)
                    entries.append(entry)
                    logger.debug(f"Parsed entry: {entry}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing JSON item {item}: {e}")
            
            logger.info(f"Successfully parsed {len(entries)} price entries")
            
            # Create PriceData object
            price_data = PriceData(
                entries=entries,
                fetch_time=datetime.datetime.now(tz)
            )
            
            # If no entries were parsed, raise exception
            if not entries:
                raise Exception("No price entries could be parsed from the JSON data")
            
            return price_data
            
        except Exception as e:
            raise Exception(f"Error parsing price JSON: {e}") from e
    
    @staticmethod
    def _generate_parsed_filename(date: datetime.datetime) -> str:
        """
        Generate a filename for storage based on the date.
        
        Args:
            date (datetime.datetime): The date for which to generate a filename
            
        Returns:
            str: The generated filename
        """
        return f"prices/parsed/ibex.bg-{date.strftime('%Y-%m-%d')}.json"
