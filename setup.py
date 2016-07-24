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
        version="0.1.1",
        description="Helper for retrieving identifying headers from the user's"
                    "default browser",
        long_description="""A self-contained script which allows your script to
retrieve headers like User-Agent from the user's preferred browser to ensure
that requests from your (hopefully well-behaved) script don't stick out like
sore thumbs for overzealous site admins to block without cause.""",
        author="Stephan Sokolow",
        author_email="http://www.ssokolow.com/ContactMe",  # No spam harvesting
        url="https://github.com/ssokolow/get_user_headers",
        license="MIT",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
        keywords="http web bot spider automation",
        py_modules=['get_user_headers'],

        zip_safe=True
    )
