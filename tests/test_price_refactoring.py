#!/usr/bin/env python3
"""
Tests for the price fetching refactoring.

These tests verify:
1. PriceData.__eq__() correctly compares price data
2. PriceRepository.scrape_prices() and persist_prices() work correctly
3. Scheduler.fetch_next_day_prices() detects and notifies on price changes
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytz

from price_analyzer import PriceData, PriceEntry


class TestPriceDataEquality:
    """Test suite for PriceData.__eq__() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tz = pytz.timezone('Europe/Sofia')
        self.fetch_time = self.tz.localize(datetime(2025, 1, 25, 14, 0))

    def test_equal_price_data_same_entries(self):
        """Two PriceData objects with identical entries should be equal."""
        entries = [
            PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 0, 0)), price=50.0),
            PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 1, 0)), price=45.0),
        ]
        pd1 = PriceData(entries=entries.copy(), fetch_time=self.fetch_time)
        pd2 = PriceData(entries=entries.copy(), fetch_time=self.fetch_time)

        assert pd1 == pd2

    def test_equal_price_data_different_fetch_times(self):
        """PriceData should be equal even if fetch_time differs."""
        entries = [
            PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 0, 0)), price=50.0),
        ]
        fetch_time1 = self.tz.localize(datetime(2025, 1, 25, 10, 0))
        fetch_time2 = self.tz.localize(datetime(2025, 1, 25, 14, 0))

        pd1 = PriceData(entries=entries.copy(), fetch_time=fetch_time1)
        pd2 = PriceData(entries=entries.copy(), fetch_time=fetch_time2)

        assert pd1 == pd2

    def test_not_equal_different_prices(self):
        """PriceData with different prices should not be equal."""
        time = self.tz.localize(datetime(2025, 1, 25, 0, 0))

        pd1 = PriceData(
            entries=[PriceEntry(time=time, price=50.0)],
            fetch_time=self.fetch_time
        )
        pd2 = PriceData(
            entries=[PriceEntry(time=time, price=0.0)],  # Different price (zero).
            fetch_time=self.fetch_time
        )

        assert pd1 != pd2

    def test_not_equal_different_times(self):
        """PriceData with different entry times should not be equal."""
        pd1 = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 0, 0)), price=50.0)],
            fetch_time=self.fetch_time
        )
        pd2 = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 1, 0)), price=50.0)],
            fetch_time=self.fetch_time
        )

        assert pd1 != pd2

    def test_not_equal_different_entry_count(self):
        """PriceData with different number of entries should not be equal."""
        time = self.tz.localize(datetime(2025, 1, 25, 0, 0))

        pd1 = PriceData(
            entries=[PriceEntry(time=time, price=50.0)],
            fetch_time=self.fetch_time
        )
        pd2 = PriceData(
            entries=[
                PriceEntry(time=time, price=50.0),
                PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 1, 0)), price=45.0),
            ],
            fetch_time=self.fetch_time
        )

        assert pd1 != pd2

    def test_not_equal_to_non_price_data(self):
        """PriceData should return NotImplemented when compared to other types."""
        pd = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 0, 0)), price=50.0)],
            fetch_time=self.fetch_time
        )

        assert pd.__eq__("not a PriceData") is NotImplemented
        assert pd.__eq__(None) is NotImplemented
        assert pd.__eq__(42) is NotImplemented

    def test_equal_empty_entries(self):
        """Two PriceData objects with no entries should be equal."""
        pd1 = PriceData(entries=[], fetch_time=self.fetch_time)
        pd2 = PriceData(entries=[], fetch_time=self.fetch_time)

        assert pd1 == pd2

    def test_zero_prices_detected_as_different(self):
        """This is the key use case: zeros replaced by real values should be detected."""
        time = self.tz.localize(datetime(2025, 1, 25, 0, 0))

        # Old data with zeros (incomplete IBEX data).
        old_data = PriceData(
            entries=[
                PriceEntry(time=time, price=0.0),
                PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 1, 0)), price=0.0),
            ],
            fetch_time=self.fetch_time
        )

        # New data with real prices.
        new_data = PriceData(
            entries=[
                PriceEntry(time=time, price=52.3),
                PriceEntry(time=self.tz.localize(datetime(2025, 1, 25, 1, 0)), price=48.7),
            ],
            fetch_time=self.fetch_time
        )

        assert old_data != new_data


class TestPriceRepositoryMethods:
    """Test suite for PriceRepository.scrape_prices() and persist_prices()."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tz = pytz.timezone('Europe/Sofia')

    @patch('price_repository.PriceRepository._fetch_online_data')
    @patch('price_repository.PriceRepository._parse_price_table')
    def test_scrape_prices_returns_price_data(self, mock_parse, mock_fetch):
        """scrape_prices() should fetch and parse without storage interaction."""
        from price_repository import PriceRepository
        from storage_interface import LocalFileStorage

        # Set up mocks.
        mock_fetch.return_value = '[{"date": "2025-01-26 00:00:00", "price": "50.0"}]'
        mock_price_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 26, 0, 0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )
        mock_parse.return_value = mock_price_data

        # Create repository with a mock storage.
        mock_storage = Mock(spec=LocalFileStorage)
        repo = PriceRepository(mock_storage)

        # Call scrape_prices.
        result = repo.scrape_prices()

        # Verify behavior.
        mock_fetch.assert_called_once()
        mock_parse.assert_called_once()
        assert result == mock_price_data
        # Storage should NOT be called.
        mock_storage.read_text.assert_not_called()
        mock_storage.write_text.assert_not_called()

    def test_persist_prices_writes_to_storage(self):
        """persist_prices() should write price data to storage."""
        from price_repository import PriceRepository
        from storage_interface import LocalFileStorage

        # Create mock storage.
        mock_storage = Mock(spec=LocalFileStorage)
        mock_storage.write_text.return_value = True

        repo = PriceRepository(mock_storage)

        # Create price data to persist.
        price_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 26, 0, 0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )

        # Call persist_prices.
        repo.persist_prices(price_data)

        # Verify storage was called with correct filename.
        mock_storage.write_text.assert_called_once()
        call_args = mock_storage.write_text.call_args
        filename = call_args[0][0]
        assert filename == "prices/parsed/ibex.bg-2025-01-26.json"

    def test_persist_prices_raises_on_failure(self):
        """persist_prices() should raise exception if storage fails."""
        from price_repository import PriceRepository
        from storage_interface import LocalFileStorage

        # Create mock storage that fails.
        mock_storage = Mock(spec=LocalFileStorage)
        mock_storage.write_text.return_value = False

        repo = PriceRepository(mock_storage)

        price_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 26, 0, 0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )

        with pytest.raises(Exception, match="Failed to write price data"):
            repo.persist_prices(price_data)

    def test_get_prices_for_date_returns_none_when_not_found(self):
        """get_prices_for_date() should return None when no stored data exists."""
        from price_repository import PriceRepository
        from storage_interface import LocalFileStorage

        mock_storage = Mock(spec=LocalFileStorage)
        mock_storage.read_text.return_value = None

        repo = PriceRepository(mock_storage)

        result = repo.get_prices_for_date(datetime(2025, 1, 26))

        assert result is None


class TestSchedulerPriceMismatchDetection:
    """Test suite for Scheduler.fetch_next_day_prices() mismatch detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tz = pytz.timezone('Europe/Sofia')

    @patch('scheduler.TelegramNotifier')
    @patch('scheduler.PriceRepository')
    @patch('scheduler.create_storage')
    def test_sends_update_notification_on_price_change(
        self, mock_create_storage, mock_repo_class, mock_notifier_class
    ):
        """Should send update notification when prices change."""
        from scheduler import Scheduler

        # Set up mocks.
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        tomorrow = datetime.now() + timedelta(days=1)

        # Old stored data with zeros.
        old_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(datetime(2025, 1, 26, 0, 0)), price=0.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 10, 0))
        )

        # New scraped data with real prices.
        new_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )

        mock_repo.scrape_prices.return_value = new_data
        mock_repo.get_prices_for_date.return_value = old_data

        scheduler = Scheduler()
        result = scheduler.fetch_next_day_prices()

        # Verify notification was sent with update message format.
        assert result is True
        mock_notifier.send_message.assert_called_once()
        call_args = mock_notifier.send_message.call_args[0][0]
        assert "Обновени цени" in call_args  # Bulgarian for "Updated prices".

        # Verify prices were persisted.
        mock_repo.persist_prices.assert_called_once_with(new_data)

    @patch('scheduler.TelegramNotifier')
    @patch('scheduler.PriceRepository')
    @patch('scheduler.create_storage')
    def test_sends_initial_notification_on_first_fetch(
        self, mock_create_storage, mock_repo_class, mock_notifier_class
    ):
        """Should send initial notification when no stored data exists."""
        from scheduler import Scheduler

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        tomorrow = datetime.now() + timedelta(days=1)

        new_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )

        mock_repo.scrape_prices.return_value = new_data
        mock_repo.get_prices_for_date.return_value = None  # No stored data.

        scheduler = Scheduler()
        result = scheduler.fetch_next_day_prices()

        assert result is True
        mock_notifier.send_message.assert_called_once()
        call_args = mock_notifier.send_message.call_args[0][0]
        assert "Успешно изтеглени цени" in call_args  # "Successfully fetched prices".

    @patch('scheduler.TelegramNotifier')
    @patch('scheduler.PriceRepository')
    @patch('scheduler.create_storage')
    def test_no_notification_when_prices_unchanged(
        self, mock_create_storage, mock_repo_class, mock_notifier_class
    ):
        """Should not send notification when prices are unchanged."""
        from scheduler import Scheduler

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        tomorrow = datetime.now() + timedelta(days=1)

        # Same data for both stored and scraped.
        price_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )

        mock_repo.scrape_prices.return_value = price_data
        mock_repo.get_prices_for_date.return_value = price_data

        scheduler = Scheduler()
        result = scheduler.fetch_next_day_prices()

        assert result is True
        mock_notifier.send_message.assert_not_called()

        # Still should persist (overwrite with same data is fine).
        mock_repo.persist_prices.assert_called_once()

    @patch('scheduler.TelegramNotifier')
    @patch('scheduler.PriceRepository')
    @patch('scheduler.create_storage')
    def test_handles_wrong_date_scraped_data(
        self, mock_create_storage, mock_repo_class, mock_notifier_class
    ):
        """Should return False when scraped data is for wrong date (IBEX not published yet)."""
        from scheduler import Scheduler

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        # Scraped data is for today, not tomorrow.
        today = datetime.now()
        today_data = PriceData(
            entries=[PriceEntry(time=self.tz.localize(today.replace(hour=0, minute=0, second=0, microsecond=0)), price=50.0)],
            fetch_time=self.tz.localize(datetime(2025, 1, 25, 14, 0))
        )

        mock_repo.scrape_prices.return_value = today_data

        scheduler = Scheduler()
        result = scheduler.fetch_next_day_prices()

        assert result is False
        # No persist should happen for wrong date.
        mock_repo.persist_prices.assert_not_called()
