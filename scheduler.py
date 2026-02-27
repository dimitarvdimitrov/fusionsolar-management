#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scheduler for FusionSolar Power Adjustment

This script implements a scheduler that runs the price analyzer every hour
to automatically adjust power limits based on electricity prices.
It also fetches prices for the next day on an hourly basis.
"""

import time
import datetime
import logging
import sys
import schedule
import price_analyzer
from storage_interface import create_storage
from price_repository import PriceRepository
from telegram_notifier import TelegramNotifier  # Import the new TelegramNotifier class
from config import PRICE_THRESHOLD  # Import price threshold for low power period calculation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# TIMEZONE is now imported from config.py


class Scheduler:
    """
    A class that handles scheduling and execution of recurring tasks
    for the FusionSolar Power Adjustment system.
    """
    
    def __init__(self):
        """Initialize the scheduler."""
        logger.info("Initializing Scheduler...")
        self.repository = PriceRepository(create_storage())
        self.telegram_notifier = TelegramNotifier()
    
    @staticmethod
    def _format_next_day_prices_message(price_data, next_day: datetime.datetime) -> str:
        """
        Format the Telegram notification message for next day prices including low power periods.
        
        Args:
            price_data: PriceData object containing price information
            next_day: datetime object representing the next day
            
        Returns:
            str: Formatted message string for Telegram notification
        """
        # Calculate low power periods for the notification
        low_power_periods = price_analyzer.get_low_power_periods(price_data, PRICE_THRESHOLD)
        
        # Format the low power periods for display
        if low_power_periods:
            periods_text = "\n".join([
                f"  • {start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
                for start, end in low_power_periods
            ])
            low_power_info = f"\n\n🔋 Периоди с ниска мощност:\n{periods_text}"
        else:
            low_power_info = "\n\n🔋 Няма периоди с ниска мощност за утре."
        
        return f"📊 Успешно изтеглени цени за {next_day.strftime('%Y-%m-%d')}:\n{price_data}{low_power_info}"
    
    def run_price_analyzer(self, force_notify: bool = False) -> bool:
        """
        Run the price analyzer and return the result.

        Args:
            force_notify: If True, always send failure notifications regardless of
                         power transition timing. Used for manual Lambda invocations.

        Returns:
            bool: True if the price analyzer ran successfully, False otherwise
        """
        try:
            logger.info("Running price analyzer...")
            result = price_analyzer.main(force_notify=force_notify)
            if result:
                logger.info("Price analyzer completed successfully")
            else:
                logger.error("Price analyzer failed")
            return result
        except Exception as e:
            logger.error(f"Error running price analyzer: {e}")
            return False

    def fetch_next_day_prices(self) -> bool:
        """
        Fetch prices for the next day using PriceRepository.

        Always scrapes fresh data from IBEX. If the new prices differ from stored
        prices (e.g., IBEX initially returned zeros that are now filled in),
        sends a Telegram notification with the updated price table.

        Returns:
            bool: True if prices were fetched successfully, False otherwise
        """
        next_day = datetime.datetime.now() + datetime.timedelta(days=1)
        next_day_str = next_day.strftime('%Y-%m-%d')

        try:
            logger.info(f"Scraping prices for {next_day_str}...")

            # Always scrape fresh data from IBEX.
            scraped_data = self.repository.scrape_prices()

            if not scraped_data.entries:
                logger.warning(f"No price entries scraped for {next_day_str}")
                self._notify_missing_prices(next_day)
                return False

            # Check if the scraped data is for the expected date.
            scraped_date = scraped_data.get_date().date()
            if scraped_date != next_day.date():
                logger.info(f"Scraped data is for {scraped_date}, not {next_day.date()} - IBEX hasn't published yet")
                self._notify_missing_prices(next_day)
                return False

            # Load existing stored data (if any) to compare.
            stored_data = self.repository.get_prices_for_date(next_day)

            # Determine what kind of notification to send.
            if stored_data is None:
                # First time fetching prices for this day.
                logger.info(f"First fetch of prices for {next_day_str}")
                message = self._format_next_day_prices_message(scraped_data, next_day)
                self.telegram_notifier.send_message(message)
            elif scraped_data != stored_data:
                # Prices have changed (e.g., zeros filled in with real values).
                logger.info(f"Price data for {next_day_str} has changed, sending update notification")
                message = self._format_price_update_message(scraped_data, next_day)
                self.telegram_notifier.send_message(message)
            else:
                # No change from stored data.
                logger.info(f"Price data for {next_day_str} unchanged")

            # Always persist the newly scraped data (overwrites old data).
            self.repository.persist_prices(scraped_data)

            logger.info(f"Successfully processed {len(scraped_data.entries)} price entries for {next_day_str}")
            return True

        except Exception as e:
            logger.error(f"Error fetching next day prices: {e}")
            self._notify_fetch_error(next_day, e)
            return False

    def _notify_missing_prices(self, next_day: datetime.datetime) -> None:
        """Send notification when prices are not available, but only after 6 PM."""
        current_hour = datetime.datetime.now().hour
        if current_hour >= 18:
            error_message = f"⚠️ Няма намерени цени за {next_day.strftime('%Y-%m-%d')}. Моля проверете дали данните са налични."
            try:
                self.telegram_notifier.send_message(error_message)
                logger.info("Sent Telegram notification for missing price data")
            except Exception as telegram_error:
                logger.error(f"Failed to send Telegram notification for missing price data: {telegram_error}")

    def _notify_fetch_error(self, next_day: datetime.datetime, error: Exception) -> None:
        """Send notification when fetching fails, but only after 6 PM."""
        current_hour = datetime.datetime.now().hour
        if current_hour >= 18:
            error_message = f"❌ Грешка при изтегляне на цените за {next_day.strftime('%Y-%m-%d')}: {str(error)}"
            try:
                self.telegram_notifier.send_message(error_message)
                logger.info("Sent Telegram error notification for failed price fetching")
            except Exception as telegram_error:
                logger.error(f"Failed to send Telegram error notification: {telegram_error}")

    @staticmethod
    def _format_price_update_message(price_data, next_day: datetime.datetime) -> str:
        """
        Format the Telegram notification message for updated prices.

        This is sent when previously stored prices differ from newly scraped prices
        (e.g., IBEX initially returned zeros that are now filled with real values).

        Args:
            price_data: PriceData object containing the new price information
            next_day: datetime object representing the next day

        Returns:
            str: Formatted message string for Telegram notification
        """
        # Calculate low power periods for the notification.
        low_power_periods = price_analyzer.get_low_power_periods(price_data, PRICE_THRESHOLD)

        # Format the low power periods for display.
        if low_power_periods:
            periods_text = "\n".join([
                f"  • {start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
                for start, end in low_power_periods
            ])
            low_power_info = f"\n\n🔋 Периоди с ниска мощност:\n{periods_text}"
        else:
            low_power_info = "\n\n🔋 Няма периоди с ниска мощност за утре."

        return f"🔄 Обновени цени за {next_day.strftime('%Y-%m-%d')}:\n{price_data}{low_power_info}"

    def schedule_jobs(self) -> None:
        """
        Schedule the price analyzer and next day price fetching to run every hour.
        """
        logger.info("Setting up scheduler...")
        
        # Schedule the price analyzer to run every hour at the 0 minute mark
        schedule.every().hour.at(":00").do(self.run_price_analyzer)
        
        # Schedule the next day price fetching to run every hour at the 30 minute mark
        # This is staggered to avoid running both tasks simultaneously
        schedule.every().hour.at(":30").do(self.fetch_next_day_prices)
        
        logger.info("Scheduler set up successfully")
        logger.info("Price analyzer will run every hour at :00")
        logger.info("Next day price fetching will run every hour at :30")
        
        # Keep the scheduler running indefinitely
        while True:
            try:
                # Run pending scheduled jobs
                schedule.run_pending()
                
                # Sleep for a short time to avoid high CPU usage
                time.sleep(30)  # Check for scheduled jobs every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait a bit longer if there was an error

    def start(self) -> None:
        """
        Start the scheduler.
        """
        logger.info("Starting FusionSolar Power Adjustment Scheduler")
        self.schedule_jobs()


if __name__ == "__main__":
    scheduler = Scheduler()
    scheduler.start() 
