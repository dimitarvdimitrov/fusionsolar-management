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
        
    async def send_async_message(self, message: str) -> bool:
        """
        Send a message to the configured Telegram chat asynchronously.

        Args:
            message (str): The message to send

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        try:
            bot = telegram.Bot(token=self.bot_token)
            await bot.send_message(chat_id=self.chat_id, text=message)
            logger.info(f"Telegram message sent: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_async_photo(self, photo: bytes, caption: Optional[str] = None) -> bool:
        """
        Send a photo to the configured Telegram chat asynchronously.

        Args:
            photo: The image data to send (PNG/JPEG).
            caption: Caption text for the photo (max 1024 chars).

        Returns:
            True if the photo was sent successfully, False otherwise.
        """
        try:
            bot = telegram.Bot(token=self.bot_token)
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=photo,
                caption=caption
            )
            logger.info("Telegram photo sent")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")
            return False

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

    def send_photo(self, photo: bytes, caption: Optional[str] = None) -> bool:
        """
        Synchronous wrapper for sending Telegram photos.

        Args:
            photo: The image data to send (PNG/JPEG).
            caption: Caption text for the photo (max 1024 chars).

        Returns:
            True if the photo was sent successfully, False otherwise.
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.send_async_photo(photo, caption))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in Telegram photo notification: {e}")
            return False