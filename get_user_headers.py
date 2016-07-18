#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Retrieval of identifying headers from the user's browser"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import datetime, errno, os, platform, sqlite3, subprocess, sys, time
import random, socket, webbrowser

try:
    import http.server as http_server
except ImportError:  # pragma: no cover
    import BaseHTTPServer as http_server

OS_ERROR = OSError  # pylint: disable=invalid-name
CACHE_ROOT = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
if os.name == 'nt':  # pragma: no cover
    OS_ERROR = WindowsError  # pylint: disable=undefined-variable
    CACHE_ROOT = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA',
                                                               CACHE_ROOT))


CACHE_DIR = os.path.join(CACHE_ROOT, "ua_cache")

# Reasonable guess at an average time for a human to cycle between
# Ctrl+S, Enter, and clicking "next page", assuming blocking HTTP requests.
DEFAULT_BASE_DELAY = 3  # seconds

def _timestamp(dt_obj):
    """Convert a naive datetime into a POSIX timestamp.

    NOTE: This will discard any millisecond time information.
    """
    return time.mktime(dt_obj.timetuple())

def webbrowser_open(url):
    """Wrapper for webbrowser.open_new_tab to fix recent Firefox versions.

    On Linux, the Python standard library brings along its own hard-coded
    support for opening URLs in Firefox which was broken by the removal of
    the `-remote` option.

    This works around that by providing an alternative which calls `xdg-open`,
    similar to how, on Windows and OSX, the webbrowser module use OS API calls
    equivalent to `start <url>` and `open <url>`.
    """
    if os.name == 'posix' and not platform.mac_ver()[0]:
        with open(os.devnull, 'wb') as nul:
            subprocess.Popen(['xdg-open', url], stdout=nul, stderr=nul)
    else:  # pragma: no cover
        webbrowser.open_new_tab(url)


class UserHeaderGetter(object):
    """Wrapper to represent a persistent cache for headers and the code to
    retrieve new ones when stale.

    (Uses SQLite for storage to get locking and corruption resistance)

    References used:
    - https://en.wikipedia.org/wiki/List_of_HTTP_headers
    - https://msdn.microsoft.com/en-us/library/aa287673(v=vs.71).aspx
    - https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
    - http://httpwg.org/http-extensions/client-hints.html
    """
    # How long retrieved headers should be cached to avoid bothering the user
    # by popping open a new browser tab
    cache_timeout = datetime.timedelta(days=7)
    cache_schema = """
        CREATE TABLE IF NOT EXISTS user_headers (
            py_version INTEGER NOT NULL,
            key TEXT NOT NULL COLLATE NOCASE,
            value TEXT,
            expires INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS user_headers_versions
            ON user_headers (py_version, key);
        CREATE INDEX IF NOT EXISTS user_headers_expires
            ON user_headers (expires);
    """

    # Headers which should either have a null or desired effect on returned
    # content. (So we should mimic them to look more like the user's browser)
    safe_headers = set([
        'Accept',
        'Accept-Charset',
        'Accept-Language',
        'DNT',
        'From',              # If you don't like it, fix your browser
        'User-Agent',
        'X-ATT-Deviceid',    # TODO: Verify proper capitalization of ID
        'X-Wap-Profile',
    ])

    # Headers which should never be retrieved for safety reasons
    unsafe_headers = set([
        # Stuff which could leak localhost credentials
        'Authorization',
        'Cookie',
        'Cookie2',           # RFC 6265: Obsolete
        'X-Csrf-Token',
        'X-CSRFToken',
        'X-UIDH',            # Don't ease tracking. Let Verizon re-insert it.
        'X-XSRF-TOKEN',
        # TODO: Need to research whether it's safe to mimic
        'Proxy-Authorization',
        # Stuff we'd like to match behaviour on, but which can't be naively
        # repeated because they depend on the request or client implementation
        'Content-Encoding',  # W3C says it's an entity header
        'Content-Language',  # W3C says it's an entity header
        'Content-Length',
        'Content-Location',  # MSDN says: Entity. Can be used in requests
        'Content-MD5',       # Wikipedia says: Obsolete
        'Content-Range',     # MSDN
        'Content-Type',
        'Date',
        'Expect',
        'Expires',           # MSDN says: Entity. Can be used in requests
        'Front-End-Https',
        'Host',
        'If-Match',
        'If-Modified-Since',
        'If-None-Match',
        'If-Range',
        'If-Unmodified-Since',
        'Last-Modified',     # MSDN says: Entity. Can be used in requests
        'Origin',
        'Range',
        'Referer',
        'TE',
        "Transfer-Encoding",
        'Upgrade',
        'X-Forwarded-Host',
        'X-Forwarded-Proto',
        'X-Http-Method-Override',
        'X-ProxyUser-Ip',
        'X-Requested-With',
    ])

    # Canonical capitalizations of headers for use in normalization
    known_headers = safe_headers.union(unsafe_headers).union([
        'Accept-Encoding',
        'Accept-Datetime',   # Wikipedia says: Provisional
        'Cache-Control',
        'Connection',
        'Pragma',            # MSDN says: Can be used in requests
        'Proxy-Connection',
        # Headers which should only be sent based on parent response's
        # Accept-CH response header
        "DPR",
        "Width",
        "Viewport-Width",
        "Downling",
        "Save-Data",
        # TODO: Research the real-world uses of these
        'Forwarded',
        'Max-Forwards',
        "Trailer",           # MSDN says: Can be used in requests
        'Via',
        'Warning',
        'X-Forwarded-For',   # TODO: Do any client-side proxies set this?
    ])

    def __init__(self, path=None):
        path = path or CACHE_DIR
        self.cache_path = os.path.join(path, 'cache.sqlite3')

        # Create the store if not already initialized
        try:
            os.makedirs(path)
        except OS_ERROR as err:
            if not err.errno == errno.EEXIST:
                raise
        self.cache_conn = sqlite3.connect(self.cache_path)
        self.cache_conn.executescript(self.cache_schema)

    def clear_expired(self):
        """Purge expired cache entries"""
        self.cache_conn.execute("DELETE FROM user_headers WHERE expires < ?",
                                [_timestamp(datetime.datetime.now())])
        self.cache_conn.commit()

    def _save_cache(self, headers):
        """Save given headers to the cache.

        NOTE: Does not clear existing headers with unlisted keys.
        """
        ts_expires = _timestamp(datetime.datetime.now() + self.cache_timeout)
        self.cache_conn.executemany("INSERT OR REPLACE INTO user_headers ("
            "py_version, key, value, expires) VALUES (?, ?, ?, ?)",
            [[sys.version_info.major, x, y, ts_expires] for x, y in
             list(headers.items())])
        self.cache_conn.commit()

    def _get_cache(self):
        """Retrieve cached headers.

        Attempts to use headers cached by the same version of Python, falling
        back to Python 3 if that fails. (To minimize uncached lookup without
        letting Python 2's case normalization potentially cause Python 3 to
        give away the bot's nature.
        """
        for version in (sys.version_info.major, 3):
            headers = list(self.cache_conn.execute(
                "SELECT key, value FROM user_headers WHERE py_version = ?",
                [version]))
            if headers:
                return dict(headers)
        return None

    def normalize_header_names(self, headers):
        """Normalize the case of keys in the given dictionary.

        Keys in `known_headers` will be normalized to the standardized casing
        while unrecognized keys will be fed through ``str.title()``
        """
        # TODO: Consider using my titlecase_up() function from game_launcher to
        # prevent acronyms from getting converted back to titlecase.
        # TODO: Force the C locale before doing this locale-specific operation
        known = {x.lower(): x for x in self.known_headers}
        return {known.get(x.lower(), x.title()): y for x, y in headers.items()}

    def _get_uncached(self):  # pylint: disable=no-self-use
        """Harvest and return all request headers from user default browser."""
        harvested_headers = []

        class UAProbingRequestHandler(http_server.BaseHTTPRequestHandler):
            """Request handler for probing the browser's User-Agent string"""

            placeholder_content = b"""<!DOCTYPE html>
                <html>
                    <head>
                        <title>Close Me</title>
                        <style>
                        body {
                            margin: auto;
                            max-width: 600px;
                            text-align: center;
                        }
                        </style>
                    </head>
                    <body>
                      <h1>You may now close this tab</h1>
                      <p>(A program needed to inspect your preferred browser's
                        HTTP request headers. This should have closed
                        automatically but your browser ignored the JavaScript
                        <code>close()</code> call.)
                      </p>
                      <script>window.close();</script>
                    </body>
                </html>"""

            # pylint: disable=invalid-name
            def do_HEAD(self):  # NOQA
                """Called to serve a HEAD request"""
                harvested_headers.append(self.headers)
                self.send_response(200)
                self.send_header("Content-type", 'text/html; charset=utf8')
                self.send_header("Content-Length",
                                 str(len(self.placeholder_content)))
                self.send_header("Last-Modified", self.date_time_string())
                self.end_headers()

            # pylint: disable=invalid-name
            def do_GET(self):  # NOQA
                """Called to serve a GET request"""
                self.do_HEAD()
                self.wfile.write(self.placeholder_content)

            def log_message(self, *args):
                """Silence the usual logging messages"""
                pass

        port_found = False
        while not port_found:
            server_address = ('', random.randrange(1024, 65535))
            try:
                httpd = http_server.HTTPServer(server_address,
                                               UAProbingRequestHandler)
            except socket.error as err:
                if err.errno != 98:  # Retry if the port is taken
                    raise
            else:
                port_found = True

        request_url = 'http://localhost:%d' % server_address[1]

        # FIXME: Fire off the subprocess/webbrowser call in another thread to
        #        minimize the chance of a race condition. (And block until the
        #        server is ready to accept requests in order to ENSURE it.)
        webbrowser_open(request_url)
        httpd.handle_request()
        httpd.server_close()  # Supposedly proper shutdown
        httpd.socket.close()  # Required to silence Py3 unclosed socket warning
        return harvested_headers.pop()

    def get_all(self, headers=None, skip_cache=False):
        """Get all headers which are safe to reuse (ie. not cookies)"""
        if not headers:
            headers = self._get_cache() if not skip_cache else {}

            self.clear_expired()
            headers = headers or self._get_uncached()
            self._save_cache(headers)

        return {key: value for key, value
                in self.normalize_header_names(headers).items()
                if key not in self.unsafe_headers}

    def get_safe(self, headers=None, skip_cache=False):
        """Get all headers which should have no or beneficial effects."""
        headers = headers or self.get_all(skip_cache=skip_cache)

        return {key: value for key, value
                in self.normalize_header_names(headers).items()
                if key in self.safe_headers}

def randomize_delay(base_delay=DEFAULT_BASE_DELAY):
    """Return a time to wait in floating-point seconds to disguise automation.

    This function currently uses the "base delay multiplied by a random value
    between 0.5 and 1.5" algorithm described in the wget manual entry for the
    --random-wait option.

    However, it will probably eventually be enhanced with experimental evidence
    to even more accurately match the statistical behaviour of a user manually
    downloading pages using Ctrl+S.

    The main things I need to determine are the type of statistical
    distribution to use and mean time it takes a typical user on a typical
    website to do the following once they get on a roll...

    1. Wait for the page to load
    2. Press Ctrl+S
    3. Press Enter
    4. Acquire and click the "next chapter/page/etc." button

    (And then err on the slow side of average to further improve the chances
    that humans will get driven away before the bots get caught reliably.)
    """
    return base_delay * random.uniform(0.5, 1.5)

if __name__ == '__main__':  # pragma: no cover
    getter = UserHeaderGetter()
    headers = getter.get_all()
    safe_headers = getter.get_safe(headers)

    def prettyprint(title, headers):
        """Deduplicated pretty-print code"""
        print(title)
        print('\n'.join(' {:>25}: {}'.format(k, v)
                        for k, v in headers.items()))

    prettyprint("Headers harvested from user's default browser:", headers)
    prettyprint("\nSafe headers harvested from user's default browser:",
                safe_headers)

# vim: set sw=4 sts=4 expandtab :
