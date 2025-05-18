#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Electricity Price Analyzer for FusionSolar Power Adjustment

This script fetches current electricity prices, analyzes them, and automatically
adjusts the power limit on a Huawei FusionSolar SmartLogger based on price thresholds.
"""

import datetime
from storage_interface import StorageInterface, create_storage
from set_power import SetPower
import logging
import sys
from typing import List, Optional
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from telegram_notifier import TelegramNotifier
from config import (
    TIMEZONE, 
    PRICE_THRESHOLD, 
    LOW_POWER_SETTING, 
    HIGH_POWER_SETTING, 
    FUSIONSOLAR_USERNAME, 
    FUSIONSOLAR_PASSWORD
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass_json
@dataclass
class PriceEntry:
    """Data class representing a single electricity price entry"""
    time: datetime.datetime
    price: float
    
    def __str__(self) -> str:
        """String representation of a price entry"""
        return f"{self.time.strftime('%Y-%m-%d %H:%M')} - {self.price:.2f} EUR/MWh"

@dataclass_json
@dataclass
class PriceData:
    """Container for a collection of price entries"""
    entries: List[PriceEntry]
    fetch_time: datetime.datetime
    
    def __post_init__(self):
        """Sort entries by time after initialization"""
        self.entries.sort(key=lambda entry: entry.time)

    def get_date(self) -> datetime.datetime:
        """
        Get the date of the price entries.
        
        Returns:
            datetime.datetime: The date of the entries
            
        Raises:
            Exception: If entries contain multiple dates
        """
        if not self.entries:
            raise Exception("No entries in price data")
            
        # Get the date (without time) from the first entry
        first_date = self.entries[0].time.date()
        
        # Check if all entries have the same date
        for entry in self.entries:
            if entry.time.date() != first_date:
                raise Exception("Price data contains entries from multiple dates")
        
        # Return the datetime with the date from entries and time set to midnight
        return datetime.datetime.combine(first_date, datetime.time.min, tzinfo=self.entries[0].time.tzinfo)
    
    def get_closest_entry(self, target_time: datetime.datetime) -> Optional[PriceEntry]:
        """
        Find the closest entry in the future relative to the given time.
        
        Args:
            target_time (datetime.datetime): The target time to find the closest future entry for
            
        Returns:
            Optional[PriceEntry]: The closest future price entry
            
        Raises:
            ValueError: If there are no future entries available
        """
        if not self.entries:
            raise ValueError("No price entries available")
            
        # Find the closest entry to the target time
        closest_entry = None
        min_time_diff = float('inf')
        
        for entry in self.entries:
            time_diff = abs((entry.time - target_time).total_seconds())
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_entry = entry
            
        return closest_entry
    
    def __str__(self) -> str:
        """String representation of the price data collection"""
        entries_str = "\n".join([str(entry) for entry in self.entries])
        return f"PriceData: {len(self.entries)} entries, fetched at {self.fetch_time}:\n{entries_str}"

# Configuration constants are now imported from config.py

# Create a TelegramNotifier instance
telegram_notifier = TelegramNotifier()

# Function definitions
# -------------------

def fetch_price_data(current_time: datetime.datetime, storage: StorageInterface) -> PriceData:
    """
    Fetch price data using the PriceRepository.
    
    This function uses PriceRepository to get the price data for the current time,
    either from local storage or by fetching from the online source.
    
    Returns:
        PriceData: Object containing structured price information
    
    Raises:
        Exception: If price data cannot be fetched
    """
    try:
        # Import PriceRepository here to avoid circular import
        from price_repository import PriceRepository
        
        # Create a price repository instance
        repository = PriceRepository(storage)
        
        # Get price data for the current time
        price_data = repository.get_prices_for_date(current_time)
        
        logger.info(f"Successfully retrieved price data: {len(price_data.entries)} entries")
        return price_data
    except Exception as e:
        raise Exception(f"Failed to fetch price data: {e}") from e


def decide_power_setting(price_data: PriceData, current_time: datetime.datetime) -> str:
    """
    Decide the power setting based on the price for the next hour.
    
    Args:
        price_data (PriceData): Object containing price information
        current_time (datetime.datetime): The current time
    
    Returns:
        str: The power setting to use (LOW_POWER_SETTING or HIGH_POWER_SETTING)
    """

    try:
        # Find the closest future price entry
        next_price_entry = price_data.get_closest_entry(current_time)
        
        if not next_price_entry:
            raise ValueError("No price entry found")
            
        # Check if the closest entry is more than 2 hours away from now
        time_diff = abs((next_price_entry.time - current_time).total_seconds()) / 3600
        if time_diff > 2:
            raise ValueError(f"Closest entry is more than 2 hours away from current time (difference: {time_diff:.2f} hours)")
        
        logger.info(f"Next price entry: {next_price_entry}")
        logger.info(f"Price: {next_price_entry.price} (threshold: {PRICE_THRESHOLD})")
        
        # Compare the price against the threshold
        if next_price_entry.price < PRICE_THRESHOLD:
            logger.info(f"Price is below threshold, setting power to LOW: {LOW_POWER_SETTING}")
            return LOW_POWER_SETTING
        else:
            logger.info(f"Price is above threshold, setting power to HIGH: {HIGH_POWER_SETTING}")
            return HIGH_POWER_SETTING
    
    except ValueError as e:
        # No future price entries available
        raise ValueError(f"Error determining power setting: {e}") from e


def main():
    """
    Main function to orchestrate the price analysis and power setting.
    """
    power_changed = False
    power_setting = None
    
    try:
        logger.info("Starting electricity price analysis")
        
        # Get current time
        current_time = datetime.datetime.now(TIMEZONE)
        logger.info(f"Current time: {current_time}")

        # Initialize storage interface
        storage = create_storage()

        # Fetch price data using the repository
        logger.info("Fetching price data using PriceRepository")
        price_data = fetch_price_data(current_time, storage)
        logger.info(f"Parsed {len(price_data.entries)} price entries")
        logger.info(f"Price data: {price_data}")


        # Decide power setting
        logger.info("Deciding power setting based on price")
        power_setting = decide_power_setting(price_data, current_time)
        
        # Apply the power setting
        logger.info(f"Setting power to {power_setting} kW")
        power_setter = SetPower(FUSIONSOLAR_USERNAME, FUSIONSOLAR_PASSWORD, storage)
        result = power_setter.set_power_limit(power_setting)
        
        if result:
            logger.info("Power setting successfully applied")
            power_changed = True
        else:
            logger.info("Power setting is already applied")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        # Send error notification
        telegram_notifier.send_message(f"❌ Грешка при анализ на цените: {str(e)}")
        return False
    
    # Send completion notification
    if power_changed:
        if power_setting == LOW_POWER_SETTING:
            telegram_notifier.send_message(f"✅ Мощността е зададена на НИСКА ({LOW_POWER_SETTING} kW) - цената ({price_data.get_closest_entry(current_time)}) е под прага ({PRICE_THRESHOLD:.2f} EUR/MWh).")
        else:
            telegram_notifier.send_message(f"✅ Мощността е зададена на {HIGH_POWER_SETTING} - цената ({price_data.get_closest_entry(current_time)}) е над прага ({PRICE_THRESHOLD:.2f} EUR/MWh).")

    return True


if __name__ == "__main__":
    main()
