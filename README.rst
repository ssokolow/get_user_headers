Module for retrieving identifying headers from the user's preferred browser
===========================================================================

**Code Health:**

.. image:: https://landscape.io/github/ssokolow/get_user_headers/master/landscape.svg?style=flat
   :target: https://landscape.io/github/ssokolow/get_user_headers/master
   :alt: Code Health

.. image:: https://scrutinizer-ci.com/g/ssokolow/get_user_headers/badges/quality-score.png?b=master
   :target: https://scrutinizer-ci.com/g/ssokolow/get_user_headers/?branch=master
   :alt: Scrutinizer Code Quality

.. image:: https://codeclimate.com/github/ssokolow/get_user_headers/badges/gpa.svg
   :target: https://codeclimate.com/github/ssokolow/get_user_headers
   :alt: Code Climate

.. image:: https://api.codacy.com/project/badge/Grade/864ff2918f1e49f18ce656a3944ffbdf
   :target: https://www.codacy.com/app/from_github/get_user_headers?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ssokolow/get_user_headers&amp;utm_campaign=Badge_Grade
   :alt: Codacy

**Unit Tests:**

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

Message to Website Developers
-----------------------------

**I write bots to streamline tasks I was already doing by hand.** While I
understand the need to prevent abusive behaviour, **not every bot is abusive**
and I hate drudgework.

The two classes of bots I write are RSS feed generators to watch a specific
thread/tag/category/search for updates and simplified HTML exporters for
reading fiction offline (either directly on my OpenPandora_ or on my old Sony
Reader PRS-505 via ebook-convert_).

**I always prefer official feeds/exporters if they meet my needs.** If you
write one, and you announce it well enough for me to discover it, and you don't
charge extra for it, I'll stop using my bots. They're always doomed to be more
fragile anyway. (But, no, **iTunes is not acceptable**. I refuse to use
proprietary clients and/or DRMed formats.)

**I'm always conservative in my update polling**. I can't remember a time I've
ever had an RSS generator poll for updates more frequently than once per day
and my story exporters tend to cache chapters forever unless I manually evict
stale content.

**All of my bots will properly obey any HTTP cache-control headers you set**
and, since hard drive space is relatively cheap and the bots are limited in
scope, they will never prematurely expire cached data the way actual browsers
do.

Double-check that your server setup can efficiently returns a
``304 Not Modified`` response when faced with headers like
``If-Modified-Since`` and ``ETag``. A surprising number of sites are wasting a
ton of CPU time and bandwidth with *real browsers* that way.

Likewise, **my example code also caches properly**, so feel free to ban any
bot with does not respect your cache directives. People who write non-caching
bots have no excuse and will get no sympathy from me.

**My bots also do request throttling** that's *stricter* than what you'll see
from my browser when I middle-click two dozen links in rapid succession so the
later ones can be loading while I look at the earlier ones.

Furthermore, while **I can't trust ROBOTS.TXT to be reasonable**, I write
my own spiders and whitelists to ensure **I only retrieve the bare minimum
necessary** to generate my desired outputs, and I have yet to find a site where
that requires downloading more than specific HTML pages and certain inline
images used as thumbnails or fancy horizontal rulings. (And, while doing so, my
scrapers *permanently* cache static files, regardless of HTTP headers, to be
extra nice.)

**However, don't mistake my kindness for weakness.**

I'm willing to bet that anything that, long **before you make my convenience
bots unfeasible, you'll annoy all of your users into leaving**.

If you start trying to identify bots by their refusal to download supplementary
files, I have no problem downloading and then throwing away CSS/JS/etc.
just to appear more browser-like.

If you do statistical analysis to identify likely bots, I'll do the labwork to
improve the statistical distribution of my ``randomize_delay()`` function to
the point where you start banning too many real humans.

If you start requiring a CAPTCHA or JavaScript, I'll pretend to be a bot you
can't afford to exclude, like GoogleBot.

If you start going to the trouble of maintaining a list of IPs used by the real
GoogleBot or if you actually *are* big enough to survive banning GoogleBot,
I'll extend this into something that makes it easy to embed a full browser
engine and JDownloader_-style "please fill this CAPTCHA" popups into any bot
anyone wants to write.

If your browser fingerprinting gets good enough to foil that, I'll convert this
into a framework that allows my bots to easily puppet my actual day-to-day web
browser to perform their requests.

**Detect abuse, not bots!**

.. _ebook-convert: http://manual.calibre-ebook.com/generated/en/ebook-convert.html
.. _JDownloader: https://en.wikipedia.org/wiki/JDownloader
.. _OpenPandora: http://openpandora.org/
.. _PRS-505: https://en.wikipedia.org/wiki/PRS-505#2007_Model_.28Discontinued_late_2009.29

Installation
------------

At present, I'm still waiting for a reply from the PyPI webmaster(s) on why the
confirmation e-mails never even reach my spam filters, so you'll have to
install directly from this repository.

.. code:: bash

    pip install git+https://github.com/ssokolow/get_user_headers.git@v0.1

I also *strongly* recommend using the requests_ and CacheControl_ libraries to
make your HTTP requests so you can get proper HTTP caching semantics for free.

.. code:: bash

    pip install requests cachecontrol[filecache]

.. _Betamax: https://github.com/sigmavirus24/betamax
.. _CacheControl: https://cachecontrol.readthedocs.io/
.. _FileCache: https://cachecontrol.readthedocs.io/en/latest/storage.html#filecache
.. _requests: http://docs.python-requests.org/

Usage
-----

.. code:: python

    import os, time

    import requests
    from cachecontrol import CacheControl
    from cachecontrol.caches import FileCache

    from get_user_headers import UserHeaderGetter, randomize_delay

    # Measure and average the time a human takes (per page, in seconds)
    # for your specific application and use that number here
    BASE_DELAY = 3

    # requests.Session provides cookie handling and default headers
    # CacheControl automates proper HTTP caching so you don't get banned
    # FileCache ensures your cache survives across multiple runs of your bot
    session = CacheControl(requests.Session(),
        cache=FileCache(os.path.expanduser('~/.cache/http_cache')))
    session.headers.update(UserHeaderGetter().get_safe())

    urls = [(None, 'http://www.example.com/')]
    while urls:
        parent_url, url = urls.pop(0)

        req_headers = {}
        if parent_url:
            req_headers['Referer'] = parent_url

        response = session.get(url, headers=req_headers)

        # TODO: Do actual stuff with the response and maybe urls.append(...)
        print(response)

        # Simulate human limits to foil statistical analysis
        time.sleep(randomize_delay(BASE_DELAY))

Also, while developing your bot, be sure to use some mechanism to cache your
test URLs permanently, such as passing ``forever=True`` when initializing
FileCache_ or using Betamax_. (Both options will make your tests more reliable
and protect you from getting banned for re-running your code too often in a
very short period of time.)

**Example Headers Gathered:**

.. code::

            Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
        User-Agent: Mozilla/5.0 (Windows NT 6.3; WOW64; rv:37.0) Gecko/20100101 Firefox/37.0
               DNT: 1
   Accept-Language: en-US,en;q=0.5

Important Dynamic Headers to Mimic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Don't forget to also provide proper values for the following headers, which
``get_safe()`` cannot return because they change from request to request:

HTTP cache-control headers
    If you are not using my example code, make sure you implement proper HTTP
    caching.

    If your bot doesn't implement HTTP caching and visits a URL more than once,
    then that's abusive behaviour and I won't shed a tear if the website
    administrator blocks you.

``Referer`` (Note the intentional mis-spelling)
   The second-easiest way for a site to detect hastily-written bots after
   checking the ``User-Agent`` header is to check for a missing or incorrect
   URL in the ``Referer`` header.

   Ideally, you want to keep track of which URLs led to which other URLs so you
   can do this perfectly, but most sites will be happy if you set ``Referer``
   to ``http://www.example.com/`` for every request that begins with that root.
   (And various privacy-enhancing browser extensions like RefControl and
   uMatrix also have an option to cause real browsers to behave this way.)

   My example code also demonstrates this.
