#! /usr/bin/env python

"""
This test verifies that CSS styles properly merges inline with DOM elements.

"""

from cStringIO import StringIO
import os
import re
import sys

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

from premailer import Premailer, etree, transform

BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'data')
WHITESPACE_AFTER_BRACE = re.compile('}\s+')
WHITESPACE_BETWEEN_TAGS = re.compile('>\s*<')


class PremailerTestCase(unittest.TestCase):

    def assert_transformed_html_equal(self, input_html, expected_html,
                                      strip_whitespace_after_brace=False,
                                      use_shortcut_function=False,
                                      **kwargs):
        if use_shortcut_function:
            result_html = transform(input_html, **kwargs)
        else:
            premailer = Premailer(input_html, **kwargs)
            result_html = premailer.transform()

        expected_html = WHITESPACE_BETWEEN_TAGS.sub('><',
                                                    expected_html).strip()
        result_html = WHITESPACE_BETWEEN_TAGS.sub('><', result_html).strip()

        if strip_whitespace_after_brace:
            expected_html = WHITESPACE_AFTER_BRACE.sub('}', expected_html)
            result_html = WHITESPACE_AFTER_BRACE.sub('}', result_html)

        self.assertEqual(expected_html, result_html)

    def read_html_file(self, basename):
        filename = os.path.join(BASE_DATA_DIR, '%s.html' % basename)
        data = ''
        with open(filename) as f:
            data = f.read()
        return data

    def assert_transformed_files_equal(self, name, **kwargs):
        html = self.read_html_file('test_%s' % name)
        expected_html = self.read_html_file('test_%s_expected' % name)
        self.assert_transformed_html_equal(html, expected_html, **kwargs)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_basic_html(self):
        """test the simplest case"""
        self.assert_transformed_files_equal('basic')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_base_url_fixer(self):
        """if you leave some URLS as /foo and set base_url to
        'http://www.google.com' the URLS become 'http://www.google.com/foo'
        """
        self.assert_transformed_files_equal('base_url_fixer',
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
        self.assert_transformed_files_equal('style_block_with_external_urls')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_shortcut_function(self):
        # you don't have to use this approach:
        #   from premailer import Premailer
        #   p = Premailer(html, base_url=base_url)
        #   print p.transform()
        # You can do it this way:
        #   from premailer import transform
        #   print transform(html, base_url=base_url)
        self.assert_transformed_files_equal('shortcut_function',
                                            use_shortcut_function=True)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_css_with_pseudoclasses_included(self):
        "Pick up the pseudoclasses too and include them"
        basename = 'test_css_with_pseudoclasses_included'
        p = Premailer(self.read_html_file(basename))
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
        self.assert_transformed_files_equal('css_with_pseudoclasses_excluded',
                                            strip_whitespace_after_brace=True,
                                            exclude_pseudoclasses=True)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_css_with_whitelisted_pseudoclasses_included(self):
        """Skip things like `a:hover{}` and keep them in the style block, but
        parse things like `p:first-child{}`."""
        basename = 'css_with_whitelisted_pseudoclasses_included'
        self.assert_transformed_files_equal(basename,
                                            strip_whitespace_after_brace=True,
                                            exclude_pseudoclasses=True)

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_css_with_html_attributes(self):
        """Some CSS styles can be applied as normal HTML attribute like
        'background-color' can be turned into 'bgcolor'
        """
        self.assert_transformed_files_equal('css_with_html_attributes',
                                            strip_whitespace_after_brace=True,
                                            exclude_pseudoclasses=True)

    def test_apple_newsletter_example(self):
        # stupidity test
        html = self.read_html_file('test-apple-newsletter')

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
        self.assert_transformed_files_equal('mailto_url',
                                            base_url='http://kungfupeople.com')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_class_removal(self):
        """Ensure that class attributes are removed from the HTML output"""
        self.assert_transformed_files_equal('class_removal')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_support_warnings(self):
        """Ensure that support warnings are emitted when specified"""
        try:
            fake_err = StringIO()
            sys.stderr = fake_err
            self.assert_transformed_files_equal('support_warnings',
                                                support_warnings=True)
            self.assertIn('WARNING: margin not supported in the following',
                          fake_err.getvalue())
        finally:
            sys.stderr = sys.__stderr__

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_duplicate_property_removal(self):
        """Ensure that there are no duplicate properties in a given style
        attribute."""
        self.assert_transformed_files_equal('duplicate_property_removal')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_intact_empty_anchors(self):
        """Ensure that empty anchors are preserved with an end tag."""
        self.assert_transformed_files_equal('intact_empty_anchors')

    @unittest.skipIf(not etree, 'ElementTree is required')
    def test_declaration_trailing_comment(self):
        """Ensure that individual style declarations don't contain
        leading/trailing semicolons."""
        self.assert_transformed_files_equal('declaration_trailing_comment')

if __name__ == '__main__':
        unittest.main()
