"""Tests for get_user_headers.py"""
# pylint: disable=protected-access

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import datetime, math, os, random, shutil, sqlite3, tempfile, unittest

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

    # TODO: Stop just guessing at the proper values for these thresholds
    min_val, max_val = (base_delay * 0.25), (base_delay * 0.5)
    assert min_val <= stddev <= max_val, (
        "not({} <= {} >= {})".format(min_val, stddev, max_val))

def check_timestamp_roundtrip(timestamp):
    """Code shared between timestamp round-tripping tests"""
    dtime = datetime.datetime.fromtimestamp(timestamp)
    tstamp = get_user_headers._timestamp(dtime)
    dtime_new = datetime.datetime.fromtimestamp(tstamp)
    assert tstamp == timestamp, '{} != {}'.format(tstamp, timestamp)
    assert dtime_new == dtime, '{} != {}'.format(dtime_new, dtime)

def test_default_randomize_delay():
    """randomize_delay(): 1 <= randomize_delay() <= 1.5"""
    results = [get_user_headers.randomize_delay() for _ in range(0, 10000)]
    check_randomize_delay(get_user_headers.DEFAULT_BASE_DELAY, results)

def test_nondefault_randomize_delay():
    """randomize_delay: 2.5 <= randomize_delay(5) <= 7.5"""
    base = 5
    results = [get_user_headers.randomize_delay(base) for _ in range(0, 10000)]
    check_randomize_delay(base, results)

def test_randomize_delay_distrib():
    """randomize_delay: Standard deviation is acceptable

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

def test_timestamp_epoch():
    """_timestamp(): round-trips correctly at the epoch"""
    check_timestamp_roundtrip(0)

def test_timestamp_recent():
    """_timestamp(): round-trips correctly at a typical time"""
    check_timestamp_roundtrip(1468673923)

class UserHeaderGetterTests(unittest.TestCase):
    """Tests for UserHeaderGetter"""
    test_data = {
        'Foo': 'Bar',
        'baz': 'quux',
        'SPAM': 'EGGS',
    }

    test_headers = {x: 'foo{}'.format(random.random()) for x in
                    list(get_user_headers.UserHeaderGetter.safe_headers) +
                    list(get_user_headers.UserHeaderGetter.unsafe_headers) +
                    ['X-Testing-{}'.format(random.random())]}
    test_headers.update({x.lower(): y for x, y in test_headers.items()})
    test_headers.update({x.upper(): y for x, y in test_headers.items()})
    test_headers.update({x.title(): y for x, y in test_headers.items()})

    def setUp(self):
        """Initialize test space on filesystem"""
        self.tempdir = tempfile.mkdtemp(prefix='nosetests-')
        self.getter = get_user_headers.UserHeaderGetter(self.tempdir)

    def tearDown(self):
        """Remove test space on filesystem"""
        self.getter.cache_conn.close()
        shutil.rmtree(self.tempdir)

    # TODO: Tests still to be written:
    # - __init__(path=None)
    # - get_all(headers=None)
    # - get_safe(headers=None)
    # - All uses of the skip_cache attribute

    def test_access_denied(self):
        """UserHeaderGetter: 'access denied' in __init__"""

        nonexist = '/w409vrporpe'
        self.assertFalse(os.path.exists(nonexist))

        readonly = 'C:\\' if os.name == 'nt' else '/'
        self.assertTrue(os.path.exists(readonly))

        # os.makedirs failure
        self.assertRaises(get_user_headers.OS_ERROR,
                          get_user_headers.UserHeaderGetter, nonexist)

        # sqlite3.connect failure
        self.assertRaises(sqlite3.OperationalError,
                          get_user_headers.UserHeaderGetter, readonly)

    def test_clear_expired(self):
        """UserHeaderGetter: clear_expired() functions properly"""
        self.assertIsNone(self.getter._get_cache())
        self.getter._save_cache(self.test_data.copy())

        self.getter.clear_expired()
        self.assertEqual(self.getter._get_cache(), self.test_data,
                         "Shouldn't expire freshly-added entries")

        # XXX: Do I want a less "DIY hack"-ish solution here?
        real_dt = datetime.datetime
        try:
            class MockDateTime(real_dt):
                """Helper to mock datetime.datetime.now() for testing"""
                @classmethod
                def now(cls, tz=None):  # pylint: disable=invalid-name
                    """Mock for datetime.datetime.now()"""
                    return real_dt.now(tz) + (
                        self.getter.cache_timeout +
                        datetime.timedelta(seconds=1))

            datetime.datetime = MockDateTime
            self.getter.clear_expired()
        finally:
            datetime.datetime = real_dt

        self.assertFalse(self.getter._get_cache(),
                         "Failed to remove stale entries")

    def test_get_all_as_filter(self):
        """UserHeaderGetter: get_all() properly filters input"""
        results = self.getter.get_all(self.test_headers.copy())
        unwanted = [x.lower() for x in self.getter.unsafe_headers]

        for key in results.keys():
            self.assertNotIn(key.lower(), unwanted,
                "Unsafe headers in get_all() output")

        # Verify the filtering process didn't modify the key=value pairs
        for key, value in results.items():
            self.assertEqual(value, self.test_headers.get(key,
                                                          random.random()))

    def test_get_safe_as_filter(self):
        """UserHeaderGetter: get_safe() properly filters input"""
        results = self.getter.get_safe(self.test_headers.copy())
        wanted = [x.lower() for x in self.getter.safe_headers]

        for key in results.keys():
            self.assertIn(key.lower(), wanted,
                "Unknown header in get_safe() output: {}".format(key))

        # Verify the filtering process didn't modify the key=value pairs
        for key, value in results.items():
            self.assertEqual(value, self.test_headers.get(key,
                                                          random.random()))

    def test_parent_dir_exists(self):
        """UserHeaderGetter: cache directory already exists"""
        get_user_headers.UserHeaderGetter(self.tempdir)

    def test_storage(self):
        """UserHeaderGetter: basic functionality of SQLite-wrapping calls"""
        self.assertIsNone(self.getter._get_cache())

        stored = self.test_data.copy()
        self.getter._save_cache(stored)
        self.assertEqual(stored, self.test_data)

        retrieved = self.getter._get_cache()
        self.assertEqual(retrieved, stored)

        retrieved_again = self.getter._get_cache()
        self.assertEqual(retrieved_again, retrieved)

        self.assertEqual(retrieved_again, self.test_data,
                        "Error introduced somewhere in round-tripping")
