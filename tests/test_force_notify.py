#!/usr/bin/env python3
"""
Tests for force_notify parameter (manual trigger notification behavior).

These tests verify that:
- force_notify=True sends notifications on error regardless of transition timing
- force_notify=False (and default) suppresses notifications when not near an edge
"""

import datetime
import sys
from unittest.mock import patch, MagicMock

import pytest
import pytz


# Create a mock SetPowerError that won't match RuntimeError in isinstance checks.
class MockSetPowerError(Exception):
    """Mock of SetPowerError for testing."""
    def __init__(self, message: str, screenshot=None, stage=None):
        super().__init__(message)
        self.screenshot = screenshot
        self.stage = stage


# Mock the set_power module before it's imported by price_analyzer.
# This avoids the playwright import that would fail in the test environment.
mock_set_power_module = MagicMock()
mock_set_power_module.SetPower = MagicMock()
mock_set_power_module.SetPowerError = MockSetPowerError
sys.modules['set_power'] = mock_set_power_module

from price_analyzer import main, PriceData, PriceEntry


class TestForceNotifyParameter:
    """Tests for the force_notify parameter in main()."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tz = pytz.timezone('Europe/Sofia')
        # Use a fixed time for deterministic tests: 10:00 on a test day.
        self.current_time = self.tz.localize(datetime.datetime(2025, 2, 14, 10, 0, 0))

    def _create_price_data_not_near_edge(self) -> PriceData:
        """
        Create price data where current time is NOT near a transition edge.

        We create uniform high prices all day, so there are no transitions.
        The test time (10:00) will not be near any edge since there are none.
        """
        entries = []
        base_date = self.current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                entries.append(PriceEntry(
                    time=base_date + datetime.timedelta(hours=hour, minutes=minute),
                    price=100.0  # High price, well above any threshold
                ))
        return PriceData(entries=entries, fetch_time=self.current_time)

    @pytest.fixture
    def mock_dependencies(self):
        """Set up mocks for external dependencies used by main()."""
        with patch("price_analyzer.datetime") as mock_dt, \
             patch("price_analyzer.is_daylight_with_times") as mock_daylight, \
             patch("price_analyzer.create_storage") as mock_storage, \
             patch("price_analyzer.fetch_price_data") as mock_fetch, \
             patch("price_analyzer.telegram_notifier") as mock_notifier:

            # Mock datetime.datetime.now() to return our fixed time.
            mock_dt.datetime.now.return_value = self.current_time
            mock_dt.timedelta = datetime.timedelta

            # It's daylight so the analyzer proceeds.
            mock_daylight.return_value = {
                'is_daylight': True,
                'sunrise': self.current_time.replace(hour=6),
                'sunset': self.current_time.replace(hour=20)
            }

            mock_storage.return_value = MagicMock()

            # Reset the mock SetPower for each test.
            mock_set_power_module.SetPower.reset_mock()

            yield {
                'datetime': mock_dt,
                'daylight': mock_daylight,
                'storage': mock_storage,
                'fetch': mock_fetch,
                'set_power_cls': mock_set_power_module.SetPower,
                'notifier': mock_notifier
            }

    def test_force_notify_true_sends_notification_on_error(self, mock_dependencies):
        """When force_notify=True, always send notification on error."""
        price_data = self._create_price_data_not_near_edge()
        mock_dependencies['fetch'].return_value = price_data

        # Make SetPower raise an error when set_power_limit is called.
        mock_set_power = MagicMock()
        mock_set_power.set_power_limit.side_effect = RuntimeError("Browser crashed")
        mock_dependencies['set_power_cls'].return_value = mock_set_power

        result = main(force_notify=True)

        assert result is False
        # Key assertion: notification IS sent despite not being near an edge.
        mock_dependencies['notifier'].send_message.assert_called_once()
        call_args = mock_dependencies['notifier'].send_message.call_args[0][0]
        assert "Browser crashed" in call_args

    def test_force_notify_false_suppresses_notification_when_not_near_edge(self, mock_dependencies):
        """When force_notify=False and not near edge, suppress notification."""
        price_data = self._create_price_data_not_near_edge()
        mock_dependencies['fetch'].return_value = price_data

        # Make SetPower raise an error.
        mock_set_power = MagicMock()
        mock_set_power.set_power_limit.side_effect = RuntimeError("Browser crashed")
        mock_dependencies['set_power_cls'].return_value = mock_set_power

        result = main(force_notify=False)

        assert result is False
        # Key assertion: notification is NOT sent because we're not near an edge.
        mock_dependencies['notifier'].send_message.assert_not_called()
        mock_dependencies['notifier'].send_photo.assert_not_called()

    def test_default_force_notify_is_false(self, mock_dependencies):
        """Calling main() without force_notify defaults to False (suppression enabled)."""
        price_data = self._create_price_data_not_near_edge()
        mock_dependencies['fetch'].return_value = price_data

        # Make SetPower raise an error.
        mock_set_power = MagicMock()
        mock_set_power.set_power_limit.side_effect = RuntimeError("Browser crashed")
        mock_dependencies['set_power_cls'].return_value = mock_set_power

        result = main()  # No force_notify argument - should default to False.

        assert result is False
        # Notification should be suppressed (default behavior matches force_notify=False).
        mock_dependencies['notifier'].send_message.assert_not_called()
        mock_dependencies['notifier'].send_photo.assert_not_called()
