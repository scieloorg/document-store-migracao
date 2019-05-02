import unittest

from lxml import etree

from documentstore_migracao.export.sps_package import (
    parse_value,
    parse_issue,
    SPS_Package,
    sort_documents,
)


def build_xml(article_meta_children_xml, doi,
                      journal_meta="", article_ids="", pub_date=""):
    default_journal_meta = """
        <journal-id journal-id-type="publisher-id">acron</journal-id>
                <issn pub-type="epub">1234-5678</issn>
                <issn pub-type="ppub">0123-4567</issn>
        """
    default_article_ids = """
        <article-id pub-id-type="publisher-id">S0074-02761962000200006</article-id>
        <article-id pub-id-type="other">00006</article-id>
    """
    default_pubdate = """
        <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>
    """
    doi_elem = ''
    if doi:
        doi_elem = '<article-id pub-id-type="doi">{}</article-id>'.format(
                doi
            )
    return """
        <article xmlns:xlink="http://www.w3.org/1999/xlink">
        <front>
        <journal-meta>
            {journal_meta}
        </journal-meta>
        <article-meta>
            {article_meta_doi}
            {article_ids}
            {article_meta_children_xml}
            {pub_date}
        </article-meta>
        </front>
        </article>
        """.format(
                article_meta_children_xml=article_meta_children_xml,
                article_meta_doi=doi_elem,
                article_ids=article_ids or default_article_ids,
                journal_meta=journal_meta or default_journal_meta,
                pub_date=pub_date or default_pubdate
            )


def pubdate_xml(year, month, day):
    LABELS = ['year', 'month', 'day']
    values = [year, month, day]
    xml = ''.join(
        [('<{}>'.format(label) + str(values[n]) + '</{}>'.format(label))
         for n, label in enumerate(LABELS)
         ])
    return """<pub-date date-type="collection">{}</pub-date>""".format(
        xml)


def sps_package(article_meta_xml, doi='10.1590/S0074-02761962000200006'):
    xml = build_xml(article_meta_xml, doi)
    xmltree = etree.fromstring(xml)
    return SPS_Package(xmltree, 'a01')


class Test_MatchPubDate1(unittest.TestCase):
    def setUp(self):
        xml = """<article><article-meta>
            <pub-date date-type="pub">
                <year>2010</year><month>5</month><day>13</day></pub-date>
            <pub-date date-type="collection">
                <year>2012</year><month>2</month><day>3</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__match_pubdate(self):
        result = self.sps_package._match_pubdate(
                    ('pub-date[@date-type="pub"]',
                     'pub-date[@date-type="collection"]'))
        self.assertEqual(
                result.findtext('year'), '2010'
            )

    def test_document_pubdate(self):
        self.assertEqual(
                self.sps_package.document_pubdate, ('2010', '05', '13')
            )

    def test_documents_bundle_pubdate(self):
        self.assertEqual(
                self.sps_package.documents_bundle_pubdate, ('2012', '02', '03')
            )


class Test_MatchPubDate2(unittest.TestCase):
    def setUp(self):
        xml = """<article><article-meta>
            <pub-date pub-type="epub">
                <year>2010</year><month>4</month><day>1</day></pub-date>
            <pub-date pub-type="collection">
                <year>2012</year></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__match_pubdate(self):
        result = self.sps_package._match_pubdate(
                    ('pub-date[@pub-type="epub"]',
                     'pub-date[@pub-type="collection"]'))
        self.assertEqual(
                result.findtext('year'), '2010'
            )

    def test_document_pubdate(self):
        self.assertEqual(
                self.sps_package.document_pubdate, ('2010', '04', '01')
            )

    def test_documents_bundle_pubdate(self):
        self.assertEqual(
                self.sps_package.documents_bundle_pubdate, ('2012', '', '')
            )


class Test_MatchPubDate3(unittest.TestCase):
    def setUp(self):
        xml = """<article><article-meta>
            <pub-date pub-type="epub">
                <year>2010</year><month>9</month><day>10</day></pub-date>
            <pub-date pub-type="epub-ppub">
                <year>2011</year></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__match_pubdate(self):
        result = self.sps_package._match_pubdate(
                    ('pub-date[@pub-type="collection"]',
                     'pub-date[@pub-type="epub-ppub"]'))
        self.assertEqual(
                result.findtext('year'), '2011'
            )

    def test_document_pubdate(self):
        self.assertEqual(
                self.sps_package.document_pubdate, ('2010', '09', '10')
            )

    def test_documents_bundle_pubdate(self):
        self.assertEqual(
                self.sps_package.documents_bundle_pubdate, ('2011', '', '')
            )


class Test_MatchPubDate4(unittest.TestCase):
    def setUp(self):
        xml = """<article><article-meta>
            <pub-date date-type="pub">
                <year>2010</year><month>9</month><day>1</day></pub-date>
            <pub-date date-type="epub-ppub">
                <year>2011</year></pub-date>
            <pub-date date-type="collection">
                <year>2012</year><month>2</month></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__match_pubdate(self):
        result = self.sps_package._match_pubdate(
                    ('pub-date[@date-type="pub"]',
                     'pub-date[@date-type="collection"]'))
        self.assertEqual(
                result.findtext('year'), '2010'
            )

    def test_document_pubdate(self):
        self.assertEqual(
                self.sps_package.document_pubdate, ('2010', '09', '01')
            )

    def test_documents_bundle_pubdate(self):
        self.assertEqual(
                self.sps_package.documents_bundle_pubdate, ('2012', '02', '')
            )


class Test_sps_package(unittest.TestCase):

    def test_parse_value_num(self):
        self.assertEqual(parse_value('3'), '03')

    def test_parse_value_num_spe(self):
        self.assertEqual(parse_value('Especial'), 'spe')

    def test_parse_value_suppl(self):
        self.assertEqual(parse_value('Supplement'), 's')

    def test_parse_issue_num_suppl(self):
        self.assertEqual(parse_issue('3 Supl'), '03-s0')

    def test_parse_issue_num_spe_(self):
        self.assertEqual(parse_issue('4 Especial'), '04-spe')

    def test_parse_issue_num_suppl_label(self):
        self.assertEqual(parse_issue('3 Supl A'), '03-sa')

    def test_parse_issue_num_spe_num(self):
        self.assertEqual(parse_issue('4 Especial 1'), '04-spe01')

    def test_parse_issue_suppl_label(self):
        self.assertEqual(parse_issue('Supl A'), 'sa')

    def test_parse_issue_spe_num(self):
        self.assertEqual(parse_issue('Especial 1'), 'spe01')


class Test_SPS_Package(unittest.TestCase):

    def setUp(self):
        article_xml = """<root xmlns:xlink="http://www.w3.org/1999/xlink">
                <inline-graphic xlink:href="a01tab01.gif"/>
                <graphic xlink:href="a01f01.gif"/>
                <ext-link xlink:href="a01tab02.gif"/>
                <ext-link xlink:href="mailto:a01f02.gif"/>
                <inline-supplementary-material xlink:href="a01tab03.gif"/>
                <supplementary-material xlink:href="a01tab04.gif"/>
                <media xlink:href="a01tab04.gif"/>
            </root>
            """
        self.sps_package = SPS_Package(
            etree.fromstring(article_xml), 'a01')

    def test_elements_which_has_xlink_href(self):
        items = list(self.sps_package.elements_which_has_xlink_href)
        self.assertEqual(len(items), 7)
        self.assertEqual(
            [node.tag for node in items],
            sorted(
                ['inline-graphic', 'graphic', 'ext-link', 'ext-link',
                 'inline-supplementary-material', 'supplementary-material',
                 'media']))

    def test_replace_assets(self):
        expected = [
            ('a01tab02.gif', 'a01-gtab02'),
            ('a01f01.gif', 'a01-gf01'),
            ('a01tab01.gif', 'a01-gtab01'),
            ('a01tab03.gif', 'a01-gtab03'),
            ('a01tab04.gif', 'a01-gtab04'),
            ('a01tab04.gif', 'a01-gtab04'),
        ]
        items = self.sps_package.replace_assets_names()
        self.assertEqual(len(items), 6)
        for i, item in enumerate(items):
            with self.subTest(i):
                self.assertEqual(expected[i][0], item[0])
                self.assertEqual(expected[i][1], item[1])


class Test_SPS_Package_No_Metadata(unittest.TestCase):

    def setUp(self):
        article_xml = """<root xmlns:xlink="http://www.w3.org/1999/xlink">
                <inline-graphic xlink:href="a01tab01.gif"/>
                <graphic xlink:href="a01f01.gif"/>
                <ext-link xlink:href="a01tab02.gif"/>
                <ext-link xlink:href="mailto:a01f02.gif"/>
                <inline-supplementary-material xlink:href="a01tab03.gif"/>
                <supplementary-material xlink:href="a01tab04.gif"/>
                <media xlink:href="a01tab04.gif"/>
            </root>
            """
        self.sps_package = SPS_Package(
            etree.fromstring(article_xml), 'a01')

    def test_parse_article(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            []
        )

    def test_package_name(self):
        self.assertEqual(
            self.sps_package.package_name,
            'a01'
        )

    def test_asset_package_name_f01(self):
        self.assertEqual(
            self.sps_package.asset_name('a01f01.jpg'),
            'a01-gf01.jpg'
        )

    def test_asset_package_name_any_img(self):
        self.assertEqual(
            self.sps_package.asset_name('img.jpg'),
            'a01-gimg.jpg'
        )

    def test_journal_meta(self):
        self.assertEqual(self.sps_package.journal_meta, [])

    def test_parse_article_meta(self):
        self.assertEqual(self.sps_package.parse_article_meta, [])


class Test_SPS_Package_VolNumFpageLpage(unittest.TestCase):

    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>5</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '05'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, None)

    def test_number(self):
        self.assertEqual(self.sps_package.number, '05')

    def test_package_name_vol_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-05-fpage-lpage'
        )

    def test_asset_package_name_f01(self):
        self.assertEqual(
            self.sps_package.asset_name('a01f01.jpg'),
            '1234-5678-acron-volume-05-fpage-lpage-gf01.jpg'
        )

    def test_asset_package_name_any_img(self):
        self.assertEqual(
            self.sps_package.asset_name('img.jpg'),
            '1234-5678-acron-volume-05-fpage-lpage-gimg.jpg'
        )

    def test_journal_meta(self):
        self.assertEqual(
            self.sps_package.journal_meta,
            [
                ('eissn', '1234-5678'),
                ('pissn', '0123-4567'),
                ('issn', '1234-5678'),
                ('acron', 'acron'),
            ]
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_vol_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_NumFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<issue>5</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_num_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('issue', '05'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-05-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolNumSpeFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>5 spe</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_spe_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '05-spe'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, None)

    def test_number(self):
        self.assertEqual(self.sps_package.number, '05-spe')

    def test_package_name_vol_num_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-05-spe-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolSpeNumFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>spe num</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_spe_num_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 'spenum'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_vol_spe_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-spenum-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolSpeFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>Especial</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_spe_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 'spe'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_vol_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-spe-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolSuplFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>Suplemento</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 's0'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, '0')

    def test_number(self):
        self.assertIsNone(self.sps_package.number)

    def test_package_name_vol_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-s0-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolSuplAFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>Suplemento A</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 'sa'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, 'a')

    def test_number(self):
        self.assertIsNone(self.sps_package.number)

    def test_package_name_vol_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-sa-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_VolNumSuplFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>2 Suplemento</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '02-s0'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, '0')

    def test_number(self):
        self.assertEqual(self.sps_package.number, '02')

    def test_package_name_vol_num_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-02-s0-fpage-lpage'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_Vol2SuplAFpageLpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>2 Suplemento A</issue>
            <fpage>fpage</fpage>
            <lpage>lpage</lpage>
            """
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '02-sa'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_vol_num_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-02-sa-fpage-lpage'
        )

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id,
            '1234-5678-acron-2010-volume-02-sa'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', 'fpage'),
                ('lpage', 'lpage'),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', 'fpage', 'lpage', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_Vol5Elocation(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>5</issue>
            <elocation-id>elocation</elocation-id>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_continuous_publication(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '05'),
                ('elocation-id', 'elocation'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_vol_num_continuous_publication(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-05-elocation'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            True
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', ''),
                ('lpage', ''),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', 'elocation'),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', '', '', ('2010', '', ''), ('2010', '', ''), 'elocation')
            )


class Test_SPS_Package_VolElocation(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <elocation-id>elocation</elocation-id>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_continuous_publication(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('elocation-id', 'elocation'),
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_vol_continuous_publication(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-elocation'
        )

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id,
            '1234-5678-acron-2010-volume'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            True
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', ''),
                ('lpage', ''),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', 'elocation'),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', '', '', ('2010', '', ''), ('2010', '', ''), 'elocation')
            )


class Test_SPS_Package_Aop_HTML(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<fpage>0</fpage>
            <lpage>00</lpage>"""
        self.sps_package = sps_package(article_meta_xml, doi="")

    def test_parse_article_meta_aop(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('year', '2010'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_package_name_aop(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-ahead-2010-00006'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            True
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', ''),
                ('lpage', ''),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', '', '', ('2010', '', ''), ('2010', '', ''), '')
            )


class Test_SPS_Package_Aop_XML(unittest.TestCase):
    def setUp(self):
        self.sps_package = sps_package("")

    def test_parse_article_meta_aop(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('year', '2010'),
                ('doi', 'S0074-02761962000200006'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),

            ]
        )

    def test_package_name_aop(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-ahead-2010-S0074-02761962000200006'
        )

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id,
            '1234-5678-acron-aop'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            True
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', ''),
                ('lpage', ''),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', '', '', ('2010', '', ''), ('2010', '', ''), '')
        )


class Test_SPS_Package_Article_HTML(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>20</volume><fpage>0</fpage>
            <lpage>00</lpage>"""
        self.sps_package = sps_package(article_meta_xml, doi="")

    def test_parse_article_meta(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', '20'),
                ('year', '2010'),
                ('publisher-id', 'S0074-02761962000200006'),
                ('other', '00006'),
            ]
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, None)

    def test_number(self):
        self.assertEqual(self.sps_package.number, None)

    def test_package_name(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-20-00006'
        )

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id,
            '1234-5678-acron-2010-20'
        )

    def test_is_only_online_publication(self):
        self.assertEqual(
            self.sps_package.is_only_online_publication,
            False
        )

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ('other', '00006'),
                ('fpage', ''),
                ('lpage', ''),
                ('documents_bundle_pubdate', ('2010', '', '')),
                ('document_pubdate', ('2010', '', '')),
                ('elocation-id', ''),
            )
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ('00006', '', '', ('2010', '', ''), ('2010', '', ''), '')
        )


class Test_DocumentsSort_Pages(unittest.TestCase):

    def XML(self, fpage, lpage):
        _xml = """<volume>volume</volume><issue>5</issue>
            <fpage>{}</fpage><lpage>{}</lpage>
            """.format(fpage, lpage)
        return etree.fromstring(build_xml(_xml, ''))

    def test_sort_documents_volume_issue_pages(self):
        expected = {
            '1234-5678-acron-2010-volume-05':
                [
                    '/documents/kaksjao',
                    '/documents/xyz',
                    '/documents/www',
                    '/documents/abc',
                ],
        }
        xmls = (
            self.XML('110', '113'),
            self.XML('101', '103'),
            self.XML('108', '109'),
            self.XML('90', '97'),
        )
        location_at_kernel = (
            '/documents/abc',
            '/documents/xyz',
            '/documents/www',
            '/documents/kaksjao',
        )
        data = [(k, v) for k, v in zip(location_at_kernel, xmls)]
        result = sort_documents(data)
        self.assertEqual(
            result['1234-5678-acron-2010-volume-05']['items'],
            expected['1234-5678-acron-2010-volume-05']
        )
        expected_data = {
            'eissn': '1234-5678',
            'pissn': '0123-4567',
            'issn': '1234-5678',
            'acron': 'acron',
            'year': '2010',
            'volume': 'volume',
            'number': '05',
            'supplement': None,
        }
        self.assertEqual(
            result['1234-5678-acron-2010-volume-05']['data'], expected_data)


class Test_DocumentsSort_PagesAndOther(unittest.TestCase):

    def XML(self, other, fpage, lpage):
        _xml = """
            <article-id pub-id-type="other">{}</article-id>
            <volume>volume</volume><issue>5</issue>
            <fpage>{}</fpage><lpage>{}</lpage>
            """.format(other, fpage, lpage)
        return etree.fromstring(build_xml(_xml, ''))

    def test_sort_documents_volume_issue_pages_and_other(self):
        xmls = (
            self.XML('1', 'v', 'vii'),
            self.XML('2', '', ''),
            self.XML('5', '108', '109'),
            self.XML('3', '90', '97'),
        )
        location_at_kernel = (
            '/documents/abc',
            '/documents/xyz',
            '/documents/www',
            '/documents/kaksjao',
        )
        expected = {
            '1234-5678-acron-2010-volume-05':
                [
                    '/documents/abc',
                    '/documents/xyz',
                    '/documents/kaksjao',
                    '/documents/www',
                ],
        }
        data = [(k, v) for k, v in zip(location_at_kernel, xmls)]
        result = sort_documents(data)
        self.assertEqual(
            result['1234-5678-acron-2010-volume-05']['items'],
            expected['1234-5678-acron-2010-volume-05']
        )
        expected_data = {
            'eissn': '1234-5678',
            'pissn': '0123-4567',
            'issn': '1234-5678',
            'acron': 'acron',
            'year': '2010',
            'volume': 'volume',
            'number': '05',
            'supplement': None,
        }
        self.assertEqual(
            result['1234-5678-acron-2010-volume-05']['data'], expected_data)


class Test_DocumentsSort_ContinuousPublication(unittest.TestCase):

    def XML(self, volume, elocation, year, month, day):
        article_meta_xml = """
            <volume>{}</volume>
            <elocation-id>{}</elocation-id>""".format(volume, elocation)

        return etree.fromstring(
            build_xml(
                article_meta_xml, '', pub_date=pubdate_xml(year, month, day))
            )

    def test_sort_documents_continous_publication(self):
        xmls = (
            self.XML('30', 'e1234', 2011, 5, 10),
            self.XML('30', 'e1235', 2012, 5, 10),
            self.XML('30', 'e1236', 2010, 4, 10),
            self.XML('30', 'e1237', 2011, 5, 10),
            self.XML('30', 'e1238', 2011, 5, 9),
            self.XML('30', 'e1239', 2012, 5, 8),
            self.XML('30', 'e1240', 2010, 5, 15),
            self.XML('30', 'e1241', 2011, 5, 10),
        )
        location_at_kernel = (
            '/documents/abc_2011_05_10_4',
            '/documents/xyz_2012_05_10_5',
            '/documents/www_2010_04_10_6',
            '/documents/kas_2011_05_10_7',
            '/documents/abc_2011_05_09_8',
            '/documents/xyz_2012_05_08_9',
            '/documents/www_2010_05_15_10',
            '/documents/kak_2011_05_10_11',
        )
        expected = {
            '1234-5678-acron-2010-30':
                [
                    '/documents/www_2010_05_15_10',
                    '/documents/www_2010_04_10_6',
                 ],
            '1234-5678-acron-2011-30':
                [
                    '/documents/kak_2011_05_10_11',
                    '/documents/kas_2011_05_10_7',
                    '/documents/abc_2011_05_10_4',
                    '/documents/abc_2011_05_09_8',
                ],
            '1234-5678-acron-2012-30':
                [
                    '/documents/xyz_2012_05_10_5',
                    '/documents/xyz_2012_05_08_9',
                ],
        }
        data = [(k, v) for k, v in zip(location_at_kernel, xmls)]
        result = sort_documents(data)
        for i, item in enumerate(result['1234-5678-acron-2010-30']['items']):
            with self.subTest(i):
                self.assertEqual(
                    item,
                    expected['1234-5678-acron-2010-30'][i]
                )
        for i, item in enumerate(result['1234-5678-acron-2011-30']['items']):
            with self.subTest(i):
                self.assertEqual(
                    item,
                    expected['1234-5678-acron-2011-30'][i]
                )
        for i, item in enumerate(result['1234-5678-acron-2012-30']['items']):
            with self.subTest(i):
                self.assertEqual(
                    item,
                    expected['1234-5678-acron-2012-30'][i]
                )


class Test_DocumentsSort_Pages_Other_and_ArticlePubDate(unittest.TestCase):

    def XML(self, other, fpage, lpage, year=None, month=None, day=None):
        _xml = """
            <article-id pub-id-type="other">{}</article-id>
            <volume>volume</volume><issue>5</issue>
            <fpage>{}</fpage><lpage>{}</lpage>
            """.format(other, fpage, lpage)
        _pubdate = ''
        if any([year, month, day]):
            _pubdate = pubdate_xml(year, month, day)
        return etree.fromstring(
                    build_xml(
                        _xml, '', pub_date=_pubdate))

    def test_sort_documents_volume_issue_pages_and_other(self):
        xmls = (
            self.XML('1', 'v', 'vii', 2010, 1, 1),
            self.XML('2', '', ''),
            self.XML('5', '108', '109', 2010, 1, 2),
            self.XML('3', '90', '97'),
        )
        location_at_kernel = (
            '/documents/abc',
            '/documents/xyz',
            '/documents/www',
            '/documents/kaksjao',
        )
        expected = {
            '1234-5678-acron-2010-volume-05':
                [
                    '/documents/abc',
                    '/documents/xyz',
                    '/documents/kaksjao',
                    '/documents/www',
                ],
        }
        data = [(k, v) for k, v in zip(location_at_kernel, xmls)]
        result = sort_documents(data)
        self.assertEqual(
            result['1234-5678-acron-2010-volume-05']['items'],
            expected['1234-5678-acron-2010-volume-05']
        )
        expected_data = {
            'eissn': '1234-5678',
            'pissn': '0123-4567',
            'issn': '1234-5678',
            'acron': 'acron',
            'year': '2010',
            'volume': 'volume',
            'number': '05',
            'supplement': None,
        }
        self.assertEqual(
            result['1234-5678-acron-2010-volume-05']['data'], expected_data)


class Test_DocumentsSort_AOP(unittest.TestCase):

    def XML(self, elocation, year, month, day):
        article_meta_xml = """
            <elocation-id>{}</elocation-id>""".format(elocation)

        return etree.fromstring(
            build_xml(
                article_meta_xml, '', pub_date=pubdate_xml(year, month, day))
            )

    def test_sort_documents_aop(self):

        xmls = (
            self.XML('e1234', 2011, 5, 10),
            self.XML('e1235', 2012, 5, 10),
            self.XML('e1236', 2010, 4, 10),
            self.XML('e1237', 2011, 5, 10),
            self.XML('e1238', 2011, 5, 9),
            self.XML('e1239', 2012, 5, 8),
            self.XML('e1240', 2010, 5, 15),
            self.XML('e1241', 2011, 5, 10),
        )
        location_at_kernel = (
            '/documents/abc_2011_05_10_4',
            '/documents/xyz_2012_05_10_5',
            '/documents/www_2010_04_10_6',
            '/documents/kas_2011_05_10_7',
            '/documents/abc_2011_05_09_8',
            '/documents/xyz_2012_05_08_9',
            '/documents/www_2010_05_15_10',
            '/documents/kak_2011_05_10_11',
        )
        expected = {
            '1234-5678-acron-aop':
                [
                    '/documents/xyz_2012_05_10_5',
                    '/documents/xyz_2012_05_08_9',
                    '/documents/kak_2011_05_10_11',
                    '/documents/kas_2011_05_10_7',
                    '/documents/abc_2011_05_10_4',
                    '/documents/abc_2011_05_09_8',
                    '/documents/www_2010_05_15_10',
                    '/documents/www_2010_04_10_6',
                ],
        }

        data = [(k, v) for k, v in zip(location_at_kernel, xmls)]
        result = sort_documents(data)
        for i, item in enumerate(result['1234-5678-acron-aop']['items']):
            with self.subTest(i):
                self.assertEqual(
                    item,
                    expected['1234-5678-acron-aop'][i]
                )


class Test_DocumentsSort_MoreThanOneBundle(unittest.TestCase):

    def XML(self, volume, elocation, year, month, day):
        article_meta_xml = """
            <volume>{}</volume>
            <elocation-id>{}</elocation-id>""".format(volume, elocation)

        return etree.fromstring(
            build_xml(
                article_meta_xml, '', pub_date=pubdate_xml(year, month, day))
            )

    def test_sort_documents_some_docs_bundles(self):

        xmls = (
            self.XML('32', 'e1234', 2011, 5, 10),
            self.XML('32', 'e1235', 2012, 5, 10),
            self.XML('32', 'e1236', 2010, 4, 10),
            self.XML('32', 'e1237', 2011, 5, 10),
            self.XML('30', 'e1238', 2011, 5, 9),
            self.XML('30', 'e1239', 2012, 5, 8),
            self.XML('30', 'e1240', 2010, 5, 15),
            self.XML('30', 'e1241', 2011, 5, 10),
        )
        location_at_kernel = (
            '/documents/abc_2011_05_10_4',
            '/documents/xyz_2012_05_10_5',
            '/documents/www_2010_04_10_6',
            '/documents/kas_2011_05_10_7',

            '/documents/abc_2011_05_09_8',
            '/documents/xyz_2012_05_08_9',
            '/documents/www_2010_05_15_10',
            '/documents/kak_2011_05_10_11',
        )
        expected = {
            '1234-5678-acron-2012-32':
                [
                    '/documents/xyz_2012_05_10_5'
                ],
            '1234-5678-acron-2011-32':
                [
                    '/documents/kas_2011_05_10_7',
                    '/documents/abc_2011_05_10_4'
                ],
            '1234-5678-acron-2010-32':
                [
                    '/documents/www_2010_04_10_6'
                ],
            '1234-5678-acron-2012-30':
                [
                    '/documents/xyz_2012_05_08_9'
                ],
            '1234-5678-acron-2011-30':
                [
                    '/documents/kak_2011_05_10_11',
                    '/documents/abc_2011_05_09_8'
                ],
            '1234-5678-acron-2010-30':
                [
                    '/documents/www_2010_05_15_10'
                ],
        }

        data = [(k, v) for k, v in zip(location_at_kernel, xmls)]
        result = sort_documents(data)
        for docs_bundle_id in expected.keys():
            for i, location in enumerate(result[docs_bundle_id]['items']):
                with self.subTest((docs_bundle_id, i)):
                    self.assertEqual(
                        location,
                        expected[docs_bundle_id][i]
                    )

