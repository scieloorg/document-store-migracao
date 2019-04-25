import os
import itertools
import logging

from lxml import etree

from documentstore_migracao.utils import files


logger = logging.getLogger(__name__)


def parse_value(value):
    value = value.lower()
    if value.isdigit():
        return value.zfill(2)
    if 'spe' in value:
        return 'spe'
    if 'sup' in value:
        return 's'
    return value


def parse_issue(issue):
    issue = ' '.join([item for item in issue.split()])
    parts = issue.split()
    parts = [parse_value(item) for item in parts]
    s = '-'.join(parts)
    s = s.replace('spe-', 'spe')
    s = s.replace('s-', 's')
    if s.endswith('s'):
        s += '0'
    return s


def is_asset_href(href):
    return ('img/revistas' in href or href.count('.') == 1) and \
           (
               ':' not in href and \
               '@' not in href and \
               not href.startswith('www') and \
               not href.startswith('http')
           )


class SPS_Package:

    def __init__(self, xmltree, prefix_asset_name):
        self.xmltree = xmltree
        self.prefix_asset_name = prefix_asset_name

    @property
    def xmltree(self):
        return self._xmltree

    @xmltree.setter
    def xmltree(self, value):
        try:
            etree.tostring(value)
        except TypeError:
            raise
        else:
            self._xmltree = value

    @property
    def issn(self):
        return self.xmltree.findtext('.//issn[@pub-type="epub"]') or \
               self.xmltree.findtext('.//issn[@pub-type="ppub"]') or \
               self.xmltree.findtext('.//issn')

    @property
    def acron(self):
        return self.xmltree.findtext(
            './/journal-id[@journal-id-type="publisher-id"]')

    @property
    def parse_article_meta(self):
        elements = ['volume', 'issue', 'fpage', 'lpage', 'elocation',
                    'pub-date', 'article-id']
        items = []
        for elem_name in elements:
            xpath = './/article-meta//{}'.format(elem_name)
            for node in self.xmltree.findall(xpath):
                if node is not None:
                    content = node.text
                    if node.tag == 'article-id':
                        elem_name = node.get('pub-id-type')
                        if elem_name == 'doi':
                            if '/' in content:
                                content = content[content.find('/')+1:]
                    if node.tag == 'issue':
                        content = parse_issue(content)
                    elif node.tag == 'pub-date':
                        content = node.findtext('year')
                        elem_name = 'year'
                    if content.isdigit() and int(content) == 0:
                        content = ''
                    if content:
                        items.append((elem_name, content))
        return items

    @property
    def package_name(self):
        data = dict(self.parse_article_meta)
        data_labels = data.keys()
        labels = ['volume', 'issue', 'fpage', 'lpage', 'elocation']
        if 'volume' not in data_labels and 'issue' not in data_labels:
            if 'doi' in data_labels:
                data.update({'type': 'ahead'})
                labels.append('type')
                labels.append('year')
                labels.append('doi')
            elif 'other' in data_labels:
                data.update({'type': 'ahead'})
                labels.append('type')
                labels.append('year')
                labels.append('other')
        elif 'fpage' not in data_labels and 'lpage' not in data_labels and \
                'elocation' not in data_labels and 'doi' not in data_labels:
            labels.append('other')
        items = [self.issn, self.acron]
        items += [data[k] for k in labels if k in data_labels]
        return '-'.join([item for item in items if item]) or \
               self.prefix_asset_name

    def asset_name(self, img_filename):
        filename, ext = os.path.splitext(self.prefix_asset_name)
        suffix = img_filename
        if img_filename.startswith(filename):
            suffix = img_filename[len(filename):]
        return '-g'.join([self.package_name, suffix])

    @property
    def elements_which_has_xlink_href(self):
        paths = [
            ".//ext-link[@xlink:href]",
            ".//graphic[@xlink:href]",
            ".//inline-graphic[@xlink:href]",
            ".//inline-supplementary-material[@xlink:href]",
            ".//media[@xlink:href]",
            ".//supplementary-material[@xlink:href]",
        ]
        iterators = [
            self.xmltree.iterfind(
                path, namespaces={"xlink": "http://www.w3.org/1999/xlink"})
            for path in paths
        ]
        return itertools.chain(*iterators)

    def replace_assets_names(self):
        replacements = []
        attr_name = '{http://www.w3.org/1999/xlink}href'
        for node in self.elements_which_has_xlink_href:
            old_path = node.get(attr_name)
            if is_asset_href(old_path):
                f_name, ext = files.extract_filename_ext_by_path(old_path)
                new_fname = self.asset_name(f_name)
                node.set(attr_name, "%s%s" % (new_fname, ext))
                replacements.append((old_path, new_fname))
        return replacements
