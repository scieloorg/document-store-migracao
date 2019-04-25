import unittest

from lxml import etree

from documentstore_migracao.export.sps_package import (
    parse_value,
    parse_issue,
    SPS_Package,
)


def build_xml(article_meta_children_xml, doi):
    doi_elem = ''
    if doi:
        doi_elem = '<article-id pub-id-type="doi">{}</article-id>'.format(
                doi
            )
    return """
        <article xmlns:xlink="http://www.w3.org/1999/xlink">
        <front>
        <journal-meta>
            <journal-id journal-id-type="publisher-id">acron</journal-id>
            <issn pub-type="epub">1234-5678</issn>
            <issn pub-type="ppub">0123-4567</issn>
        </journal-meta>
        <article-meta>
            {article_meta_doi}
            <article-id pub-id-type="publisher-id">S0074-02761962000200006</article-id>
            <article-id pub-id-type="other">00006</article-id>
           {article_meta_children_xml}
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>
        </article-meta>
        </front>
        </article>
        """.format(
                article_meta_children_xml=article_meta_children_xml,
                article_meta_doi=doi_elem
            )


def sps_package(article_meta_xml, doi='10.1590/S0074-02761962000200006'):
    xml = build_xml(article_meta_xml, doi)
    xmltree = etree.fromstring(xml)
    return SPS_Package(xmltree, 'a01')


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

    def test_package_name_vol_num_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-05-spe-fpage-lpage'
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

    def test_package_name_vol_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-s0-fpage-lpage'
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

    def test_package_name_vol_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-sa-fpage-lpage'
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

    def test_package_name_vol_num_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-02-s0-fpage-lpage'
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


class Test_SPS_Package_Vol5Elocation(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>5</issue>
            <elocation>elocation</elocation>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_continuous_publication(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '05'),
                ('elocation', 'elocation'),
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


class Test_SPS_Package_VolElocation(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <elocation>elocation</elocation>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_continuous_publication(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('elocation', 'elocation'),
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

    def test_package_name(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-20-00006'
        )
