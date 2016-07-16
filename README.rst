Module for retrieving identifying headers from the user's preferred browser
===========================================================================

**Code Health:**

.. image:: https://landscape.io/github/ssokolow/get_user_headers/master/landscape.svg?style=flat
   :target: https://landscape.io/github/ssokolow/get_user_headers/master
   :alt: Code Health

.. image:: https://scrutinizer-ci.com/g/ssokolow/get_user_headers/badges/quality-score.png?b=master
   :target: https://scrutinizer-ci.com/g/ssokolow/get_user_headers/?branch=master
   :alt: Scrutinizer Code Quality

.. image:: https://api.codacy.com/project/badge/Grade/864ff2918f1e49f18ce656a3944ffbdf
   :target: https://www.codacy.com/app/from_github/get_user_headers?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ssokolow/get_user_headers&amp;utm_campaign=Badge_Grade
   :alt: Codacy

.. image:: https://codeclimate.com/github/ssokolow/get_user_headers/badges/gpa.svg
   :target: https://codeclimate.com/github/ssokolow/get_user_headers
   :alt: Code Climate

**Unit Tests (In Development):**

.. image:: https://travis-ci.org/ssokolow/get_user_headers.svg?branch=master
   :target: https://travis-ci.org/ssokolow/get_user_headers
   :alt: Unit Tests

.. image:: https://ci.appveyor.com/api/projects/status/1ds9dwd85vl94nsi?svg=true
   :target: https://ci.appveyor.com/project/ssokolow/get-user-headers
   :alt: Unit Tests (Windows)

.. image:: https://coveralls.io/repos/github/ssokolow/get_user_headers/badge.svg?branch=master
   :target: https://coveralls.io/github/ssokolow/get_user_headers?branch=master
   :alt: Coverage

**Project Status:**

.. image:: https://badge.waffle.io/ssokolow/get_user_headers.svg?label=ready&title=Ready%20Tasks
   :target: https://waffle.io/ssokolow/get_user_headers
   :alt: 'Tasks ready to be worked on'

Developed under Python 2.7 and 3.4.

Rationale
---------

Some sites don't provide an API for automating commonly desired tasks and can
be overly aggressive in blocking user agents which merely do what the user
could do anyway (ie. Ctrl+S on every chapter of a story so it can be converted
into an eBook for reading on the go) but faster... *Even when they go out of
their way to be kinder to the website than real browsers by not loading
images/CSS/JavaScript/fonts/etc. and using a stricter caching policy.*

This module makes it easier for well-intentioned convenience bots to disguise
themselves as the user's regular browser. When combined with a randomized
delay between each request, this makes it difficult for sites to distinguish
actions performed by the user directly from actions performed by a bot acting
on behalf of the user... thus forcing such sites to address the root problem
(abusive behaviour) rather than singling out bots which are only doing what
humans otherwise would.

I understand that the desire to display advertising may be a factor, but I feel
that ad-blocking extensions will always be far more popular than this ever
could be and those are part of the browsers that are let through, un-molested.

Warning to Website Developers
-----------------------------

While I understand the need to prevent abusive behaviour, I don't take
kindly to being forced into pointless drudgework because you were too busy to
provide an RSS feed or an ePub exporter.

Those are the two kinds of scrapers I write and, no, a walled garden with a
proprietary client, such as Apple is offering, is not an acceptable substitute.

If you do statistical analysis to identify likely bots, I'll do the labwork to
develop a random delay function which is statistically indistinguishable from a
human performing the task.

If you just slap a CAPTCHA or some "must have JavaScript" check on your
site on the continued assumption that all bots must be abusers, I'll extend
this into something that makes it easy to embed a full browser engine and
JDownloader_-style "please fill this CAPTCHA" popup into any bot.

(I'm willing to bet that anything that makes my convenience bots unfeasible
will annoy users on normal browsers enough to drive them away in droves.)

...or possibly write a framework which makes it easy for any bot to integrate
with the user's browser to bypass checks.

**Detect abuse, not bots!**

.. _JDownloader: https://en.wikipedia.org/wiki/JDownloader

Installation
------------

At present, I'm still waiting for a reply from the PyPI webmaster(s) on why the
confirmation e-mails never even reach my spam filters, so you'll have to
install directly from this repository.

.. code:: bash

    pip install git+https://github.com/ssokolow/get_user_headers.git

(I haven't yet tagged the 0.1 release because I'd like to grow the unit test
suite as much as possible before my inability to push to PyPI is resolved.)

Usage
-----

.. code:: python

    import time
    from get_user_headers import UserHeaderGetter, randomize_delay

    base_delay = 3  # Measure the average time a human takes in seconds
    headers = UserHeaderGetter().get_safe()

    # <configure HTTP client to use retrieved headers>

    while next_page:
       # Simulate human limits to foil statistical analysis
       time.sleep(randomize_delay(base_delay))

       # <retrieve another page>


The resulting headers should either have no effect on the returned content or
should help to ensure that the bot sees the same content the user will see when
visiting the page normally.

**Example Headers Gathered:**

.. code::

            Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
        User-Agent: Mozilla/5.0 (Windows NT 6.3; WOW64; rv:37.0) Gecko/20100101 Firefox/37.0
               DNT: 1
   Accept-Language: en-US,en;q=0.5

