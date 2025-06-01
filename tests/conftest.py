#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures

This file automatically applies to all tests in the tests/ directory.
It sets up the environment to avoid configuration dependencies.
"""

import os

# Set minimal environment variables needed for tests
# Only the ones without defaults in config.py are required
os.environ.update({
    'FUSIONSOLAR_USERNAME': 'test_user',
    'FUSIONSOLAR_PASSWORD': 'test_pass',
    'TELEGRAM_BOT_TOKEN': 'test_token',
    'TELEGRAM_CHAT_ID': 'test_chat'
})
