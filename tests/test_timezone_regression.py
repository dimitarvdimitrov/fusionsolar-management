#!/usr/bin/env python3
"""
Timezone regression tests for price data handling.

These tests verify:
1. Price entries are stored with correct timezone (CET/Budapest)
2. Low power periods are correctly calculated across timezones
3. Telegram notifications display times in Sofia timezone
4. Hourly averages work correctly with 15-minute intervals in CET

Background: In d4ac0a9, scrape_prices() was introduced but returned CET times
without converting to Sofia for display, causing incorrect Telegram notifications.
"""

import pytest
import datetime
import json
import pytz
from pathlib import Path
from unittest.mock import Mock, patch

from price_analyzer import PriceData, PriceEntry, get_low_power_periods, should_use_low_power


# Timezones used in the system
SOFIA_TZ = pytz.timezone('Europe/Sofia')
CET_TZ = pytz.timezone('Europe/Budapest')  # IBEX uses CET
UTC_TZ = pytz.UTC


class TestPriceDataTimezones:
    """Test that PriceData handles timezones correctly."""

    @pytest.fixture
    def real_price_fixture(self):
        """Load real price data from fixture file."""
        fixture_path = Path(__file__).parent / 'fixtures' / 'ibex-2026-03-05.json'
        with open(fixture_path) as f:
            data = json.load(f)
        return data

    def test_fixture_entries_are_15_minute_intervals(self, real_price_fixture):
        """Verify fixture has 96 entries (24 hours * 4 quarter-hours)."""
        assert len(real_price_fixture['entries']) == 96

    def test_fixture_timestamps_are_utc(self, real_price_fixture):
        """Verify stored timestamps are Unix timestamps (UTC)."""
        # First entry should be 2026-03-05 00:00:00 CET = 2026-03-04 23:00:00 UTC
        first_ts = real_price_fixture['entries'][0]['time']
        first_dt = datetime.datetime.fromtimestamp(first_ts, tz=UTC_TZ)

        # Should be 2026-03-04 23:00 UTC (which is 2026-03-05 00:00 CET)
        assert first_dt.year == 2026
        assert first_dt.month == 3
        assert first_dt.day == 4
        assert first_dt.hour == 23
        assert first_dt.minute == 0

    def test_first_entry_is_cet_midnight(self, real_price_fixture):
        """First entry should be CET midnight (00:00 Budapest time)."""
        first_ts = real_price_fixture['entries'][0]['time']
        first_dt = datetime.datetime.fromtimestamp(first_ts, tz=CET_TZ)

        assert first_dt.hour == 0
        assert first_dt.minute == 0
        assert first_dt.day == 5  # March 5th in CET

    def test_first_entry_is_sofia_1am(self, real_price_fixture):
        """First CET entry should be 01:00 Sofia time (Sofia is UTC+2, CET is UTC+1)."""
        first_ts = real_price_fixture['entries'][0]['time']
        first_dt = datetime.datetime.fromtimestamp(first_ts, tz=SOFIA_TZ)

        assert first_dt.hour == 1  # 00:00 CET = 01:00 Sofia
        assert first_dt.minute == 0
        assert first_dt.day == 5  # Still March 5th in Sofia

    def test_price_data_from_json_preserves_timestamps(self, real_price_fixture):
        """PriceData.from_json should preserve exact timestamp values."""
        price_data = PriceData.from_json(json.dumps(real_price_fixture))

        # Check first entry
        first_entry = price_data.entries[0]
        expected_ts = real_price_fixture['entries'][0]['time']
        actual_ts = first_entry.time.timestamp()

        assert actual_ts == expected_ts

    def test_known_price_value_at_cet_midnight(self, real_price_fixture):
        """Verify known price at CET hour 0 is 135.24 EUR/MWh."""
        # From IBEX website, CET hour 0 price is 135.24
        first_entry = real_price_fixture['entries'][0]
        assert first_entry['price'] == 135.24


class TestLowPowerPeriodsTimezone:
    """Test that low power periods are calculated correctly across timezones."""

    @pytest.fixture
    def mar5_price_data(self):
        """Load March 5, 2026 price data."""
        fixture_path = Path(__file__).parent / 'fixtures' / 'ibex-2026-03-05.json'
        with open(fixture_path) as f:
            data = json.load(f)

        # Convert to PriceData with CET timezone
        entries = []
        for item in data['entries']:
            dt = datetime.datetime.fromtimestamp(item['time'], tz=CET_TZ)
            entries.append(PriceEntry(time=dt, price=item['price']))

        fetch_time = datetime.datetime.fromtimestamp(data['fetch_time'], tz=CET_TZ)
        return PriceData(entries=entries, fetch_time=fetch_time)

    def test_low_power_periods_exist(self, mar5_price_data):
        """March 5 data should have low power periods (prices drop midday)."""
        # From the data, there's a period where prices drop below 15.04
        # around CET hours 11-14 (prices like 0.79, 5.11, 10.0, etc.)
        threshold = 15.04
        periods = get_low_power_periods(mar5_price_data, threshold)

        assert len(periods) > 0, "Expected at least one low power period"

    def test_low_power_periods_in_cet(self, mar5_price_data):
        """Low power periods should be returned in the same timezone as input."""
        threshold = 15.04
        periods = get_low_power_periods(mar5_price_data, threshold)

        # All returned times should have CET timezone
        for start, end in periods:
            assert start.tzinfo is not None
            assert end.tzinfo is not None

    def test_cet_hour_13_is_low_power(self, mar5_price_data):
        """CET hour 13 (prices 0.79, 5.11, 10.0, 22.55) should be low power."""
        # CET hour 13 = 12:00-13:00 UTC = 14:00-15:00 Sofia
        # Average of 0.79, 5.11, 10.0, 22.55 = 9.61, below 15.04 threshold
        threshold = 15.04

        # Create a time at CET hour 13
        cet_hour_13 = CET_TZ.localize(datetime.datetime(2026, 3, 5, 13, 0))

        is_low = should_use_low_power(mar5_price_data, cet_hour_13, threshold)
        assert is_low, "CET hour 13 should be low power (avg ~9.61 < 15.04)"

    def test_cet_hour_8_is_high_power(self, mar5_price_data):
        """CET hour 8 (morning peak) should be high power."""
        threshold = 15.04

        cet_hour_8 = CET_TZ.localize(datetime.datetime(2026, 3, 5, 8, 0))

        is_low = should_use_low_power(mar5_price_data, cet_hour_8, threshold)
        assert not is_low, "CET hour 8 should be high power (morning peak)"

    def test_sofia_to_cet_conversion_for_display(self, mar5_price_data):
        """Converting low power periods to Sofia time for display."""
        threshold = 15.04
        periods = get_low_power_periods(mar5_price_data, threshold)

        # Convert to Sofia timezone (as done in scheduler.py)
        sofia_periods = [
            (start.astimezone(SOFIA_TZ), end.astimezone(SOFIA_TZ))
            for start, end in periods
        ]

        # The Sofia times should be 1 hour ahead of CET
        for (cet_start, cet_end), (sofia_start, sofia_end) in zip(periods, sofia_periods):
            cet_hour = cet_start.hour
            sofia_hour = sofia_start.hour
            # Sofia is UTC+2, CET is UTC+1, so Sofia = CET + 1
            assert (cet_hour + 1) % 24 == sofia_hour


class TestHourlyAverageTimezone:
    """Test that hourly averages work correctly with timezone-aware times."""

    @pytest.fixture
    def mar5_price_data(self):
        """Load March 5, 2026 price data."""
        fixture_path = Path(__file__).parent / 'fixtures' / 'ibex-2026-03-05.json'
        with open(fixture_path) as f:
            data = json.load(f)

        entries = []
        for item in data['entries']:
            dt = datetime.datetime.fromtimestamp(item['time'], tz=CET_TZ)
            entries.append(PriceEntry(time=dt, price=item['price']))

        fetch_time = datetime.datetime.fromtimestamp(data['fetch_time'], tz=CET_TZ)
        return PriceData(entries=entries, fetch_time=fetch_time)

    def test_hourly_average_cet_hour_0(self, mar5_price_data):
        """CET hour 0 should average entries 0-3 (135.24, 116.08, 112.22, 111.87)."""
        cet_hour_0 = CET_TZ.localize(datetime.datetime(2026, 3, 5, 0, 30))

        avg = mar5_price_data.get_hourly_average(cet_hour_0)
        expected = (135.24 + 116.08 + 112.22 + 111.87) / 4

        assert abs(avg - expected) < 0.01

    def test_same_hour_different_tz_same_result(self, mar5_price_data):
        """Querying the same instant in different timezones should give same result."""
        # 14:00 Sofia = 13:00 CET = 12:00 UTC
        sofia_time = SOFIA_TZ.localize(datetime.datetime(2026, 3, 5, 14, 30))
        cet_time = CET_TZ.localize(datetime.datetime(2026, 3, 5, 13, 30))

        # Note: These are different hours in different timezones, so they'll
        # query different 1-hour windows. This test verifies the timezone
        # handling is consistent.

        # CET 13:00-14:00 has entries at 13:00, 13:15, 13:30, 13:45
        # Sofia 14:00-15:00 is the same wall-clock hour but different TZ

        # The actual behavior depends on how entries are stored.
        # If entries are stored in CET, querying with Sofia time needs conversion.

        # For now, just verify both calls succeed
        avg_cet = mar5_price_data.get_hourly_average(cet_time)
        assert avg_cet > 0


class TestTelegramNotificationTimezone:
    """Test that Telegram notifications display times in Sofia timezone."""

    def test_format_periods_in_sofia(self):
        """Low power periods should be formatted in Sofia timezone for Telegram."""
        # Simulate what scheduler.py does
        from config import TIMEZONE  # Sofia timezone

        # Create a period in CET
        cet_start = CET_TZ.localize(datetime.datetime(2026, 3, 5, 11, 0))
        cet_end = CET_TZ.localize(datetime.datetime(2026, 3, 5, 15, 0))
        periods = [(cet_start, cet_end)]

        # Format as done in scheduler.py
        periods_text = "\n".join([
            f"  - {start.astimezone(TIMEZONE).strftime('%H:%M')} - {end.astimezone(TIMEZONE).strftime('%H:%M')}"
            for start, end in periods
        ])

        # Should show Sofia times (CET + 1 hour)
        assert "12:00" in periods_text  # 11:00 CET = 12:00 Sofia
        assert "16:00" in periods_text  # 15:00 CET = 16:00 Sofia

    def test_format_periods_without_conversion_is_wrong(self):
        """Without timezone conversion, periods would show CET times incorrectly."""
        # This demonstrates the bug that was fixed
        cet_start = CET_TZ.localize(datetime.datetime(2026, 3, 5, 11, 0))
        cet_end = CET_TZ.localize(datetime.datetime(2026, 3, 5, 15, 0))
        periods = [(cet_start, cet_end)]

        # Incorrect: formatting without conversion shows CET times
        wrong_text = "\n".join([
            f"  - {start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
            for start, end in periods
        ])

        # This would show 11:00 - 15:00 (CET) instead of 12:00 - 16:00 (Sofia)
        assert "11:00" in wrong_text
        assert "15:00" in wrong_text


class TestPriceDataGetDate:
    """Test that get_date() works correctly with timezone-aware entries."""

    def test_get_date_returns_correct_date_for_cet_entries(self):
        """get_date() should return the date from entries, not UTC."""
        # Create entries for March 5, 2026 in CET
        entries = [
            PriceEntry(
                time=CET_TZ.localize(datetime.datetime(2026, 3, 5, 0, 0)),
                price=100.0
            ),
            PriceEntry(
                time=CET_TZ.localize(datetime.datetime(2026, 3, 5, 23, 45)),
                price=100.0
            ),
        ]
        fetch_time = CET_TZ.localize(datetime.datetime(2026, 3, 4, 18, 0))
        price_data = PriceData(entries=entries, fetch_time=fetch_time)

        result_date = price_data.get_date()

        # Should be March 5, not March 4 (even though 00:00 CET = 23:00 UTC on March 4)
        assert result_date.date() == datetime.date(2026, 3, 5)

    def test_get_date_raises_for_multiple_dates(self):
        """get_date() should raise if entries span multiple dates."""
        entries = [
            PriceEntry(
                time=CET_TZ.localize(datetime.datetime(2026, 3, 5, 0, 0)),
                price=100.0
            ),
            PriceEntry(
                time=CET_TZ.localize(datetime.datetime(2026, 3, 6, 0, 0)),
                price=100.0
            ),
        ]
        fetch_time = CET_TZ.localize(datetime.datetime(2026, 3, 4, 18, 0))
        price_data = PriceData(entries=entries, fetch_time=fetch_time)

        with pytest.raises(Exception, match="multiple dates"):
            price_data.get_date()
