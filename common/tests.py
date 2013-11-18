"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import SimpleTestCase
from datetime import datetime
from common.utilities import weekOfMonth, lastWeekOfMonth


class datetimeUtilitiesTest(SimpleTestCase):
	def test_week_of_month(self):
		testtime = datetime(year=2013, month=11, day=17)
		# 11/17/2013 is the third Sunday of the month
		self.assertEqual(weekOfMonth(testtime), 3)
		testtime = datetime(year=2013, month=1, day=1)
		self.assertEqual(weekOfMonth(testtime), 1)
		testtime = datetime(year=2013, month=1, day=31)
		self.assertEqual(weekOfMonth(testtime), 5)
		testtime = datetime(year=2013, month=2, day=28)
		self.assertEqual(weekOfMonth(testtime), 4)
	def test_last_week_of_month(self):
		testtime = datetime(year=2013, month=11, day=17)
		self.assertFalse(lastWeekOfMonth(testtime)) # 11/17/2013 is the third Sunday of the month
		testtime = datetime(year=2013, month=1, day=1)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=1, day=21)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=2, day=21)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=5, day=24)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=2, day=22)
		self.assertTrue(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=2, day=28)
		self.assertTrue(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=5, day=31)
		self.assertTrue(lastWeekOfMonth(testtime))
