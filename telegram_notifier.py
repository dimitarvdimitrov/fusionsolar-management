#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Notification Module for FusionSolar Power Adjustment

This module provides a centralized way to send Telegram notifications
across different parts of the application.
"""

import logging
import asyncio
import telegram
import time
import random
from typing import Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Configure logging
logger = logging.getLogger(__name__)

# Telegram configuration constants are now imported from config.py

class TelegramNotifier:
    """
    A class that handles sending notifications to Telegram.
    """
    
    def __init__(self):
        """
        Initialize the TelegramNotifier.
        """
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        
    async def send_async_message(self, message: str, max_retries: int = 3, base_delay: float = 1.0) -> bool:
        """
        Send a message to the configured Telegram chat asynchronously with retry and exponential backoff.
        
        Args:
            message (str): The message to send
            max_retries (int): Maximum number of retry attempts (default: 3)
            base_delay (float): Base delay in seconds for exponential backoff (default: 1.0)
            
        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        bot = telegram.Bot(token=self.bot_token)
        
        for attempt in range(max_retries + 1):
            try:
                await bot.send_message(chat_id=self.chat_id, text=message)
                logger.info(f"Telegram message sent successfully on attempt {attempt + 1}: {message}")
                return True
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to send Telegram message after {max_retries + 1} attempts: {e}")
                    return False
                
                # Calculate exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Telegram message send failed on attempt {attempt + 1}, retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)

    def send_message(self, message: str) -> bool:
        """
        Synchronous wrapper for sending Telegram messages.
        
        Args:
            message (str): The message to send
            
        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        try:
            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async function in the loop
            result = loop.run_until_complete(self.send_async_message(message))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in Telegram notification: {e}")
            return False 