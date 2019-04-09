import unittest

from lxml import etree

from documentstore_migracao.export.sps_package import (
    parse_value,
    parse_issue,
    SPS_Package,
)


def build_xml(article_meta_children_xml):
    return """
        <article>
        <front>
        <journal-meta>
            <journal-id journal-id-type="publisher-id">acron</journal-id>
            <issn pub-type="epub">1234-5678</issn>
            <issn pub-type="ppub">0123-4567</issn>
        </journal-meta>
        <article-meta>
            <article-id article-id-type="doi">10.1590/S0123-45672018050</article-id>
            {article_meta_children_xml}
        </article-meta>
        </front>
        </article>
        """.format(
                article_meta_children_xml=article_meta_children_xml
            )


def sps_package(article_meta_xml):
    xml = build_xml(article_meta_xml)
    xmltree = etree.fromstring(xml)
    return SPS_Package(xmltree)


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


class Test_SPS_Package_VolNumFpage(unittest.TestCase):

    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>5</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '05'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-05-fpage'
        )


class Test_SPS_Package_VolFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
           ]
        )

    def test_package_name_vol_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-fpage'
        )


class Test_SPS_Package_NumFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<issue>5</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_num_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('issue', '05'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-05-fpage'
        )


class Test_SPS_Package_VolNumSpeFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>5 spe</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_spe_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '05-spe'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_num_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-05-spe-fpage'
        )


class Test_SPS_Package_VolSpeNumFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>spe num</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_spe_num_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 'spenum'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_spe_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-spenum-fpage'
        )


class Test_SPS_Package_VolSpeFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>Especial</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_spe_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 'spe'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-spe-fpage'
        )


class Test_SPS_Package_VolSuplFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>Suplemento</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 's0'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-s0-fpage'
        )


class Test_SPS_Package_VolSuplAFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>Suplemento A</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', 'sa'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-sa-fpage'
        )


class Test_SPS_Package_VolNumSuplFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>2 Suplemento</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '02-s0'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_num_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-02-s0-fpage'
        )


class Test_SPS_Package_Vol2SuplAFpage(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <issue>2 Suplemento A</issue>
            <fpage>fpage</fpage>
            <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_num_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('volume', 'volume'),
                ('issue', '02-sa'),
                ('fpage', 'fpage'),
                ('year', '2010'),
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_num_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-02-sa-fpage'
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
                ('doi', 'S0123-45672018050'),
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
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_vol_continuous_publication(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-volume-elocation'
        )


class Test_SPS_Package_Aop(unittest.TestCase):
    def setUp(self):
        self.sps_package = sps_package("")

    def test_parse_article_meta_aop(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ('doi', 'S0123-45672018050'),
            ]
        )

    def test_package_name_aop(self):
        self.assertEqual(
            self.sps_package.package_name,
            '1234-5678-acron-S0123-45672018050'
        )
