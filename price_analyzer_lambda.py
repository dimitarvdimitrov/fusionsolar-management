#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda function for analyzing electricity prices and setting power limits.
"""

import logging
from scheduler import Scheduler
from telegram_notifier import TelegramNotifier

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the TelegramNotifier once outside the handler
telegram_notifier = TelegramNotifier()
scheduler = Scheduler()


def is_scheduled_event(event: dict) -> bool:
    """
    Check if the Lambda was invoked by a CloudWatch Events / EventBridge scheduled rule.

    Scheduled events have a specific structure with:
    - "detail-type": "Scheduled Event"
    - "source": "aws.events" or "aws.scheduler"

    Manual invocations (console, CLI, SDK) typically have an empty dict or custom payload.
    """
    if not isinstance(event, dict):
        return False
    detail_type = event.get("detail-type", "")
    source = event.get("source", "")
    return detail_type == "Scheduled Event" and source in ("aws.events", "aws.scheduler")


def lambda_handler(event, context):
    """
    AWS Lambda handler for analyzing prices and setting power limits.

    Args:
        event (dict): Lambda event data
        context (LambdaContext): Lambda context object

    Returns:
        dict: Response containing success status and message
    """
    # Manual triggers should always notify on failure.
    force_notify = not is_scheduled_event(event)

    if scheduler.run_price_analyzer(force_notify=force_notify):
        return {
            'statusCode': 200,
            'body': "Price analyzer completed successfully"
        }
    else:
        return {
            'statusCode': 500,
            'body': "Price analyzer failed"
        }
