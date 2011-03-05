# http://www.peterbe.com/plog/premailer.py
from collections import defaultdict
import os
import re
import sys
import urlparse

import cssutils
from lxml.cssselect import CSSSelector
from lxml import etree
import yaml

__version__ = '1.9'

__all__ = ['PremailerError', 'Premailer', 'transform']

CLIENT_SUPPORT_YAML = os.path.join(os.path.dirname(__file__), 'data',
                                   'client_support.yaml')


class PremailerError(Exception):
    pass


class Premailer(object):
    def __init__(self, html, base_url=None,
                 preserve_internal_links=False,
                 exclude_pseudoclasses=False,
                 keep_style_tags=False,
                 include_star_selectors=False,
                 external_styles=[],
                 support_warnings=False):
        self.html = html
        self.base_url = base_url
        self.preserve_internal_links = preserve_internal_links
        self.exclude_pseudoclasses = exclude_pseudoclasses
        # whether to delete the <style> tag once it's been processed
        self.keep_style_tags = keep_style_tags
        # whether to process or ignore selectors like '* { foo:bar; }'
        self.include_star_selectors = include_star_selectors
        if isinstance(external_styles, basestring):
            external_styles = [external_styles]
        self.external_styles = external_styles
        self.support_warnings = support_warnings
        if self.support_warnings:
            self.support_matrix = \
                yaml.load(open(CLIENT_SUPPORT_YAML))

    def _check_style_support(self, style):
        for prop in style.getProperties():
            name = prop.name
            if name in self.support_matrix['css_properties']:
                unsupported = self.support_matrix['css_properties'][name]\
                                                 ['unsupported_in']
                print >> sys.stderr, '** WARNING: %s not supported in the ' \
                      'following clients: %s' % (name, ', '.join(unsupported))

    def _parse_stylesheet(self, page, stylesheet):
        leftovers = []
        for rule in stylesheet.cssRules:
            if rule.type == cssutils.css.CSSRule.STYLE_RULE:
                if self.support_warnings:
                    self._check_style_support(rule.style)
                style = rule.style.cssText.strip()
                for selector in rule.selectorList:
                    sel_text = selector.selectorText
                    pseudoclass = ''
                    if '*' in sel_text and not self.include_star_selectors:
                        leftovers.append(cssutils.css.CSSStyleRule(sel_text,
                                                                   style))
                        continue
                    elif ':' in sel_text:  # pseudoclass
                        if self.exclude_pseudoclasses:
                            style_rule = cssutils.css.CSSStyleRule(sel_text,
                                                                   style)
                            leftovers.append(style_rule)
                            continue
                        else:
                            sel_text, pseudoclass = re.split(':', sel_text, 1)

                    css_selector = CSSSelector(sel_text)
                    for item in css_selector(page):
                        if pseudoclass:
                            self.styles[item].append((pseudoclass, style))
                        else:
                            self.styles[item].append(style)
        return leftovers

    def transform(self, pretty_print=True):
        """change the self.html and return it with CSS turned into style
        attributes.
        """
        if etree is None:
            return self.html

        parser = etree.HTMLParser()
        tree = etree.fromstring(self.html.strip(), parser).getroottree()
        page = tree.getroot()

        cssutils.ser.prefs.useMinified()

        if page is None:
            print repr(self.html)
            raise PremailerError("Could not parse the html")
        assert page is not None

        ##
        ## style selectors
        ##

        self.styles = defaultdict(list)
        for style in CSSSelector('style')(page):
            css_body = etree.tostring(style)
            css_body = css_body.split('>')[1].split('</')[0]
            leftovers = self._parse_stylesheet(page,
                                               cssutils.parseString(css_body))

            if leftovers:
                style.text = '\n'.join([r.cssText for r in leftovers])
            elif not self.keep_style_tags:
                parent_of_style = style.getparent()
                parent_of_style.remove(style)

        for stylefile in self.external_styles:
            if stylefile.startswith('http://'):
                self._parse_stylesheet(page, cssutils.parseUrl(stylefile))
            elif os.path.exists(stylefile):
                self._parse_stylesheet(page, cssutils.parseFile(stylefile))
            else:
                raise ValueError(u'Could not find external style: %s' % \
                                 stylefile)

        for element, rules in self.styles.iteritems():
            rules += [element.attrib.get('style', '')]
            declarations = []
            pseudoclass_rules = defaultdict(list)
            for rule in rules:
                if not rule:
                    continue
                elif isinstance(rule, tuple):  # pseudoclass
                    pseudoclass, prules = rule
                    pseudoclass_rules[pseudoclass].append(prules)
                else:
                    declarations.append(rule)
            css_text = ';'.join(declarations)
            style = cssutils.parseStyle(css_text)
            if pseudoclass_rules:
                prules_list = []
                for pclass, prules in pseudoclass_rules.iteritems():
                    pdecl = cssutils.parseStyle(';'.join(prules))
                    prules_list.append(':%s{%s}' % (pclass, pdecl.cssText))
                if css_text:
                    element.attrib['style'] = '{%s} %s' % \
                        (style.cssText, ' '.join(prules_list))
                else:
                    element.attrib['style'] = ' '.join(prules_list)
            else:
                element.attrib['style'] = style.cssText
            self._style_to_basic_html_attributes(element, style)

        # now we can delete all 'class' attributes
        for item in page.xpath('//*[@class]'):
            del item.attrib['class']

        ##
        ## URLs
        ##

        if self.base_url:
            for attr in ('href', 'src'):
                for item in page.xpath('//*[@%s]' % attr):
                    if attr == 'href' and self.preserve_internal_links \
                           and item.attrib[attr].startswith('#'):
                        continue
                    item.attrib[attr] = urlparse.urljoin(self.base_url,
                                                         item.attrib[attr])

        return etree.tostring(page, pretty_print=pretty_print) \
                    .replace('<head/>', '<head></head>')

    def _style_to_basic_html_attributes(self, element, style):
        """given an element and styles like
        'background-color:red; font-family:Arial' turn some of that into HTML
        attributes. like 'bgcolor', etc.

        Note, the style_content can contain pseudoclasses like:
        '{color:red; border:1px solid green} :visited{border:1px solid green}'
        """

        attributes = {}
        for prop in style.getProperties():
            name = prop.name
            value = prop.propertyValue.cssText

            if name == 'text-align':
                attributes['align'] = value.strip()
            elif name == 'background-color':
                attributes['bgcolor'] = value.strip()
            elif name == 'width':
                value = value.strip()
                if value.endswith('px'):
                    value = value[:-2]
                attributes['width'] = value

        for key, value in attributes.items():
            if key in element.attrib:
                # already set, don't dare to overwrite
                continue
            element.attrib[key] = value


def transform(html, base_url=None):
    return Premailer(html, base_url=base_url).transform()
