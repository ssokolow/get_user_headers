#!/usr/bin/env python
"""setup.py for get_user_headers"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import sys

if __name__ == '__main__' and 'flake8' not in sys.modules:
    # FIXME: Why does this segfault flake8 under PyPy?
    from setuptools import setup

    setup(
        name="get_user_headers",
        version="0.1",
        description="Helper for retrieving identifying headers from the user's"
                    "default browser",
        long_description="""A self-contained script which allows your script to
retrieve headers like User-Agent from the user's preferred browser to ensure
that requests from your (hopefully well-behaved) script don't stick out like
sore thumbs for overzealous site admins to block without cause.""",
        author="Stephan Sokolow",
        author_email="http://www.ssokolow.com/ContactMe",  # No spam harvesting
        py_modules=['get_user_headers'],

        zip_safe=True
    )
