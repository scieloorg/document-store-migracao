
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


def parse_pub_date(issue):
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
                        elem_name = node.get('article-id-type')
                        if elem_name == 'doi':
                            if '/' in content:
                                content = content[content.find('/')+1:]
                    if node.tag == 'issue':
                        content = parse_issue(content)
                    elif node.tag == 'pub-date':
                        content = node.findtext('year')
                        elem_name = 'year'
                    items.append((elem_name, content))
        return items

    @property
    def package_name(self):
        data = dict(self.parse_article_meta)
        labels = ['volume', 'issue', 'fpage', 'lpage', 'elocation']
        if 'volume' not in data.keys() and 'issue' not in data.keys():
            labels += ['doi', 'other']
        items = [self.issn, self.acron]
        items += [data[k] for k in labels if k in data.keys()]
        return '-'.join(items)
