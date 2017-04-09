"""Tests for get_user_headers.py"""
# pylint: disable=protected-access

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import datetime, locale, math, os, platform, random, shutil, socket, sqlite3
import sys, tempfile, threading, unittest

try:
    from unittest.mock import patch, ANY  # pylint: disable=no-name-in-module
except ImportError:  # pragma: no cover
    from mock import patch, ANY

if sys.version_info.major < 3:  # pragma: no cover
    import urllib2
    Request = urllib2.Request
    urlopen = urllib2.urlopen
else:  # pragma: no cover
    import urllib.request  # pylint: disable=no-name-in-module,import-error
    Request = urllib.request.Request   # pylint: disable=no-member,invalid-name
    urlopen = urllib.request.urlopen  # pylint: disable=no-member

import get_user_headers
from get_user_headers import USABLE_PORTS

def assert_mock_call_count(mock_map):
    """Helper to shut Scrutinizer up about complexity in test_get_*"""
    for mock, count in mock_map.items():
        assert mock.call_count == count

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

class MockBrowser(threading.Thread):
    """Fake browser which provides a run() method to replace webbrowser_open"""
    def __init__(self, urls, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self._urls = urls

    def run(self):
        while self._urls:
            request = Request(self._urls.pop(), headers={
                'User-Agent': 'test-agent',
                'X-Testing-123': 'Mock Data',
            })
            urlopen(request).read()

    @classmethod
    def cls_webbrowser_open(cls, url):
        """Wrapper to adapt Thread's API to webbrowser_open mocking"""
        cls([url]).start()

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

class UserHeaderGetterBase(unittest.TestCase):
    """Base class for UserHeaderGetter tests.

    (Because cyclomatic complexity tests and JUnit-style testing disagree)
    """
    test_data = {
        'Foo': 'Bar',
        'baz': 'quux',
        'SPAM': 'EGGS',
    }

    test_headers = {x: 'foo{}'.format(random.random()) for x in
                    list(get_user_headers.UserHeaderGetter.known_headers) +
                    ['X-Testing-{}'.format(random.random())]}
    test_headers.update({x.lower(): y for x, y in test_headers.items()})
    test_headers.update({x.upper(): y for x, y in test_headers.items()})
    test_headers.update({x.title(): y for x, y in test_headers.items()})

    def setUp(self):
        """Initialize test space on filesystem"""
        self.tempdir = tempfile.mkdtemp(prefix='nosetests-')
        self.getter = get_user_headers.UserHeaderGetter(self.tempdir)
        self.random_numbers = [6023, 13724, 1120, 38582, 22531, 23561, 33109]

    def tearDown(self):
        """Remove test space on filesystem"""
        self.getter.cache_conn.close()  # Needed for Windows
        shutil.rmtree(self.tempdir)

    @staticmethod
    def block_n_ports(random_provider, port_count):
        """Helper for test_get_uncached_collision"""
        blockers = []
        for _ in range(port_count):
            sock = socket.socket()
            sock.bind(('0.0.0.0', random_provider(*USABLE_PORTS)))
            blockers.append(sock)

        return blockers

    def check_unmodified_keys(self, results):
        """Shared code between check_get_all() and check_get_safe()"""
        # Verify the filtering process didn't modify the key=value pairs
        for key, value in results.items():
            self.assertEqual(value, self.test_headers.get(key,
                                                          random.random()))

    def check_get_all(self, results):
        """Shared code for get_all() tests"""
        unwanted = [x.lower() for x in self.getter.unsafe_headers]

        for key in results.keys():
            self.assertNotIn(key.lower(), unwanted,
                "Unsafe header in get_all() output: {}".format(key))
        self.check_unmodified_keys(results)

    def check_get_safe(self, results):
        """Shared code for get_safe() tests"""
        wanted = list(sorted(self.getter.safe_headers))

        self.assertEqual(list(sorted(results.keys())), wanted)
        self.check_unmodified_keys(results)

    def check_header_name(self, key, matcher):
        """Helper to check the validity of a header name

        (Used to keep cyclomatic complexity down in test_normalize_header_names
        """
        if key.lower() in matcher:
            self.assertIn(key, self.getter.known_headers)
        elif key.startswith('X-Testing-'):
            self.assertEqual(key, key.title())
        else:  # pragma: no cover
            self.fail("Unrecognized header: {}".format(key))

    def check_header_names_multicase(self, before, matcher):
        """Helper to be called once per locale under test"""
        for oper in ('lower', 'upper', 'title'):
            before = {getattr(x, oper)(): y for x, y in before.items()}
            result = self.getter.normalize_header_names(before)

            for key in result:
                self.check_header_name(key, matcher)

    @staticmethod
    def check_success(results):
        """Common code for checking successful header retrieval"""
        assert results.get('User-Agent') == 'test-agent'
        assert results.get('X-Testing-123') == 'Mock Data'

    def make_predictable_randrange(self):
        """Helper for mocking random.randrange()"""
        random_numbers = self.random_numbers[:]

        def randrange(start, stop, *args, **kwargs):  # pylint: disable=W0613
            """Closure to actually implement the mock"""
            result = random_numbers.pop()
            assert start <= result < stop
            return result

        return randrange

    def prepare_for_header_name_check(self):
        """Common code for test_normalize_header_names*"""
        matcher = [x.lower() for x in self.getter.known_headers]
        before = self.test_headers.copy()

        self.getter.normalize_header_names(before)
        self.assertEqual(before, self.test_headers,
                         "Must not mutate input dict")
        return before, matcher

class UserHeaderGetterTests1(UserHeaderGetterBase):
    """Tests for UserHeaderGetter (part 1)

    (Split to make JUnit-style testing please the cyclomatic complexity check)
    """

    @unittest.skipIf(os.name == 'nt', "Test is broken under Windows XP")
    def test_access_denied(self):
        """UserHeaderGetter: 'access denied' in __init__"""
        readonly = os.path.join(self.tempdir, 'readonly')
        nonexist = os.path.join(readonly, 'nonexistant')

        os.mkdir(readonly)
        os.chmod(readonly, 444)
        try:
            # os.makedirs failure
            self.assertFalse(os.path.exists(nonexist))
            self.assertRaises(get_user_headers.OS_ERROR,
                              get_user_headers.UserHeaderGetter, nonexist)

            # sqlite3.connect failure
            self.assertTrue(os.path.exists(readonly))
            self.assertRaises(sqlite3.OperationalError,
                              get_user_headers.UserHeaderGetter, readonly)
        finally:
            os.chmod(readonly, 777)

    def test_default_path(self):
        """UserHeaderGetter: initialization with default path works properly"""
        test_dir = os.path.join(self.tempdir, 'default')
        os.makedirs(test_dir)

        orig_cache_dir = get_user_headers.CACHE_DIR
        get_user_headers.CACHE_DIR = test_dir

        try:
            getter = get_user_headers.UserHeaderGetter()
            assert getter.cache_path == os.path.join(test_dir, 'cache.sqlite3')
        finally:
            get_user_headers.CACHE_DIR = orig_cache_dir

    def test_clear_expired(self):
        """UserHeaderGetter: clear_expired() functions properly"""
        self.assertIsNone(self.getter._get_cache())
        self.getter._save_cache(self.test_data.copy())

        self.getter.clear_expired()
        self.assertEqual(self.getter._get_cache(), self.test_data,
                         "Shouldn't expire freshly-added entries")

        # XXX: Why can't mock find 'now' on get_user_headers.datetime.datetime?
        real_dt = datetime.datetime
        try:
            class MockDateTime(real_dt):
                """Helper to mock datetime.datetime.now() for testing"""
                @staticmethod
                def now(tz=None):  # pylint: disable=invalid-name
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

    @patch('get_user_headers.UserHeaderGetter.normalize_header_names',
           autospec=True)
    def test_normalize_called(self, normalize):
        """UserHeaderGetter: get_safe/get_all call normalize_header_names()"""
        assert not normalize.called

        self.getter.get_all(self.test_headers.copy())
        assert normalize.call_count == 1
        normalize.reset_mock()

        self.getter.get_safe(self.test_headers.copy())
        assert normalize.call_count == 1

    def test_normalize_header_names(self):
        """UserHeaderGetter: normalize_header_names functions properly"""
        before, matcher = self.prepare_for_header_name_check()
        self.check_header_names_multicase(before, matcher)

    @unittest.skipIf(os.name == 'nt', "Test is broken on AppVeyor")
    @unittest.skipIf(platform.mac_ver()[0], "Test is broken on Travis-CI OSX")
    def test_normalize_header_names_turkish(self):  # pylint: disable=C0103
        """UserHeaderGetter: normalize_header_names is locale-independent"""
        before, matcher = self.prepare_for_header_name_check()

        old_locale = locale.setlocale(locale.LC_ALL)
        try:
            locale.setlocale(locale.LC_ALL, 'tr_TR.utf8')
        except ValueError:  # pragma: no cover
            raise unittest.SkipTest("Running under a Python version with "
                "broken support for calling locale.setlocale() with "
                "'tr_TR.utf8'. This only breaks the unit test though.")
        else:
            self.check_header_names_multicase(before, matcher)
        finally:
            locale.setlocale(locale.LC_ALL, old_locale)

    def test_parent_dir_exists(self):
        """UserHeaderGetter: no exception if cache directory already exists"""
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

    @staticmethod
    @patch('get_user_headers.subprocess.Popen', autospec=True)
    @patch('get_user_headers.webbrowser.open_new_tab', autospec=True)
    def test_webbrowser_open(wb_open, popen):  # pylint: disable=R0201
        """webbrowser_open: Calls appropriate backend for this OS"""
        assert not popen.called
        assert not wb_open.called

        test_url = 'http://www.example.com:1234/'
        get_user_headers.webbrowser_open(test_url)

        if os.name == 'posix' and not platform.mac_ver()[0]:
            assert not wb_open.called
            popen.assert_called_once_with(['xdg-open', test_url],
                                          stdout=ANY, stderr=ANY)
        else:  # pragma: no cover
            wb_open.assert_called_once_with(test_url)
            assert not popen.called

class UserHeaderGetterTests2(UserHeaderGetterBase):
    """Tests for UserHeaderGetter (part 2)

    (Split to make JUnit-style testing please the cyclomatic complexity check)
    """

    @patch('get_user_headers.UserHeaderGetter.clear_expired', autospec=True)
    def test_get_all(self, clear):
        """UserHeaderGetter: get_all() functions properly"""

        with patch(
                'get_user_headers.UserHeaderGetter._get_uncached',
                autospec=True, return_value=self.test_headers.copy()
                    ) as get_uncached, patch(
                'get_user_headers.UserHeaderGetter._get_cache',
                autospec=True, return_value=self.test_headers.copy()
                    ) as get_cache:
            assert_mock_call_count({get_uncached: 0, get_cache: 0, clear: 0})

            results = self.getter.get_all(skip_cache=True)
            assert_mock_call_count({get_uncached: 1, get_cache: 0, clear: 1})

            results = self.getter.get_all()
            assert_mock_call_count({get_uncached: 1, get_cache: 1, clear: 2})

        self.check_get_all(results)

    def test_get_all_as_filter(self):
        """UserHeaderGetter: get_all(headers) properly filters input"""
        self.check_get_all(self.getter.get_all(self.test_headers.copy()))

    def test_get_safe(self):
        """UserHeaderGetter: get_safe() functions properly"""
        with patch(
                'get_user_headers.UserHeaderGetter._get_uncached',
                autospec=True, return_value=self.test_headers.copy()
                    ) as get_uncached, patch(
                'get_user_headers.UserHeaderGetter._get_cache',
                autospec=True, return_value=self.test_headers.copy()
                    ) as get_cache:
            assert_mock_call_count({get_uncached: 0, get_cache: 0})

            results = self.getter.get_safe(skip_cache=True)
            self.check_get_safe(results)
            assert_mock_call_count({get_uncached: 1, get_cache: 0})

            results = self.getter.get_safe()
            self.check_get_safe(results)
            assert_mock_call_count({get_uncached: 1, get_cache: 1})

    def test_get_safe_as_filter(self):
        """UserHeaderGetter: get_safe(headers) properly filters input"""
        self.check_get_safe(self.getter.get_safe(self.test_headers.copy()))

    def test_get_uncached(self):
        """UserHeaderGetter: get_uncached() functions properly"""
        with patch('get_user_headers.webbrowser_open', autospec=True,
                   side_effect=MockBrowser.cls_webbrowser_open):
            self.check_success(self.getter._get_uncached())

    def test_get_uncached_collision(self):
        """UserHeaderGetter: get_uncached() recovers from port collisions"""
        with patch('get_user_headers.random.randrange',
                self.make_predictable_randrange()) as provider:
            with patch('get_user_headers.webbrowser_open', autospec=True,
                       side_effect=MockBrowser.cls_webbrowser_open):

                # Tie up the first few ports randrange() will return
                expect_src = self.make_predictable_randrange()
                try:
                    socks = self.block_n_ports(expect_src, 2)  # NOQA

                    # Throw out the value it'll successfully bind to
                    expect_src(*USABLE_PORTS)

                    self.check_success(self.getter._get_uncached())

                    # Assert it fell back to the port we expected by checking
                    # whether we're in the same place in the "random" sequence
                    assert provider(*USABLE_PORTS) == expect_src(*USABLE_PORTS)
                finally:
                    for sock in socks:
                        sock.close()

    @unittest.skipIf(os.name == 'nt',
                     "Need a different way to trigger an error on Windows")
    def test_get_uncached_port_denied(self):
        """UserHeaderGetter: get_uncached() doesn't swallow non-collisions"""
        with patch('get_user_headers.webbrowser_open', autospec=True,
                   side_effect=MockBrowser.cls_webbrowser_open):
            usable_orig = USABLE_PORTS
            get_user_headers.USABLE_PORTS = (750, 764)  # Unallocated but <1024

            try:
                self.assertRaises(socket.error, self.getter._get_uncached)
            finally:
                get_user_headers.USABLE_PORTS = usable_orig
