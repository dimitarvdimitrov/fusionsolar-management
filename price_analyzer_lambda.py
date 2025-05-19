#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda function for analyzing electricity prices and setting power limits.
This is extracted from the scheduler's price_analyzer functionality.
"""
try:
    import unzip_requirements
except ImportError:
    pass

import logging
from scheduler import Scheduler
from telegram_notifier import TelegramNotifier

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the TelegramNotifier once outside the handler
telegram_notifier = TelegramNotifier()
scheduler = Scheduler()

def lambda_handler(event, context):
    """
    AWS Lambda handler for analyzing prices and setting power limits.
    
    Args:
        event (dict): Lambda event data
        context (LambdaContext): Lambda context object
    
    Returns:
        dict: Response containing success status and message
    """
    if scheduler.run_price_analyzer():
        return {
            'statusCode': 200,
            'body': "Price analyzer completed successfully"
        }
    else:
        return {
            'statusCode': 500,
            'body': "Price analyzer failed"
        }
