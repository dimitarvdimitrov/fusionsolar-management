#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Power Decision Maker Module

This module provides a centralized class for deciding whether power should be
high or low based on hourly average electricity prices.
"""

import datetime
import logging
from price_analyzer import PriceData

# Configure logging
logger = logging.getLogger(__name__)


class PowerDecisionMaker:
	"""
	Class responsible for deciding power settings based on hourly average prices.
	"""

	def __init__(self, price_data: PriceData, price_threshold: float, low_power_setting: str, high_power_setting: str):
		"""
		Initialize the PowerDecisionMaker.

		Args:
			price_data (PriceData): The price data to use for decisions
			price_threshold (float): The price threshold below which power should be low
			low_power_setting (str): The power setting to use when prices are below threshold
			high_power_setting (str): The power setting to use when prices are above threshold
		"""
		self.price_data = price_data
		self.price_threshold = price_threshold
		self.low_power_setting = low_power_setting
		self.high_power_setting = high_power_setting

	def should_use_low_power(self, target_time: datetime.datetime) -> bool:
		"""
		Determine if low power should be used at the given time based on hourly average.

		Args:
			target_time (datetime.datetime): The time to check

		Returns:
			bool: True if low power should be used, False otherwise

		Raises:
			ValueError: If no price data is available for the target hour
		"""
		try:
			hourly_avg = self.price_data.get_hourly_average(target_time)
			return hourly_avg < self.price_threshold
		except ValueError as e:
			logger.error(f"Error getting hourly average for {target_time}: {e}")
			raise

	def get_power_setting(self, target_time: datetime.datetime) -> str:
		"""
		Get the power setting to use at the given time based on hourly average.

		Args:
			target_time (datetime.datetime): The time to check

		Returns:
			str: The power setting to use (low_power_setting or high_power_setting)

		Raises:
			ValueError: If no price data is available for the target hour
		"""
		if self.should_use_low_power(target_time):
			hourly_avg = self.price_data.get_hourly_average(target_time)
			logger.info(f"Hourly average price ({hourly_avg:.2f}) is below threshold ({self.price_threshold:.2f}), using low power: {self.low_power_setting}")
			return self.low_power_setting
		else:
			hourly_avg = self.price_data.get_hourly_average(target_time)
			logger.info(f"Hourly average price ({hourly_avg:.2f}) is above threshold ({self.price_threshold:.2f}), using high power: {self.high_power_setting}")
			return self.high_power_setting

	def get_hourly_average(self, target_time: datetime.datetime) -> float:
		"""
		Get the hourly average price for the given time.

		Args:
			target_time (datetime.datetime): The time to check

		Returns:
			float: The hourly average price

		Raises:
			ValueError: If no price data is available for the target hour
		"""
		return self.price_data.get_hourly_average(target_time)
