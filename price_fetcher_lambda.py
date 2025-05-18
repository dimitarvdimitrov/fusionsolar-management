#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda function for fetching next day electricity prices.
This is extracted from the scheduler's fetch_next_day_prices function.
"""

import logging
from storage_interface import create_storage
from price_repository import PriceRepository
from scheduler import Scheduler
from telegram_notifier import TelegramNotifier

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize dependencies once outside the handler
repository = PriceRepository(create_storage())
scheduler = Scheduler()
telegram_notifier = TelegramNotifier()

def lambda_handler(event, context):
    """
    AWS Lambda handler for fetching next day prices.
    Args:
        event (dict): Lambda event data
        context (LambdaContext): Lambda context object
    """
    if scheduler.fetch_next_day_prices():
        return {
            'statusCode': 200,
            'body': f"Successfully fetched price entries"
        }
    else:
        return {
            'statusCode': 404,
            'body': "No price data found for next day"
        }
