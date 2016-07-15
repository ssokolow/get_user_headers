#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Retrieval of identifying headers from the user's browser"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import os, platform, subprocess
import random, socket, webbrowser

try:
    import http.server as http_server
except ImportError:
    import BaseHTTPServer as http_server

# Headers which should either have no effect or a desired effect on returned
# content. (So we should mimic them to look more like the user's browser)
MIMIC_SAFE_HEADERS = [
    'Accept-Charset',
    'Accept-Language',
    'Accept',
    'User-Agent',
    'DNT',
]

def get_all_user_headers():
    """Harvest the request headers from the user's default browser."""
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
                    HTTP request headers. This should have closed automatically
                    but your browser ignored the JavaScript
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
        # The webbrowser module uses its own internal resolution order rather
        # than XDG preferences on Linux and, for some reason, its approach to
        # calling Firefox via -remote is broken on my machine. Just use XDG.
        with open(os.devnull, 'wb') as nul:
            subprocess.Popen(['xdg-open', request_url], stdout=nul, stderr=nul)
    else:
        webbrowser.open_new_tab(request_url)
    httpd.handle_request()
    httpd.server_close()  # Supposedly proper shutdown
    httpd.socket.close()  # Required to silence Py3 unclosed socket warning
    return harvested_headers[0]

def get_safe_user_headers(headers=None):
    """Filter for headers from the user's default browser which are safe or
    beneficial to mimic.

    Calls `get_all_user_headers` if no dict is passed in.
    """
    headers = headers or get_all_user_headers()
    matchable_headers = {x.lower(): x for x in MIMIC_SAFE_HEADERS}

    return {key: value for key, value in headers.items()
            if key.lower() in matchable_headers}

if __name__ == '__main__':
    headers = get_all_user_headers()
    safe_headers = get_safe_user_headers(headers)

    print("Headers harvested from user's default browser:")
    print('\n'.join(' {:>25}: {}'.format(k, v)
                    for k, v in headers.items()))
    print("\nSAFE headers harvested from user's default browser:")
    print('\n'.join(' {:>25}: {}'.format(k, v)
                    for k, v in safe_headers.items()))

# vim: set sw=4 sts=4 expandtab :
