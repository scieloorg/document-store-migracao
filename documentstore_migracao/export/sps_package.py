import os


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


class SPS_Package:

    def __init__(self, xmltree):
        self.xmltree = xmltree

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
        return '-'.join(items)

    def asset_package_name(self, original_document_filename, img_filename):
        filename, ext = os.path.splitext(original_document_filename)
        suffix = img_filename
        if img_filename.startswith(filename):
            suffix = img_filename[len(filename):]
        return '-g'.join([self.package_name, suffix])


