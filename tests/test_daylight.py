#!/usr/bin/env python3
"""
Tests for daylight calculation functions

These tests verify that sunrise/sunset calculations work correctly
for the configured location (Karlovo, Bulgaria).
"""

import pytest
from datetime import datetime
import pytz

# Import from the actual module now that circular import is fixed
from price_analyzer import is_daylight_with_times


class TestDaylightCalculations:
    """Test suite for daylight calculation functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tz = pytz.timezone('Europe/Sofia')
        # Test date: January 25, 2025 (winter)
        self.test_date = datetime(2025, 1, 25)
        
    def test_morning_is_daylight(self):
        """Test that morning time (8:00) is correctly identified as daylight."""
        morning_time = self.tz.localize(self.test_date.replace(hour=8, minute=0))
        result = is_daylight_with_times(morning_time)
        
        assert result['is_daylight'] is True
        assert isinstance(result['sunrise'], datetime)
        assert isinstance(result['sunset'], datetime)
        
    def test_noon_is_daylight(self):
        """Test that noon (12:00) is correctly identified as daylight."""
        noon_time = self.tz.localize(self.test_date.replace(hour=12, minute=0))
        result = is_daylight_with_times(noon_time)
        
        assert result['is_daylight'] is True
        
    def test_evening_is_not_daylight(self):
        """Test that evening time (18:00) is correctly identified as nighttime."""
        evening_time = self.tz.localize(self.test_date.replace(hour=18, minute=0))
        result = is_daylight_with_times(evening_time)
        
        assert result['is_daylight'] is False
        
    def test_night_is_not_daylight(self):
        """Test that night time (22:00) is correctly identified as nighttime."""
        night_time = self.tz.localize(self.test_date.replace(hour=22, minute=0))
        result = is_daylight_with_times(night_time)
        
        assert result['is_daylight'] is False
        
    def test_sunrise_sunset_order(self):
        """Test that sunrise is before sunset."""
        test_time = self.tz.localize(self.test_date.replace(hour=12, minute=0))
        result = is_daylight_with_times(test_time)
        
        assert result['sunrise'] < result['sunset']
        
    def test_sunrise_sunset_timezone_aware(self):
        """Test that sunrise and sunset times are timezone-aware."""
        test_time = self.tz.localize(self.test_date.replace(hour=12, minute=0))
        result = is_daylight_with_times(test_time)
        
        assert result['sunrise'].tzinfo is not None
        assert result['sunset'].tzinfo is not None
        
    def test_daylight_boolean_extraction(self):
        """Test extracting just the boolean daylight result."""
        morning_time = self.tz.localize(self.test_date.replace(hour=8, minute=0))
        night_time = self.tz.localize(self.test_date.replace(hour=22, minute=0))
        
        assert is_daylight_with_times(morning_time)['is_daylight'] is True
        assert is_daylight_with_times(night_time)['is_daylight'] is False
        
    def test_winter_vs_summer_daylight_hours(self):
        """Test that winter has shorter daylight hours than summer."""
        # Winter test (January)
        winter_time = self.tz.localize(datetime(2025, 1, 25, 12, 0))
        winter_result = is_daylight_with_times(winter_time)
        winter_daylight_duration = (winter_result['sunset'] - winter_result['sunrise']).total_seconds()
        
        # Summer test (July)
        summer_time = self.tz.localize(datetime(2025, 7, 25, 12, 0))
        summer_result = is_daylight_with_times(summer_time)
        summer_daylight_duration = (summer_result['sunset'] - summer_result['sunrise']).total_seconds()
        
        assert winter_daylight_duration < summer_daylight_duration
        
    def test_edge_case_exactly_sunrise(self):
        """Test behavior exactly at sunrise time."""
        test_time = self.tz.localize(self.test_date.replace(hour=12, minute=0))
        result = is_daylight_with_times(test_time)
        
        # Test exactly at sunrise
        sunrise_time = result['sunrise']
        sunrise_result = is_daylight_with_times(sunrise_time)
        
        assert sunrise_result['is_daylight'] is True
        
    def test_edge_case_exactly_sunset(self):
        """Test behavior exactly at sunset time."""
        test_time = self.tz.localize(self.test_date.replace(hour=12, minute=0))
        result = is_daylight_with_times(test_time)
        
        # Test exactly at sunset
        sunset_time = result['sunset']
        sunset_result = is_daylight_with_times(sunset_time)
        
        assert sunset_result['is_daylight'] is True


if __name__ == "__main__":
    # Allow running the test file directly
    pytest.main([__file__, "-v"])
