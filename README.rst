Module for retrieving identifying headers from the user's preferred browser
===========================================================================

Rationale
---------

Some sites don't provide an API for automating commonly desired tasks and can
be overly aggressive in blocking user agents which merely do what the user
could do anyway (ie. Ctrl+S on every chapter of a story so it can be converted
into an eBook for reading on the go) but faster... *Even when they go out of
their way to be kinder to the website than real browsers by not loading
CSS/JavaScript/fonts/etc. and using a stricter caching policy.*

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

Those are the two kinds of scrapers I write and I refuse to be locked into
walled gardens like the iTunes store.

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

Usage
-----

Call `get_safe_user_headers()` and use the returned headers as defaults for your
HTTP requests.

The resulting headers should either have no effect on the returned content or
should help to ensure that the bot sees the same content the user will see when
visiting the page normally.

Example Output:

.. code::

               dnt: 1
   accept-language: en-US,en;q=0.5
            accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
        user-agent: Mozilla/5.0 (Windows NT 6.3; WOW64; rv:37.0) Gecko/20100101 Firefox/37.0
