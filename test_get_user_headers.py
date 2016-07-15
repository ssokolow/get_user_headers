"""Tests for get_user_headers.py"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import math

import get_user_headers

def check_randomize_delay(base_delay, results):
    """Code shared between default and nondefault randomize_delay tests."""
    assert min(results) >= base_delay * 0.5
    assert max(results) <= base_delay * 1.5

def check_randomize_stddev(base_delay, results):
    """Code shared between default and non-default std. deviation tests."""
    mean = sum(results) / len(results)
    variance = sum((x - mean) ** 2 for x in results) / len(results)
    stddev = math.sqrt(variance)

    assert (base_delay * 0.25) <= stddev <= (base_delay * 0.3), stddev

def test_default_randomize_delay():
    """1 <= randomize_delay() <= 1.5"""
    results = [get_user_headers.randomize_delay() for _ in range(0, 10000)]
    check_randomize_delay(2, results)

def test_nondefault_randomize_delay():
    """2.5 <= randomize_delay(5) <= 7.5"""
    base = 5
    results = [get_user_headers.randomize_delay(base) for _ in range(0, 10000)]
    check_randomize_delay(base, results)

def test_randomize_delay_distrib():
    """The standard deviation of randomize_delay is sufficiently high

    NOTE: This will need to be changed when I change the distribution of the
          random numbers to better simulate real human behaviour.

          (This is really just a poor proxy for doing proper statistical
          analysis on the function's output.)"""
    results = [get_user_headers.randomize_delay() for _ in range(0, 10000)]
    check_randomize_stddev(2, results)
    results = [get_user_headers.randomize_delay(5) for _ in range(0, 10000)]
    check_randomize_stddev(5, results)

# TODO: How difficult would it be to have a testcase which statistically
#       analyzes the generated delays for similarity to test data collected
#       from actual human activity?
