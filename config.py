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
import json
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# AWS Secrets Manager Configuration
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")
USE_SECRETS_MANAGER = os.environ.get("USE_SECRETS_MANAGER", "true").lower() == "true"
SECRETS_MANAGER_SECRET_NAME = os.environ.get("SECRETS_MANAGER_SECRET_NAME", "FusionSolarSecrets")

def get_secret(secret_name):
    """
    Retrieve a secret from AWS Secrets Manager.
    
    Args:
        secret_name (str): The name of the secret to retrieve
        
    Returns:
        str: The secret value if successful, None otherwise
    """
    if not USE_SECRETS_MANAGER:
        raise EnvironmentError(f"AWS Secrets Manager is not enabled and {secret_name} env var is not set. Set USE_SECRETS_MANAGER=true")

    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=AWS_REGION
        )
        
        # Get the secret
        get_secret_value_response = client.get_secret_value(SecretId=SECRETS_MANAGER_SECRET_NAME)
        
        # Handle binary or string secret
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            # Check if the secret is a JSON string
            try:
                secret_dict = json.loads(secret)
                # If the secret name is in the dictionary, return that value
                if secret_name in secret_dict:
                    return secret_dict[secret_name]
                # Otherwise return the whole JSON string
                return secret
            except json.JSONDecodeError:
                # If not JSON, return the raw string
                return secret
        else:
            raise ValueError(f"Secret {SECRETS_MANAGER_SECRET_NAME} is not in string format, which is not supported")

    except ClientError as e:
        logger.error(f"Error retrieving secret {SECRETS_MANAGER_SECRET_NAME}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving secret {SECRETS_MANAGER_SECRET_NAME}: {e}")
        return None

def get_config_value(env_var_name, default_value=None, allow_empty=False):
    """
    Get a configuration value from environment variables or Secrets Manager.
    
    Args:
        env_var_name (str): The name of the environment variable
        default_value (any, optional): Default value if not found
        allow_empty (bool, optional): Allow empty values to be returned
        
    Returns:
        any: The configuration value
    """
    # First check environment variables
    env_value = os.environ.get(env_var_name)
    if env_value is not None:
        return env_value
        
    # Then check Secrets Manager
    secret_value = get_secret(env_var_name)
    if secret_value is not None:
        return secret_value
        
    # Fall back to default value
    if default_value is not None:
        return default_value

    if allow_empty:
        return None

    raise EnvironmentError(f"Configuration value for {env_var_name} not found and no default value provided")

# Time zone for proper time comparison
TIMEZONE = pytz.timezone("Europe/Sofia")  # Adjust to your local timezone
IBEX_TIMEZONE = pytz.timezone("Europe/Budapest")

# FusionSolar credentials
FUSIONSOLAR_USERNAME = get_config_value("FUSIONSOLAR_USERNAME")
FUSIONSOLAR_PASSWORD = get_config_value("FUSIONSOLAR_PASSWORD")

# Price threshold in the appropriate currency (e.g., EUR/MWh)
PRICE_THRESHOLD = float(get_config_value("PRICE_THRESHOLD", "15.04"))

# Power settings (in kW)
LOW_POWER_SETTING = get_config_value("LOW_POWER_SETTING", "5.000") # Power limit when prices are high
HIGH_POWER_SETTING = get_config_value("HIGH_POWER_SETTING", "no limit")   # Power limit when prices are low

# Telegram configuration constants
TELEGRAM_BOT_TOKEN = get_config_value("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_config_value("TELEGRAM_CHAT_ID")

# Default directory for storing screenshots
SCREENSHOT_DIR = get_config_value("FUSIONSOLAR_SCREENSHOT_DIR", "/tmp/fusionsolar_management/screenshots")

# Directory for storing price history
LOCAL_STORAGE_DIR = get_config_value("FUSIONSOLAR_PRICE_STORAGE_DIR", "/tmp/fusionsolar_management/prices") 

# Storage configuration
# Options: "local" or "s3"
STORAGE_TYPE = get_config_value("FUSIONSOLAR_STORAGE_TYPE", "local")

# S3 configuration (only used if STORAGE_TYPE is "s3")
S3_BUCKET_NAME = get_config_value("FUSIONSOLAR_S3_BUCKET_NAME", "fusionsolar-management")
S3_REGION = get_config_value("FUSIONSOLAR_S3_REGION", "eu-central-1")
S3_ACCESS_KEY_ID = get_config_value("FUSIONSOLAR_S3_ACCESS_KEY_ID", allow_empty=True)
S3_SECRET_ACCESS_KEY = get_config_value("FUSIONSOLAR_S3_SECRET_ACCESS_KEY", allow_empty=True)

# Location configuration for sunrise/sunset calculations
LOCATION_LATITUDE = float(get_config_value("FUSIONSOLAR_LOCATION_LATITUDE", "42.6420"))  # Karlovo, Bulgaria
LOCATION_LONGITUDE = float(get_config_value("FUSIONSOLAR_LOCATION_LONGITUDE", "24.8083"))  # Karlovo, Bulgaria
LOCATION_NAME = get_config_value("FUSIONSOLAR_LOCATION_NAME", "Karlovo")
LOCATION_COUNTRY = get_config_value("FUSIONSOLAR_LOCATION_COUNTRY", "Bulgaria")
