#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Electricity Price Analyzer for FusionSolar Power Adjustment

This script fetches current electricity prices, analyzes them, and automatically
adjusts the power limit on a Huawei FusionSolar SmartLogger based on price thresholds.
"""

import datetime
from storage_interface import StorageInterface, create_storage
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
    FUSIONSOLAR_PASSWORD,
    LOCATION_LATITUDE,
    LOCATION_LONGITUDE,
    LOCATION_NAME,
    LOCATION_COUNTRY
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

    def get_hourly_average(self, target_time: datetime.datetime) -> float:
        """
        Calculate the average price for the hour containing the given time.

        Args:
            target_time (datetime.datetime): The target time to calculate the hourly average for

        Returns:
            float: The average price for the hour

        Raises:
            ValueError: If there are no entries for the target hour
        """
        if not self.entries:
            raise ValueError("No price entries available")

        # Get the hour start and end times
        hour_start = target_time.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + datetime.timedelta(hours=1)

        # Find all entries within this hour
        hourly_entries = [
            entry for entry in self.entries
            if hour_start <= entry.time < hour_end
        ]

        if not hourly_entries:
            raise ValueError(f"No price entries found for hour starting at {hour_start}")

        # Calculate and return the average
        avg_price = sum(entry.price for entry in hourly_entries) / len(hourly_entries)
        return avg_price

    def __str__(self) -> str:
        """String representation of the price data collection with visual timeline"""
        if not self.entries:
            return f"PriceData: No entries, fetched at {self.fetch_time}"

        # Get price range for scaling
        prices = [entry.price for entry in self.entries]
        min_price = min(prices)
        max_price = max(prices)

        # Group entries by 2-hour periods
        period_prices = {}
        for entry in self.entries:
            period = entry.time.hour // 2  # 0-11 for 12 periods
            if period not in period_prices:
                period_prices[period] = []
            period_prices[period].append(entry.price)

        # Create visual timeline with 2-hour periods
        timeline = []
        timeline.append("Period    Avg   Min   Max")
        timeline.append("------   ----  ----  ----")

        for period in range(12):  # 12 periods of 2 hours each
            if period in period_prices:
                prices = period_prices[period]
                avg_price = sum(prices) / len(prices)
                min_period_price = min(prices)
                max_period_price = max(prices)
                
                start_hour = period * 2
                end_hour = start_hour + 2
                period_str = f"{start_hour:02d}-{end_hour:02d}h"

                timeline.append(f"{period_str}   {avg_price:4.1f}  {min_period_price:4.1f}  {max_period_price:4.1f}")
            else:
                # No data for this period
                start_hour = period * 2
                end_hour = start_hour + 2
                period_str = f"{start_hour:02d}-{end_hour:02d}h"
                timeline.append(f"{period_str}    --.-   --.-   --.-")

        # Add summary info
        timeline.append("")
        avg_price = sum(prices) / len(prices)
        timeline.append(f"Min: {min_price:.1f}  Max: {max_price:.1f}  Avg: {avg_price:.1f} EUR/MWh")
        timeline.append(f"Entries: {len(self.entries)}")

        # Return the timeline as plain text
        timeline_text = "\n".join(timeline)
        return timeline_text

    def llm_prompt(self) -> str:
        """Generate a VLM prompt to create a price chart image"""
        if not self.entries:
            return f"PriceData: No entries, fetched at {self.fetch_time}"

        # Get price data for the prompt
        prices = [entry.price for entry in self.entries]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)

        # Create hourly price list for the prompt
        hourly_data = []
        for i, entry in enumerate(self.entries):
            hourly_data.append(f"{i:02d}:00 → {entry.price:.1f}")

        # Generate VLM prompt
        prompt = f"""Create a clean line chart showing electricity prices over 24 hours:

Data points (Hour → Price in EUR/MWh):
{', '.join(hourly_data)}

Chart specifications:
- X-axis: Hours 00-23 with clear labels every 4 hours
- Y-axis: Price range {min_price:.1f} to {max_price:.1f} EUR/MWh
- Blue line chart with data points marked
- Grid lines for easy reading
- Title: "Electricity Prices - 24 Hour Profile"
- Subtitle: "Min: {min_price:.1f} | Avg: {avg_price:.1f} | Max: {max_price:.1f} EUR/MWh"
- Clean white background
- Styling suitable for a telegram message"""

        return prompt
# Configuration constants are now imported from config.py

# Create a TelegramNotifier instance
telegram_notifier = TelegramNotifier()

# Function definitions
# -------------------

def should_use_low_power(price_data: PriceData, target_time: datetime.datetime, price_threshold: float) -> bool:
    """
    Determine if low power should be used at the given time based on hourly average.

    Args:
        price_data (PriceData): Object containing price information
        target_time (datetime.datetime): The time to check
        price_threshold (float): The price threshold below which power should be low

    Returns:
        bool: True if low power should be used, False otherwise

    Raises:
        ValueError: If no price data is available for the target hour
    """
    hourly_avg = price_data.get_hourly_average(target_time)
    return hourly_avg < price_threshold

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
    Decide the power setting based on the hourly average price for the current hour.

    Args:
        price_data (PriceData): Object containing price information
        current_time (datetime.datetime): The current time

    Returns:
        str: The power setting to use (LOW_POWER_SETTING or HIGH_POWER_SETTING)
    """
    try:
        # Check if low power should be used based on hourly average
        if should_use_low_power(price_data, current_time, PRICE_THRESHOLD):
            hourly_avg = price_data.get_hourly_average(current_time)
            logger.info(f"Hourly average price ({hourly_avg:.2f}) is below threshold ({PRICE_THRESHOLD:.2f}), using low power: {LOW_POWER_SETTING}")
            return LOW_POWER_SETTING
        else:
            hourly_avg = price_data.get_hourly_average(current_time)
            logger.info(f"Hourly average price ({hourly_avg:.2f}) is above threshold ({PRICE_THRESHOLD:.2f}), using high power: {HIGH_POWER_SETTING}")
            return HIGH_POWER_SETTING

    except ValueError as e:
        # No price data available for this hour
        raise ValueError(f"Error determining power setting: {e}") from e

def get_low_power_periods(price_data: PriceData, price_threshold: float) -> List[tuple]:
    """
    Analyze PriceData to determine all time periods when power will be set to low power
    based on hourly averages.

    Args:
        price_data (PriceData): Object containing price information
        price_threshold (float): The price threshold below which power is set to low

    Returns:
        List[tuple]: List of (start_time, end_time) tuples representing low power periods.
                    Each tuple contains datetime objects marking the start and end of a low power period.

    Examples:
        - No low power periods: []
        - Single hour: [(datetime(2025, 1, 1, 14, 0), datetime(2025, 1, 1, 15, 0))]
        - Multiple ranges: [(datetime(2025, 1, 1, 2, 0), datetime(2025, 1, 1, 5, 0)),
                           (datetime(2025, 1, 1, 14, 0), datetime(2025, 1, 1, 16, 0))]
    """
    if not price_data.entries:
        return []

    # Get all unique hours from the entries
    hours = set()
    for entry in price_data.entries:
        hour_start = entry.time.replace(minute=0, second=0, microsecond=0)
        hours.add(hour_start)

    # Sort hours
    sorted_hours = sorted(hours)

    low_power_periods = []
    current_range_start = None

    for hour in sorted_hours:
        try:
            is_low_power = should_use_low_power(price_data, hour, price_threshold)

            if is_low_power and current_range_start is None:
                # Start of a new low power period
                current_range_start = hour
            elif not is_low_power and current_range_start is not None:
                # End of current low power period
                low_power_periods.append((current_range_start, hour))
                current_range_start = None
        except ValueError:
            # No data for this hour, skip it
            if current_range_start is not None:
                # End the current period at the previous hour
                low_power_periods.append((current_range_start, hour))
                current_range_start = None

    # Handle case where the last hour is still in a low power period
    if current_range_start is not None:
        # End the period at the last hour + 1 hour
        end_time = sorted_hours[-1] + datetime.timedelta(hours=1)
        low_power_periods.append((current_range_start, end_time))

    return low_power_periods


def is_daylight_with_times(current_time: datetime.datetime) -> dict:
    """
    Check if the current time is between sunrise and sunset and return times.
    
    Args:
        current_time (datetime.datetime): The current time to check
        
    Returns:
        dict: Contains 'is_daylight' (bool), 'sunrise' (datetime), 'sunset' (datetime)
    """
    from astral import LocationInfo
    from astral.sun import sun
    
    # Create location info
    location = LocationInfo(
        name=LOCATION_NAME,
        region=LOCATION_COUNTRY,
        timezone=str(TIMEZONE),
        latitude=LOCATION_LATITUDE,
        longitude=LOCATION_LONGITUDE
    )
    
    # Get sunrise and sunset times for the current date
    current_date = current_time.date()
    solar_times = sun(location.observer, date=current_date, tzinfo=TIMEZONE)
    sunrise = solar_times['sunrise']
    sunset = solar_times['sunset']

    is_day = sunrise <= current_time <= sunset
    logger.info(f"Solar times for {current_date}: sunrise={sunrise.strftime('%H:%M')}, sunset={sunset.strftime('%H:%M')}, is_daylight={is_day}")

    return {
        'is_daylight': is_day,
        'sunrise': sunrise,
        'sunset': sunset
    }


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

        # Check if it's daylight (between sunrise and sunset)
        daylight_info = is_daylight_with_times(current_time)
        if not daylight_info['is_daylight']:
            sunrise_time = daylight_info['sunrise'].strftime('%H:%M')
            sunset_time = daylight_info['sunset'].strftime('%H:%M')
            logger.info(f"It's nighttime - skipping power changes as inverters are automatically shut down: sunrise ({sunrise_time}), sunset ({sunset_time}).")
            return True

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
        from set_power import SetPower
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
        hourly_avg = price_data.get_hourly_average(current_time)
        if power_setting == LOW_POWER_SETTING:
            telegram_notifier.send_message(f"✅ Мощността е зададена на НИСКА ({LOW_POWER_SETTING} kW) - средна цена за часа ({hourly_avg:.2f} EUR/MWh) е под прага ({PRICE_THRESHOLD:.2f} EUR/MWh).")
        else:
            telegram_notifier.send_message(f"✅ Мощността е зададена на {HIGH_POWER_SETTING} - средна цена за часа ({hourly_avg:.2f} EUR/MWh) е над прага ({PRICE_THRESHOLD:.2f} EUR/MWh).")

    return True


if __name__ == "__main__":
    main()
