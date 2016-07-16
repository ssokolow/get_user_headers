#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Retrieval of identifying headers from the user's browser"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import datetime, os, platform, sqlite3, subprocess, sys, time
import random, socket, webbrowser

try:
    import http.server as http_server
except ImportError:  # pragma: no cover
    import BaseHTTPServer as http_server

CACHE_ROOT = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
if os.name == 'nt':  # pragma: no cover
    CACHE_ROOT = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA',
                                                               CACHE_ROOT))
CACHE_DIR = os.path.join(CACHE_ROOT, "ua_cache")

def _timestamp(dt_obj):
    """Convert a naive datetime into a POSIX timestamp.

    NOTE: This will discard any millisecond time information.
    """
    return time.mktime(dt_obj.timetuple())

class UserHeaderGetter(object):
    """Wrapper to represent a persistent cache for headers and the code to
    retrieve new ones when stale.

    (Uses SQLite for storage to get locking and corruption resistance)
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
        'Accept-Charset',
        'Accept-Language',
        'Accept',
        'User-Agent',
        'DNT',
    ])

    # Headers which should never be retrieved for safety reasons
    unsafe_headers = set([
        'Cookie',
        'Host',
        'Referer'
    ])

    def __init__(self, path=None):
        path = path or CACHE_DIR
        self.cache_path = os.path.join(path, 'cache.sqlite3')

        # Create the store if not already initialized
        try:
            os.makedirs(path)
        except OSError:
            pass  # Already exists (or access denied)
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

    def _get_uncached(self):
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
                if err.errno != 98:
                    raise
            else:
                port_found = True

        request_url = 'http://localhost:%d' % server_address[1]

        # FIXME: Fire off the subprocess/webbrowser call in another thread to
        #        minimize the chance of a race condition.
        if os.name == 'posix' and not platform.mac_ver()[0]:
            # The webbrowser module uses its own internal resolution order
            # rather han XDG preferences on Linux and, for some reason, its
            # approach to calling Firefox via -remote is broken on my machine.
            # Just use XDG.
            with open(os.devnull, 'wb') as nul:
                subprocess.Popen(['xdg-open', request_url],
                                 stdout=nul, stderr=nul)
        else:
            webbrowser.open_new_tab(request_url)
        httpd.handle_request()
        httpd.server_close()  # Supposedly proper shutdown
        httpd.socket.close()  # Required to silence Py3 unclosed socket warning
        return {key: value for key, value in harvested_headers.pop().items()
                if not set([key, key.title(), key.upper()]
                           ).intersection(self.unsafe_headers)}

    def get_all(self, headers=None, skip_cache=False):
        """Get all headers which are safe to reuse (ie. not cookies)"""
        headers = self._get_cache() if not skip_cache else None

        self.clear_expired()
        headers = headers or self._get_uncached()
        self._save_cache(headers)
        return headers

    def get_safe(self, headers=None, skip_cache=False):
        """Get all headers which should have no or beneficial effects."""
        headers = headers or self.get_all(skip_cache=skip_cache)

        return {key: value for key, value in headers.items()
                if set([key, key.title(), key.upper()]
                       ).intersection(self.safe_headers)}

def randomize_delay(base_delay=2):
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
        print(title)
        print('\n'.join(' {:>25}: {}'.format(k, v)
                        for k, v in headers.items()))

    prettyprint("Headers harvested from user's default browser:", headers)
    prettyprint("\nSafe headers harvested from user's default browser:",
                safe_headers)

# vim: set sw=4 sts=4 expandtab :
