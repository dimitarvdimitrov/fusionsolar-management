#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Module for FusionSolar Power Adjustment

This module centralizes all configuration settings and secrets used across
the FusionSolar Power Adjustment system.
"""

import os
import pytz
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Time zone for proper time comparison
TIMEZONE = "Europe/Sofia"  # Adjust to your local timezone

# FusionSolar credentials
FUSION_USERNAME = ""
FUSION_PASSWORD = ""

# Price threshold in the appropriate currency (e.g., EUR/MWh)
PRICE_THRESHOLD = 15.04

# Power settings (in kW)
LOW_POWER_SETTING = "5.000"     # Power limit when prices are high
HIGH_POWER_SETTING = "600.000"  # Power limit when prices are low

# Telegram configuration constants
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Default directory for storing screenshots
SCREENSHOT_DIR = os.environ.get("FUSIONSOLAR_SCREENSHOT_DIR", "/tmp/fusionsolar_management/screenshots")

# Directory for storing price history
LOCAL_STORAGE_DIR = os.environ.get("FUSIONSOLAR_PRICE_STORAGE_DIR", "/tmp/fusionsolar_management/prices") 