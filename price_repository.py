#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Price Repository for FusionSolar Power Adjustment

This module provides a repository for electricity price data, managing both 
the retrieval from online sources and local storage for historical data access.
"""

import os
import datetime
import pytz
from typing import Optional, Tuple
import requests
from io import StringIO
import pandas as pd
import logging
from config import TIMEZONE, LOCAL_STORAGE_DIR

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
    
    def __init__(self, storage_dir: str = LOCAL_STORAGE_DIR):
        """
        Initialize the price repository.
        
        Args:
            storage_dir (str): Directory where price history is stored
        """
        # Directory for storing price history
        self.storage_dir = storage_dir
        
        # Create storage directory if it doesn't exist
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            logger.info(f"Created storage directory: {self.storage_dir}")
    
    def get_prices_for_date(self, target_date: datetime.datetime) -> PriceData:
        """
        Get price data for the day containing the specified datetime.
        
        The function first checks if we have the data locally, and if not,
        fetches it from the online source and saves it locally.
        
        Args:
            target_date (datetime.datetime): The datetime for which to get price data
            
        Returns:
            PriceData: Price data for the day containing the target date
            
        Raises:
            Exception: If price data cannot be retrieved after attempting to fetch and store
        """
        logger.info(f"Getting prices for date: {target_date}")
        
        # 1. First, check if we have local data for the target date
        local_data = self._get_local_data(target_date)
        if local_data:
            logger.info(f"Found local price data for {target_date}")
            return local_data
        
        # We won't be able to fetch data for today.
        if target_date.date() == datetime.datetime.now(pytz.timezone(TIMEZONE)).date():
            raise Exception(f"No local data available for today ({target_date}) and day ahead prices are already gone")
        
        # 2. If local data doesn't exist, fetch from online source and save locally
        logger.info(f"No local data found for {target_date}, fetching from online source")
        self._fetch_and_store_data()
        logger.info(f"Successfully fetched and stored price data for {target_date}")
        
        # 3. Try to get local data again after fetching
        local_data = self._get_local_data(target_date)
        if local_data:
            return local_data
        else:
            # 4. If still no local data, raise exception
            raise Exception(f"Failed to retrieve local data after fetching for {target_date}")
    
    def _get_local_data(self, date: datetime.datetime) -> Optional[PriceData]:
        """
        Try to get price data from local storage for the specified date.
        
        Args:
            date (datetime.datetime): The date for which to retrieve local data
            
        Returns:
            Optional[PriceData]: Price data if found, None otherwise
        """
        # 1. Generate the filename from the date
        filename = self._generate_parsed_filename(date)
        
        # 2. Check if the file exists
        if not os.path.exists(filename):
            logger.info(f"Local data file not found: {filename}")
            return None
        
        try:
            # 3. Read and parse the file into a PriceData object
            with open(filename, 'r') as file:
                json_data = file.read()
                
            # Use dataclass_json to deserialize directly to PriceData
            price_data = PriceData.from_json(json_data)

            tz = pytz.timezone(TIMEZONE)
            # Localize each entry's time if needed
            for entry in price_data.entries:
                if entry.time.tzinfo is None:
                    entry.time = tz.localize(entry.time)
                elif entry.time.tzinfo != tz:
                    entry.time = entry.time.astimezone(tz)
            
            logger.info(f"Successfully loaded local price data from {filename}: {len(price_data.entries)} entries")
            return price_data
                
        except Exception as e:
            logger.error(f"Error loading local price data from {filename}: {e}")
            return None
    
    def _fetch_and_store_data(self):
        """
        Fetch price data from online source and store it locally.
        
        Returns:
            Tuple[PriceData, datetime.datetime]: The fetched price data and the fetch time
            
        Raises:
            Exception: If data can't be fetched or parsed
        """
        try:
            # 1. Fetch data from online source
            html_content = self._fetch_online_data()
            
            # 2. Parse the data into a PriceData object
            price_data = self._parse_price_table(html_content)
            
            # Get current time in the configured timezone
            data_date = price_data.get_date()
            
            # Check if we already have this data stored locally using _get_local_data
            existing_data = self._get_local_data(data_date)
            if existing_data:
                logger.info(f"Price data for {data_date.strftime('%Y-%m-%d')} already exists on disk")
                if existing_data.entries != price_data.entries:
                    raise Exception(f"Price data for {data_date.strftime('%Y-%m-%d')} already exists on disk but is different: existing {existing_data} != fetched {price_data}")
            
            # 3. Store the data locally if it doesn't exist
            self._store_local_data(data_date, price_data, html_content)
            
        except Exception as e:
            logger.error(f"Error in fetch_and_store_data: {e}")
            raise Exception(f"Failed to fetch and store price data: {e}") from e
    
    def _fetch_online_data(self) -> str:
        """
        Fetch the HTML page containing electricity price information.
        
        Returns:
            str: HTML content of the price page
            
        Raises:
            Exception: If the page cannot be fetched
        """
        try:
            # URL for the electricity price data
            # use /en to get EUR prices
            url = "https://ibex.bg/en/"
            
            # Set up headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            
            # Send the GET request
            logger.info(f"Fetching price data from {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Get the content as text
            html_content = response.text
            logger.info(f"Successfully fetched price data, content length: {len(html_content)} chars")
            
            return html_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch price data: {e}")
            raise Exception(f"Error fetching price data: {e}") from e
    
    def _parse_price_table(self, html_content: str) -> PriceData:
        """
        Parse the HTML content to extract price data from tables.
        
        Args:
            html_content (str): HTML content containing price tables
                Note: This parameter is kept for compatibility but not used.
                Instead, we read directly from the file path.
        
        Returns:
            PriceData: Object containing structured price information
        """
        try:
            # Use pandas to read all HTML tables from the file
            tables = pd.read_html(StringIO(html_content))
            logger.info(f"Found {len(tables)} tables in the HTML file")
            
            # Based on our analysis, Table 1 (index 1) contains the price data
            if len(tables) < 2:
                raise Exception("Expected price table not found in HTML file")
            
            # Get the price table
            price_table = tables[1]
            logger.info(f"Processing price table with shape: {price_table.shape}")
            
            # Get timezone for datetime conversion
            tz = pytz.timezone(TIMEZONE)
            
            # Create PriceEntry objects from table rows
            entries = []
            for _, row in price_table.iterrows():
                try:
                    # Extract date, time and price from the row
                    date_str = str(row[0])  # First column is date
                    time_str = str(row[1])  # Second column is time
                    price_str = str(row[2])  # Third column is price
                    
                    # Create full datetime string and parse it
                    datetime_str = f"{date_str} {time_str}"
                    dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    
                    # Localize the datetime to the specified timezone
                    dt = tz.localize(dt)
                    
                    # Convert price to float
                    price = float(price_str)
                    
                    # Create and add PriceEntry
                    entry = PriceEntry(time=dt, price=price)
                    entries.append(entry)
                    logger.debug(f"Parsed entry: {entry}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {row}: {e}")
            
            logger.info(f"Successfully parsed {len(entries)} price entries")
            
            # Create PriceData object
            price_data = PriceData(
                entries=entries,
                fetch_time=datetime.datetime.now(tz)
            )
            
            # If no entries were parsed, fall back to dummy data
            if not entries:
                raise Exception("No price entries could be parsed from the table")
            
            return price_data
            
        except Exception as e:
            raise Exception(f"Error parsing price table: {e}") from e
    
    def _store_local_data(self, date: datetime.datetime, price_data: PriceData, html_content: str):
        """
        Store price data locally for future retrieval.
        
        Args:
            date (datetime.datetime): The date for which the data is relevant
            price_data (PriceData): The price data to store
            html_content (str): The raw HTML content to store, if provided
            
        Returns:
            None
            
        Raises:
            Exception: If the data cannot be stored locally
        """
        try:
            # 1. Generate the filename from the date
            filename = self._generate_parsed_filename(date)

            # 2. Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)
          
            # 3. Convert PriceData to JSON using dataclass_json
            json_data = price_data.to_json(indent=2)
            
            # 4. Write the data to the file
            with open(filename, 'w') as file:
                file.write(json_data)
                
            logger.info(f"Successfully stored price data to {filename}")
            
            # 5. Store raw HTML content if provided
            raw_filename = self._generate_raw_filename(date)
            with open(raw_filename, 'w', encoding='utf-8') as file:
                file.write(html_content)
            logger.info(f"Successfully stored raw HTML content to {raw_filename}")
            
        except Exception as e:
            logger.error(f"Error storing price data to file: {e}")
            raise Exception(f"Failed to store price data locally: {e}") from e
    
    def _generate_parsed_filename(self, date: datetime.datetime) -> str:
        """
        Generate a filename for local storage based on the date.
        
        Args:
            date (datetime.datetime): The date for which to generate a filename
            
        Returns:
            str: The generated filename
        """
        return f"{self.storage_dir}/ibex.bg-{date.strftime('%Y-%m-%d')}.json"
    
    def _generate_raw_filename(self, date: datetime.datetime) -> str:
        """
        Generate a filename for raw data storage based on the date.
        
        Args:
            date (datetime.datetime): The date for which to generate a filename
            
        Returns:
            str: The generated filename
        """
        return f"{self.storage_dir}/ibex.bg-{date.strftime('%Y-%m-%d')}.html"
