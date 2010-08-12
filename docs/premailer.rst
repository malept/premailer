:mod:`premailer` --- Premailer
==============================

.. module:: premailer
   :synopsis Premailer
.. moduleauthor:: Peter Bengtsson <peter@fry-it.com>
.. sectionauthor:: Ryan Coyner <rcoyner@gmail.com>

Premailer transforms standard HTML into a format best suited for e-mail delivery
by creating inline CSS styles.


Style Tags
----------

HTML e-mails does not support style tags and instead requires inline style
attributes on every element. Premailer parses an HTML page, retrieves all the
style blocks and parses the CSS. The DOM tree is then updated accordingly to
generate the final output. For example, the following::


    <html>
      <style type="text/css">
          h1 { border:1px solid black }
          p { color:red;}
          p::first-letter { float:left; }
      </style>
      <h1 style="font-weight:bolder">Peter</h1>
      <p>Hej</p>
    </html>

is transformed into::

    <html>
      <h1 style="font-weight:bolder; border:1px solid black">Peter</h1>
      <p style="{color:red} ::first-letter{float:left}">Hej</p>
    </html>


Relative URLs
-------------

Premailer transforms relative URLs in a HTML page into absolute URLs for all
``href`` and ``src`` attributes that are missing a protocol prefix (i.e.
http://). For example, the following::

    <html>
      <body>
        <a href="/">Home</a>
        <a href="page.html">Page</a>
        <a href="http://crosstips.org">External</a>
        <img src="/folder/">Folder</a>
      </body>
    </html>

is transformed into::

    <html>
      <body>
        <a href="http://www.peterbe.com/">Home</a>
        <a href="http://www.peterbe.com/page.html">Page</a>
        <a href="http://crosstips.org">External</a>
        <img src="http://www.peterbe.com/folder/">Folder</a>
      </body>
    </html>


Additional Attributes
---------------------

Certain HTML attributes are also created on the HTML elemtents if the CSS
contains any ones that are easily translated into HTML attributes. For example,
the following in CSS::

    td { background-color:#eee; }
    
is transformed into the following inline CSS::

    style="background-color:#eee"

and HTML attribute:: 

    bgcolor="#eee"

These extra attributes act as a backup for e-mail clients that are not capable
of rendering style attributes. This feature is modeled after professional HTML
newsletters, such as Amazon's.
