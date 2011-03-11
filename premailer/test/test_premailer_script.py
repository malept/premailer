#! /usr/bin/env python
"""Tests for the premailer script.
"""

import os
import re
from subprocess import Popen, PIPE
import sys

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'data')
WHITESPACE_AFTER_BRACE = re.compile('}\s+')
WHITESPACE_BETWEEN_TAGS = re.compile('>\s*<')


class PremailerTestCase(unittest.TestCase):

    def assert_transformed_html_equal(self, result_html, expected_html,
                                      strip_whitespace_after_brace=False,
                                      **kwargs):
        expected_html = WHITESPACE_BETWEEN_TAGS.sub('><',
                                                    expected_html).strip()
        result_html = WHITESPACE_BETWEEN_TAGS.sub('><', result_html).strip()

        if strip_whitespace_after_brace:
            expected_html = WHITESPACE_AFTER_BRACE.sub('}', expected_html)
            result_html = WHITESPACE_AFTER_BRACE.sub('}', result_html)

        self.assertEqual(expected_html, result_html)

    def html_file_path(self, basename):
        return os.path.join(BASE_DATA_DIR, '%s.html' % basename)

    def read_html_file(self, basename):
        filename = self.html_file_path(basename)
        data = ''
        with open(filename) as f:
            data = f.read()
        return data

    def run_premailer(self, basename, **kwargs):
        dirname = os.path.dirname
        bin_path = os.path.join(dirname(dirname(dirname(BASE_DATA_DIR))),
                                'bin', 'premailer')
        args = []
        for key, value in kwargs.iteritems():
            if key == 'strip_whitespace_after_brace':
                continue
            if value:
                flag = '--%s' % key.replace('_', '-')
                if isinstance(value, str):
                    args.append('%s=%s' % (flag, value))
                else:
                    args.append(flag)
        filename = self.html_file_path(basename)
        cmd = [bin_path, filename] + args
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        return proc.communicate()

    def assert_transformed_files_equal(self, name, **kwargs):
        result_html, stderr = self.run_premailer('test_%s' % name, **kwargs)
        expected_html = self.read_html_file('test_%s_expected' % name)
        self.assert_transformed_html_equal(result_html, expected_html, **kwargs)
        return result_html, stderr

    def test_basic_html(self):
        """test the simplest case"""
        self.assert_transformed_files_equal('basic')

    def test_base_url_fixer(self):
        """if you leave some URLS as /foo and set base_url to
        'http://www.google.com' the URLS become 'http://www.google.com/foo'
        """
        self.assert_transformed_files_equal('base_url_fixer',
                                            base_url='http://kungfupeople.com',
                                            preserve_internal_links=True)

    def test_style_block_with_external_urls(self):
        """
        From http://github.com/peterbe/premailer/issues/#issue/2

        If you have
          body { background:url(http://example.com/bg.png); }
        the ':' inside '://' is causing a problem
        """
        self.assert_transformed_files_equal('style_block_with_external_urls')

    def test_css_with_pseudoclasses_included(self):
        "Pick up the pseudoclasses too and include them"
        basename = 'test_css_with_pseudoclasses_included'
        result_html = self.run_premailer(basename)[0]

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

    def test_css_with_pseudoclasses_excluded(self):
        "Skip things like `a:hover{}` and keep them in the style block"
        self.assert_transformed_files_equal('css_with_pseudoclasses_excluded',
                                            strip_whitespace_after_brace=True,
                                            exclude_pseudoclasses=True)

    def test_css_with_html_attributes(self):
        """Some CSS styles can be applied as normal HTML attribute like
        'background-color' can be turned into 'bgcolor'
        """
        self.assert_transformed_files_equal('css_with_html_attributes',
                                            strip_whitespace_after_brace=True,
                                            exclude_pseudoclasses=True)

    def test_apple_newsletter_example(self):
        # stupidity test
        result_html = self.run_premailer('test-apple-newsletter',
                                         exclude_pseudoclasses=False,
                                         keep_style_tags=True)[0]
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

    def test_mailto_url(self):
        """if you use URL with mailto: protocol, they should stay as mailto:
        when baseurl is used
        """
        self.assert_transformed_files_equal('mailto_url',
                                            base_url='http://kungfupeople.com')

    def test_class_removal(self):
        """Ensure that class attributes are removed from the HTML output"""
        self.assert_transformed_files_equal('class_removal')

    def test_support_warnings(self):
        """Ensure that support warnings are emitted when specified"""
        stderr = self.assert_transformed_files_equal('support_warnings',
                                                     support_warnings=True)[1]
        self.assertIn('WARNING: margin not supported in the following', stderr)

if __name__ == '__main__':
        unittest.main()
