#!/usr/bin/env python3
"""
Tests for Lambda event detection (scheduled vs manual trigger).

These tests verify that is_scheduled_event() correctly distinguishes between
CloudWatch Events / EventBridge Scheduler invocations and manual triggers.
"""

from price_analyzer_lambda import is_scheduled_event


class TestIsScheduledEvent:
    """Test is_scheduled_event helper function."""

    def test_cloudwatch_events_scheduled(self):
        """CloudWatch Events scheduled event is detected."""
        event = {
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "id": "abc123",
            "resources": ["arn:aws:events:..."],
            "detail": {}
        }
        assert is_scheduled_event(event) is True

    def test_eventbridge_scheduler(self):
        """EventBridge Scheduler event is detected."""
        event = {
            "detail-type": "Scheduled Event",
            "source": "aws.scheduler",
        }
        assert is_scheduled_event(event) is True

    def test_empty_event_is_manual(self):
        """Empty event (manual invoke) is not scheduled."""
        assert is_scheduled_event({}) is False

    def test_custom_payload_is_manual(self):
        """Custom payload without scheduled fields is manual."""
        event = {"custom": "data", "test": True}
        assert is_scheduled_event(event) is False

    def test_none_event_is_manual(self):
        """None event is not scheduled."""
        assert is_scheduled_event(None) is False

    def test_wrong_detail_type(self):
        """Event with different detail-type is not scheduled."""
        event = {
            "detail-type": "Custom Event",
            "source": "aws.events",
        }
        assert is_scheduled_event(event) is False

    def test_wrong_source(self):
        """Event with different source is not scheduled."""
        event = {
            "detail-type": "Scheduled Event",
            "source": "custom.source",
        }
        assert is_scheduled_event(event) is False
