#! /usr/bin/env python

"""
This test verifies that CSS styles properly merges inline with DOM elements.

"""

from cStringIO import StringIO
import re
import sys

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

from premailer import Premailer, etree

WHITESPACE_AFTER_BRACE = re.compile('}\s+')
WHITESPACE_BETWEEN_TAGS = re.compile('>\s*<')


class PremailerTestCase(unittest.TestCase):

    def assert_transformed_html_equal(self, input_html, expected_html,
                                      strip_whitespace_after_brace=False,
                                      **kwargs):
        premailer = Premailer(input_html, **kwargs)
        result_html = premailer.transform()

        expected_html = WHITESPACE_BETWEEN_TAGS.sub('><',
                                                    expected_html).strip()
        result_html = WHITESPACE_BETWEEN_TAGS.sub('><', result_html).strip()

        if strip_whitespace_after_brace:
            expected_html = WHITESPACE_AFTER_BRACE.sub('}', expected_html)
            result_html = WHITESPACE_AFTER_BRACE.sub('}', result_html)

        self.assertEqual(expected_html, result_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_basic_html(self):
        """test the simplest case"""
        html = """<html>
        <head>
        <title>Title</title>
        <style type="text/css">
        h1, h2 { color:red; }
        strong {
            text-decoration:none
            }
        </style>
        </head>
        <body>
        <h1>Hi!</h1>
        <p><strong>Yes!</strong></p>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <h1 style="color:red">Hi!</h1>
        <p><strong style="text-decoration:none">Yes!</strong></p>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_base_url_fixer(self):
        """if you leave some URLS as /foo and set base_url to
        'http://www.google.com' the URLS become 'http://www.google.com/foo'
        """
        html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <img src="/images/foo.jpg"/>
        <img src="/images/bar.gif"/>
        <img src="http://www.googe.com/photos/foo.jpg">
        <a href="/home">Home</a>
        <a href="http://www.peterbe.com">External</a>
        <a href="subpage">Subpage</a>
        <a href="#internal_link">Internal Link</a>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <img src="http://kungfupeople.com/images/foo.jpg"/>
        <img src="http://kungfupeople.com/images/bar.gif"/>
        <img src="http://www.googe.com/photos/foo.jpg"/>
        <a href="http://kungfupeople.com/home">Home</a>
        <a href="http://www.peterbe.com">External</a>
        <a href="http://kungfupeople.com/subpage">Subpage</a>
        <a href="#internal_link">Internal Link</a>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html,
                                           base_url='http://kungfupeople.com',
                                           preserve_internal_links=True)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_style_block_with_external_urls(self):
        """
        From http://github.com/peterbe/premailer/issues/#issue/2

        If you have
          body { background:url(http://example.com/bg.png); }
        the ':' inside '://' is causing a problem
        """
        html = """<html>
        <head>
        <title>Title</title>
        <style type="text/css">
        body {
          color:#123;
          background: url(http://example.com/bg.png);
          font-family: Omerta;
        }
        </style>
        </head>
        <body>
        <h1>Hi!</h1>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body style="color:#123;background:url(http://example.com/bg.png);\
font-family:Omerta">
        <h1>Hi!</h1>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_shortcut_function(self):
        # you don't have to use this approach:
        #   from premailer import Premailer
        #   p = Premailer(html, base_url=base_url)
        #   print p.transform()
        # You can do it this way:
        #   from premailer import transform
        #   print transform(html, base_url=base_url)
        html = """<html>
        <head>
        <style type="text/css">h1{color:#123}</style>
        </head>
        <body>
        <h1>Hi!</h1>
        </body>
        </html>"""

        expect_html = """<html>
        <head></head>
        <body>
        <h1 style="color:#123">Hi!</h1>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_css_with_pseudoclasses_included(self):
        "Pick up the pseudoclasses too and include them"
        html = """<html>
        <head>
        <style type="text/css">
        a.special:link { text-decoration:none; }
        a { color:red; }
        a:hover { text-decoration:none; }
        a,a:hover,
        a:visited { border:1px solid green; }
        p::first-letter {float: left; font-size: 300%}
        </style>
        </head>
        <body>
        <a href="#" class="special">Special!</a>
        <a href="#">Page</a>
        <p>Paragraph</p>
        </body>
        </html>"""

        p = Premailer(html)
        result_html = p.transform()

        # because we're dealing with random dicts here we can't predict what
        # order the style attribute will be written in so we'll look for things
        # manually.
        self.assertIn('<head></head>', result_html)
        self.assertIn('<p style="::first-letter{float:left;font-size:300%}">'\
                      'Paragraph</p>', result_html)

        self.assertIn('style="{color:red;border:1px solid green}', result_html)
        self.assertIn(' :visited{border:1px solid green}', result_html)
        self.assertIn(' :hover{text-decoration:none;border:1px solid green}',
                      result_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_css_with_pseudoclasses_excluded(self):
        "Skip things like `a:hover{}` and keep them in the style block"
        html = """<html>
        <head>
        <style type="text/css">
        a { color:red; }
        a:hover { text-decoration:none; }
        a,a:hover,
        a:visited { border:1px solid green; }
        p::first-letter {float: left; font-size: 300%}
        </style>
        </head>
        <body>
        <a href="#">Page</a>
        <p>Paragraph</p>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <style type="text/css">a:hover{text-decoration:none}
        a:hover{border:1px solid green}
        a:visited{border:1px solid green}
        p::first-letter{float:left;font-size:300%}
        </style>
        </head>
        <body>
        <a href="#" style="color:red;border:1px solid green">Page</a>
        <p>Paragraph</p>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html,
                                           strip_whitespace_after_brace=True,
                                           exclude_pseudoclasses=True)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_css_with_html_attributes(self):
        """Some CSS styles can be applied as normal HTML attribute like
        'background-color' can be turned into 'bgcolor'
        """
        html = """<html>
        <head>
        <style type="text/css">
        td { background-color:red; }
        p { text-align:center; }
        table { width:200px; }
        </style>
        </head>
        <body>
        <p>Text</p>
        <table>
          <tr>
            <td>Cell 1</td>
            <td>Cell 2</td>
          </tr>
        </table>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        </head>
        <body>
        <p style="text-align:center" align="center">Text</p>
        <table style="width:200px" width="200">
          <tr>
            <td style="background-color:red" bgcolor="red">Cell 1</td>
            <td style="background-color:red" bgcolor="red">Cell 2</td>
          </tr>
        </table>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html,
                                           strip_whitespace_after_brace=True,
                                           exclude_pseudoclasses=True)

    def test_apple_newsletter_example(self):
        # stupidity test
        import os
        html_file = os.path.join(os.path.dirname(__file__),
                             'test-apple-newsletter.html')
        html = open(html_file).read()

        p = Premailer(html, exclude_pseudoclasses=False,
                      keep_style_tags=True)
        result_html = p.transform()
        self.assertIn('<html>', result_html)
        self.assertIn("""<style media="only screen and (max-device-width: \
480px)" type="text/css">*{line-height:normal !important;\
-webkit-text-size-adjust:125%}</style>""", result_html)
        self.assertIsNotNone(result_html.find('Add this to your calendar'))
        self.assertIn('''style="{font-family:Lucida Grande,Arial,Helvetica,\
Geneva,Verdana,sans-serif;font-size:11px;color:#5b7ab3} :active{color:#5b7ab3;\
text-decoration:none} :visited{color:#5b7ab3;text-decoration:none} :hover\
{color:#5b7ab3;text-decoration:underline} :link{color:#5b7ab3;text-decoration:\
none}">Add this to your calendar''', result_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_mailto_url(self):
        """if you use URL with mailto: protocol, they should stay as mailto:
        when baseurl is used
        """
        html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <a href="mailto:e-mail@example.com">e-mail@example.com</a>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <a href="mailto:e-mail@example.com">e-mail@example.com</a>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html,
                                           base_url='http://kungfupeople.com')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_class_removal(self):
        """Ensure that class attributes are removed from the HTML output"""
        html = """<html>
        <head>
        <title>Title</title>
        <style type="text/css">
        .text { font-family:sans-serif }
        </style>
        </head>
        <body>
        <h1 class="text">Hi!</h1>
        <p><strong class="text">Yes!</strong></p>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <h1 style="font-family:sans-serif">Hi!</h1>
        <p><strong style="font-family:sans-serif">Yes!</strong></p>
        </body>
        </html>"""

        self.assert_transformed_html_equal(html, expect_html)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_support_warnings(self):
        """Ensure that support warnings are emitted when specified"""
        html = """<html>
        <head>
        <title>Title</title>
        <style type="text/css">
        .text { margin:2px }
        </style>
        </head>
        <body>
        <h1 class="text">Hi!</h1>
        <p><strong class="text">Yes!</strong></p>
        </body>
        </html>"""

        expect_html = """<html>
        <head>
        <title>Title</title>
        </head>
        <body>
        <h1 style="margin:2px">Hi!</h1>
        <p><strong style="margin:2px">Yes!</strong></p>
        </body>
        </html>"""

        try:
            fake_err = StringIO()
            sys.stderr = fake_err
            self.assert_transformed_html_equal(html, expect_html,
                                               support_warnings=True)
            self.assertIn('WARNING: margin not supported in the following',
                          fake_err.getvalue())
        finally:
            sys.stderr = sys.__stderr__

if __name__ == '__main__':
        unittest.main()
