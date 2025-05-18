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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scheduler.log')
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
        self.next_day_prices_fetched = self.repository.prices_for_day_exist(datetime.datetime.now() + datetime.timedelta(days=1))
        # Create a TelegramNotifier instance
        self.telegram_notifier = TelegramNotifier()
    
    def run_price_analyzer(self) -> bool:
        """
        Run the price analyzer and return the result.
        
        Returns:
            bool: True if the price analyzer ran successfully, False otherwise
        """
        try:
            logger.info("Running price analyzer...")
            result = price_analyzer.main()
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
        
        Returns:
            bool: True if prices were fetched successfully, False otherwise
        """
        try:
            logger.info("Fetching prices for next day...")
            
            # Get the current time in the configured timezone
            current_time = datetime.datetime.now()
            
            # Calculate the next day's date
            next_day = current_time + datetime.timedelta(days=1)

            # Try to fetch prices for the next day
            logger.info(f"Attempting to fetch prices for {next_day.strftime('%Y-%m-%d')}")
            price_data = self.repository.get_prices_for_date(next_day)
            
            if price_data and price_data.entries:
                if not self.next_day_prices_fetched:
                    self.telegram_notifier.send_message(f"📊 Успешно изтеглени цени за {next_day.strftime('%Y-%m-%d')}:\n{price_data}")
                    self.next_day_prices_fetched = True
                    
                logger.info(f"Successfully fetched {len(price_data.entries)} price entries for {next_day.strftime('%Y-%m-%d')}")
                return True
            else:
                self.next_day_prices_fetched = False
                logger.warning(f"No price entries found for {next_day.strftime('%Y-%m-%d')}")
                return False
                
        except Exception as e:
            self.next_day_prices_fetched = False
            logger.error(f"Error fetching next day prices: {e}")
            return False

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
