import unittest
from unittest import mock

from lxml import etree

from . import utils
from documentstore_migracao.export.sps_package import (
    parse_value,
    parse_issue,
    SPS_Package
)


def pubdate_xml(year, month, day):
    LABELS = ["year", "month", "day"]
    values = [year, month, day]
    xml = "".join(
        [
            ("<{}>".format(label) + str(values[n]) + "</{}>".format(label))
            for n, label in enumerate(LABELS)
        ]
    )
    return """<pub-date date-type="collection">{}</pub-date>""".format(xml)


def sps_package(article_meta_xml, doi="10.1590/S0074-02761962000200006"):
    xml = utils.build_xml(article_meta_xml, doi)
    xmltree = etree.fromstring(xml)
    return SPS_Package(xmltree, "a01")


class Test_MatchPubDate1(unittest.TestCase):
    def setUp(self):
        self.xml = """<article><article-meta>
            <pub-date date-type="pub">
                <year>2010</year><month>5</month><day>13</day></pub-date>
            <pub-date date-type="collection">
                <year>2012</year><month>2</month><day>3</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__match_pubdate(self):
        result = self.sps_package._match_pubdate(
            ('pub-date[@date-type="pub"]', 'pub-date[@date-type="collection"]')
        )
        self.assertEqual(result.findtext("year"), "2010")

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "05", "13"))

    def test_documents_bundle_pubdate(self):
        self.assertEqual(
            self.sps_package.documents_bundle_pubdate, ("2012", "02", "03")
        )

    def test_transform_pubdate(self):
        self.sps_package.transform_pubdate()
        xpaths_results = (
            ('pub-date[@date-type="pub"]', ("2010", "5", "13")),
            ('pub-date[@date-type="collection"]', ("2012", "2", "3")),
        )
        for xpath, result in xpaths_results:
            with self.subTest(xpath=xpath, result=result):
                pubdate = self.sps_package.article_meta.find(xpath)
                self.assertIsNotNone(pubdate)
                self.assertEqual(pubdate.get("publication-format"), "electronic")
                self.assertEqual(pubdate.findtext("year"), result[0])
                self.assertEqual(pubdate.findtext("month"), result[1])
                self.assertEqual(pubdate.findtext("day"), result[2])


class Test_MatchPubDate1_Season(unittest.TestCase):
    def setUp(self):
        xml = """<article><article-meta>
            <pub-date date-type="pub">
                <year>2010</year><month>5</month><day>13</day></pub-date>
            <pub-date date-type="collection">
                <year>2012</year><season>Jan-Feb</season></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__match_pubdate(self):
        result = self.sps_package._match_pubdate(
            ('pub-date[@date-type="pub"]', 'pub-date[@date-type="collection"]')
        )
        self.assertEqual(result.findtext("year"), "2010")

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "05", "13"))

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "", ""))

    def test_transform_pubdate(self):
        self.sps_package.transform_pubdate()
        pubdate = self.sps_package.article_meta.find('pub-date[@date-type="pub"]')
        self.assertIsNotNone(pubdate)
        self.assertEqual(pubdate.get("publication-format"), "electronic")
        self.assertEqual(pubdate.findtext("year"), "2010")
        self.assertEqual(pubdate.findtext("month"), "5")
        self.assertEqual(pubdate.findtext("day"), "13")
        pubdate = self.sps_package.article_meta.find(
            'pub-date[@date-type="collection"]'
        )
        self.assertIsNotNone(pubdate)
        self.assertEqual(pubdate.get("publication-format"), "electronic")
        self.assertEqual(pubdate.findtext("year"), "2012")
        self.assertEqual(pubdate.findtext("season"), "Jan-Feb")


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
            ('pub-date[@pub-type="epub"]', 'pub-date[@pub-type="collection"]')
        )
        self.assertEqual(result.findtext("year"), "2010")

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "04", "01"))

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "", ""))

    def test_transform_pubdate(self):
        self.sps_package.transform_pubdate()
        xpaths_results = (
            ('pub-date[@date-type="pub"]', ("2010", "4", "1")),
            ('pub-date[@date-type="collection"]', ("2012", None, None)),
        )
        for xpath, result in xpaths_results:
            with self.subTest(xpath=xpath, result=result):
                pubdate = self.sps_package.article_meta.find(xpath)
                self.assertIsNotNone(pubdate)
                self.assertIsNone(pubdate.attrib.get("pub-type"))
                self.assertEqual(pubdate.get("publication-format"), "electronic")
                self.assertEqual(pubdate.findtext("year"), result[0])
                self.assertEqual(pubdate.findtext("month"), result[1])
                self.assertEqual(pubdate.findtext("day"), result[2])


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
            ('pub-date[@pub-type="collection"]', 'pub-date[@pub-type="epub-ppub"]')
        )
        self.assertEqual(result.findtext("year"), "2011")

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "09", "10"))

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2011", "", ""))

    def test_transform_pubdate(self):
        self.sps_package.transform_pubdate()
        xpaths_results = (
            ('pub-date[@date-type="pub"]', ("2010", "9", "10")),
            ('pub-date[@date-type="collection"]', ("2011", None, None)),
        )
        for xpath, result in xpaths_results:
            with self.subTest(xpath=xpath, result=result):
                pubdate = self.sps_package.article_meta.find(xpath)
                self.assertIsNotNone(pubdate)
                self.assertIsNone(pubdate.attrib.get("pub-type"))
                self.assertEqual(pubdate.get("publication-format"), "electronic")
                self.assertEqual(pubdate.findtext("year"), result[0])
                self.assertEqual(pubdate.findtext("month"), result[1])
                self.assertEqual(pubdate.findtext("day"), result[2])


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
            ('pub-date[@date-type="pub"]', 'pub-date[@date-type="collection"]')
        )
        self.assertEqual(result.findtext("year"), "2010")

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "09", "01"))

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "02", ""))

    def test_transform_pubdate(self):
        self.sps_package.transform_pubdate()
        xpaths_results = (
            ('pub-date[@date-type="pub"]', ("2010", "9", "1")),
            ('pub-date[@date-type="collection"]', ("2012", "2", None)),
        )
        for xpath, result in xpaths_results:
            with self.subTest(xpath=xpath, result=result):
                pubdate = self.sps_package.article_meta.find(xpath)
                self.assertIsNotNone(pubdate)
                self.assertEqual(pubdate.get("publication-format"), "electronic")
                self.assertEqual(pubdate.findtext("year"), result[0])
                self.assertEqual(pubdate.findtext("month"), result[1])
                self.assertEqual(pubdate.findtext("day"), result[2])


class Test_sps_package(unittest.TestCase):
    def test_parse_value_num(self):
        self.assertEqual(parse_value("3"), "03")

    def test_parse_value_num_spe(self):
        self.assertEqual(parse_value("Especial"), "spe")

    def test_parse_value_suppl(self):
        self.assertEqual(parse_value("Supplement"), "s")

    def test_parse_issue_num_suppl(self):
        self.assertEqual(parse_issue("3 Supl"), "03-s0")

    def test_parse_issue_num_spe_(self):
        self.assertEqual(parse_issue("4 Especial"), "04-spe")

    def test_parse_issue_num_suppl_label(self):
        self.assertEqual(parse_issue("3 Supl A"), "03-sa")

    def test_parse_issue_num_spe_num(self):
        self.assertEqual(parse_issue("4 Especial 1"), "04-spe01")

    def test_parse_issue_suppl_label(self):
        self.assertEqual(parse_issue("Supl A"), "sa")

    def test_parse_issue_spe_num(self):
        self.assertEqual(parse_issue("Especial 1"), "spe01")


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
        self.sps_package = SPS_Package(etree.fromstring(article_xml), "a01")

    def test_elements_which_has_xlink_href(self):
        items = list(self.sps_package.elements_which_has_xlink_href)
        self.assertEqual(len(items), 7)
        self.assertEqual(
            [node.tag for node in items],
            sorted(
                [
                    "inline-graphic",
                    "graphic",
                    "ext-link",
                    "ext-link",
                    "inline-supplementary-material",
                    "supplementary-material",
                    "media",
                ]
            ),
        )

    def test_replace_assets(self):
        expected = [
            ("a01tab02.gif", "a01-gtab02"),
            ("a01f01.gif", "a01-gf01"),
            ("a01tab01.gif", "a01-gtab01"),
            ("a01tab03.gif", "a01-gtab03"),
            ("a01tab04.gif", "a01-gtab04"),
            ("a01tab04.gif", "a01-gtab04"),
        ]
        items = self.sps_package.replace_assets_names()
        self.assertEqual(len(items), 6)
        for i, item in enumerate(items):
            with self.subTest(i):
                self.assertEqual(expected[i][0], item[0])
                self.assertEqual(expected[i][1], item[1])

    @mock.patch("documentstore_migracao.export.sps_package.article.get_article")
    def test_get_renditions_metadata_no_renditions(self, mk_get_article):
        mk_article = mock.Mock()
        mk_article.fulltexts.return_value = {}
        mk_get_article.return_value = mk_article
        renditions, renditions_metadata = self.sps_package.get_renditions_metadata()
        self.assertEqual(renditions, [])
        self.assertEqual(renditions_metadata, {})

    @mock.patch("documentstore_migracao.export.sps_package.article.get_article")
    def test_get_renditions_metadata(self, mk_get_article):
        fulltexts = {
            "pdf": {
                "en": "http://www.scielo.br/pdf/aa/v1n1/a01.pdf",
                "pt": "http://www.scielo.br/pdf/aa/v1n1/pt_a01.pdf",
            },
            "html": {
                "en": "http://www.scielo.br/scielo.php?script=sci_arttext&tlng=en",
                "pt": "http://www.scielo.br/scielo.php?script=sci_arttext&tlng=pt",
            },
        }
        mk_article = mock.Mock()
        mk_article.fulltexts.return_value = fulltexts
        mk_get_article.return_value = mk_article
        renditions, renditions_metadata = self.sps_package.get_renditions_metadata()
        for lang, link in fulltexts.get("pdf"):
            self.assertEqual(
                renditions,
                [
                    ('http://www.scielo.br/pdf/aa/v1n1/a01.pdf', 'a01'),
                    ('http://www.scielo.br/pdf/aa/v1n1/pt_a01.pdf', 'pt_a01'),
                ]
            )
            self.assertEqual(
                renditions_metadata,
                {
                    'en': 'http://www.scielo.br/pdf/aa/v1n1/a01.pdf',
                    'pt': 'http://www.scielo.br/pdf/aa/v1n1/pt_a01.pdf',
                }
            )


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
        self.sps_package = SPS_Package(etree.fromstring(article_xml), "a01")

    def test_parse_article(self):
        self.assertEqual(self.sps_package.parse_article_meta, [])

    def test_package_name(self):
        self.assertEqual(self.sps_package.package_name, "a01")

    def test_asset_package_name_f01(self):
        self.assertEqual(self.sps_package.asset_name("a01f01.jpg"), "a01-gf01.jpg")

    def test_asset_package_name_any_img(self):
        self.assertEqual(self.sps_package.asset_name("img.jpg"), "a01-gimg.jpg")

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
                ("volume", "volume"),
                ("issue", "05"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, None)

    def test_number(self):
        self.assertEqual(self.sps_package.number, "05")

    def test_package_name_vol_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-05-fpage-lpage"
        )

    def test_asset_package_name_f01(self):
        self.assertEqual(
            self.sps_package.asset_name("a01f01.jpg"),
            "1234-5678-acron-volume-05-fpage-lpage-gf01.jpg",
        )

    def test_asset_package_name_any_img(self):
        self.assertEqual(
            self.sps_package.asset_name("img.jpg"),
            "1234-5678-acron-volume-05-fpage-lpage-gimg.jpg",
        )

    def test_journal_meta(self):
        self.assertEqual(
            self.sps_package.journal_meta,
            [
                ("eissn", "1234-5678"),
                ("pissn", "0123-4567"),
                ("issn", "1234-5678"),
                ("acron", "acron"),
            ],
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_vol_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("issue", "05"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-05-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "05-spe"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, None)

    def test_number(self):
        self.assertEqual(self.sps_package.number, "05-spe")

    def test_package_name_vol_num_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-05-spe-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "spenum"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_vol_spe_num_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-spenum-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "spe"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_vol_spe_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-spe-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "s0"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, "0")

    def test_number(self):
        self.assertIsNone(self.sps_package.number)

    def test_package_name_vol_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-s0-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "sa"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, "a")

    def test_number(self):
        self.assertIsNone(self.sps_package.number)

    def test_package_name_vol_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-sa-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "02-s0"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, "0")

    def test_number(self):
        self.assertEqual(self.sps_package.number, "02")

    def test_package_name_vol_num_suppl_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-02-s0-fpage-lpage"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "02-sa"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_vol_num_suppl_a_fpage(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-02-sa-fpage-lpage"
        )

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id, "1234-5678-acron-2010-volume-02-sa"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", "fpage"),
                ("lpage", "lpage"),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "fpage", "lpage", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


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
                ("volume", "volume"),
                ("issue", "05"),
                ("elocation-id", "elocation"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_vol_num_continuous_publication(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-05-elocation"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, True)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", ""),
                ("lpage", ""),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", "elocation"),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "", "", ("2010", "", ""), ("", "", ""), "elocation"),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


class Test_SPS_Package_VolElocation(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>volume</volume>
            <elocation-id>elocation</elocation-id>"""
        self.sps_package = sps_package(article_meta_xml)

    def test_parse_article_meta_vol_continuous_publication(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ("volume", "volume"),
                ("elocation-id", "elocation"),
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_vol_continuous_publication(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-volume-elocation"
        )

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id, "1234-5678-acron-2010-volume"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, True)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", ""),
                ("lpage", ""),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", "elocation"),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "", "", ("2010", "", ""), ("", "", ""), "elocation"),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


class Test_SPS_Package_Aop_HTML(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<fpage>0</fpage>
            <lpage>00</lpage>"""
        self.sps_package = sps_package(article_meta_xml, doi="")

    def test_parse_article_meta_aop(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ("year", "2010"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_aop(self):
        self.assertEqual(
            self.sps_package.package_name, "1234-5678-acron-ahead-2010-00006"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, True)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", ""),
                ("lpage", ""),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "", "", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_true(self):
        self.assertTrue(self.sps_package.is_ahead_of_print)


class Test_SPS_Package_Aop_XML(unittest.TestCase):
    def setUp(self):
        self.sps_package = sps_package("")

    def test_parse_article_meta_aop(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ("year", "2010"),
                ("doi", "S0074-02761962000200006"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_package_name_aop(self):
        self.assertEqual(
            self.sps_package.package_name,
            "1234-5678-acron-ahead-2010-S0074-02761962000200006",
        )

    def test_documents_bundle_id(self):
        self.assertEqual(self.sps_package.documents_bundle_id, "1234-5678-acron-aop")

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, True)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", ""),
                ("lpage", ""),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "", "", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_true(self):
        self.assertTrue(self.sps_package.is_ahead_of_print)


class Test_SPS_Package_Article_HTML(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<volume>20</volume><fpage>0</fpage>
            <lpage>00</lpage>"""
        self.sps_package = sps_package(article_meta_xml, doi="")

    def test_parse_article_meta(self):
        self.assertEqual(
            self.sps_package.parse_article_meta,
            [
                ("volume", "20"),
                ("year", "2010"),
                ("publisher-id", "S0074-02761962000200006"),
                ("other", "00006"),
            ],
        )

    def test_supplement(self):
        self.assertEqual(self.sps_package.supplement, None)

    def test_number(self):
        self.assertEqual(self.sps_package.number, None)

    def test_package_name(self):
        self.assertEqual(self.sps_package.package_name, "1234-5678-acron-20-00006")

    def test_documents_bundle_id(self):
        self.assertEqual(
            self.sps_package.documents_bundle_id, "1234-5678-acron-2010-20"
        )

    def test_is_only_online_publication(self):
        self.assertEqual(self.sps_package.is_only_online_publication, False)

    def test_order_meta(self):
        self.assertEqual(
            self.sps_package.order_meta,
            (
                ("other", "00006"),
                ("fpage", ""),
                ("lpage", ""),
                ("documents_bundle_pubdate", ("2010", "", "")),
                ("document_pubdate", ("", "", "")),
                ("elocation-id", ""),
            ),
        )

    def test_order(self):
        self.assertEqual(
            self.sps_package.order,
            ("00006", "", "", ("2010", "", ""), ("", "", ""), ""),
        )

    def test_is_ahead_of_print_false(self):
        self.assertFalse(self.sps_package.is_ahead_of_print)


class Test_ArticleMetaCount(unittest.TestCase):
    def setUp(self):
        xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
            <counts>
                <fig-count count="0"/>
                <table-count count="0"/>
                <equation-count count="0"/>
            </counts>
            <body>
                <fig id="i01"><graphic xlink:href="/img/fbpe/rm/v30n1/0002i01.gif"/></fig>
                <table-wrap id="tab01"><label>Tabela 1</label><table><tr><td>TEXTO</td></tr></table></table-wrap>
            </body>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test__transform_article_meta_count(self):
        result = self.sps_package.transform_article_meta_count()

        self.assertIsNone(result.find(".//counts"))


class Test_ArticleMetaPublisherId(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id">S0074-02761962000200006</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_publisher_id(self):
        self.assertEqual(self.sps_package.publisher_id, "S0074-02761962000200006")


class Test_ArticleMetaNoPublisherId(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_publisher_id(self):
        self.assertIsNone(self.sps_package.publisher_id)


class Test_ArticleMetaAOPPID(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id">S0074-02761962000200006</article-id>
            <article-id pub-id-type="publisher-id" specific-use="previous-pid">S0074-02761962005000001</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_aop_pid(self):
        self.assertEqual(self.sps_package.aop_pid, "S0074-02761962005000001")

    def test_change_aop_pid(self):
        self.sps_package.aop_pid = "S0074-02761962005000001"
        self.assertEqual(self.sps_package.aop_pid, "S0074-02761962005000001")


class Test_ArticleMetaNoAOPPID(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id">S0074-02761962000200006</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_aop_pid(self):
        self.assertIsNone(self.sps_package.aop_pid)

    def test_set_aop_pid(self):
        self.sps_package.aop_pid = "S0074-02761962005000001"
        self.assertEqual(self.sps_package.aop_pid, "S0074-02761962005000001")


class Test_ArticleMetaScieloPIDV1(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id" specific-use="scielo-v1">12345(1995)</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_scielo_pid_v1(self):
        self.assertIsNotNone(self.sps_package.scielo_pid_v1)
        self.assertEqual(self.sps_package.scielo_pid_v1, "12345(1995)")

    def test_set_scielo_pid_v1(self):
        self.sps_package.scielo_pid_v1 = "1234-5678(1995)0001"
        self.assertEqual(self.sps_package.scielo_pid_v1, "1234-5678(1995)0001")


class Test_ArticleMetaNoPIDScieloV1(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id" specific-use="scielo-v2">S0101-02022011009000001</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_scielo_pid_v1(self):
        self.assertIsNone(self.sps_package.scielo_pid_v1)


class Test_ArticleMetaPIDScieloV2(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id" specific-use="scielo-v2">S0101-02022011009000001</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_scielo_pid_v2(self):
        self.assertIsNotNone(self.sps_package.scielo_pid_v2)
        self.assertEqual(self.sps_package.scielo_pid_v2, "S0101-02022011009000001")

    def test_set_scielo_pid_v2(self):
        self.sps_package.scielo_pid_v2 = "S0101-02022011009000001"
        self.assertEqual(self.sps_package.scielo_pid_v2, "S0101-02022011009000001")


class Test_ArticleMetaNoPIDScieloV2(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id" specific-use="scielo-v1">12345(1995)</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_scielo_pid_v2(self):
        self.assertIsNone(self.sps_package.scielo_pid_v2)


class Test_ArticleMetaPIDScieloV3(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id" specific-use="scielo-v3">cdmqrXxyd3DRjr88hpGQPLx</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_scielo_pid_v3(self):
        self.assertIsNotNone(self.sps_package.scielo_pid_v3)
        self.assertEqual(self.sps_package.scielo_pid_v3, "cdmqrXxyd3DRjr88hpGQPLx")

    def test_set_scielo_pid_v3(self):
        self.sps_package.scielo_pid_v3 = "cdmqrXxyd3DRjr88hpGQ123"
        self.assertEqual(self.sps_package.scielo_pid_v3, "cdmqrXxyd3DRjr88hpGQ123")


class Test_ArticleMetaNoPIDScieloV3(unittest.TestCase):
    def setUp(self):
        article_meta_xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
        </article-meta></article>"""
        article_ids = """
            <article-id pub-id-type="publisher-id" specific-use="scielo-v2">S0101-02022011009000001</article-id>
            <article-id pub-id-type="other">00006</article-id>
        """
        xml = utils.build_xml(article_meta_xml, "", article_ids=article_ids)
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree)

    def test_scielo_pid_v3(self):
        self.assertIsNone(self.sps_package.scielo_pid_v3)


class Test_DocumentPubdateSPS1_9(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9"><article-meta>
            <pub-date publication-format="electronic" date-type="collection">
                <year>2012</year><month>2</month><day>3</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("", "", ""))

    def test_set_document_pubdate(self):
        self.sps_package.document_pubdate = ("2010", "07", "20")
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "07", "20"))

    def test_set_incomplete_document_pubdate(self):
        self.sps_package.document_pubdate = ("2010", "", "")
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "", ""))


class Test_DocumentPubdateSPS1_8(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.8"><article-meta>
            <pub-date pub-type="epub-ppub">
                <year>2012</year><month>2</month><day>3</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2012", "02", "03"))

    def test_set_document_pubdate(self):
        self.sps_package.document_pubdate = ("2010", "07", "20")
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "07", "20"))

    def test_set_incomplete_document_pubdate(self):
        self.sps_package.document_pubdate = ("2010", "", "")
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "", ""))


class Test_DocumentPubdateSPS1_4(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.4"><article-meta>
            <pub-date pub-type="epub-ppub">
                <year>2012</year><month>2</month></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_document_pubdate(self):
        self.assertEqual(self.sps_package.document_pubdate, ("2012", "02", ""))

    def test_set_document_pubdate(self):
        self.sps_package.document_pubdate = ("2010", "07", "20")
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "07", "20"))

    def test_set_incomplete_document_pubdate(self):
        self.sps_package.document_pubdate = ("2010", "", "")
        self.assertEqual(self.sps_package.document_pubdate, ("2010", "", ""))


class Test_DocumentsBundlePubdateSPS1_9(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9"><article-meta>
            <pub-date publication-format="electronic" date-type="pub">
                <year>2010</year><month>5</month><day>13</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("", "", ""))

    def test_set_documents_bundle_pubdate(self):
        self.sps_package.documents_bundle_pubdate = ("2012", "10", "21")
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "10", "21"))

    def test_set_incomplete_documents_bundle_pubdate(self):
        self.sps_package.documents_bundle_pubdate = ("2012", "", "")
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "", ""))


class Test_DocumentsBundlePubdateSPS1_8(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.8"><article-meta>
            <pub-date pub-type="epub">
                <year>2010</year><month>5</month><day>13</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("", "", ""))

    def test_set_documents_bundle_pubdate(self):
        self.sps_package.documents_bundle_pubdate = ("2012", "10", "21")
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "10", "21"))

    def test_set_incomplete_documents_bundle_pubdate(self):
        self.sps_package.documents_bundle_pubdate = ("2012", "", "")
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "", ""))


class Test_DocumentsBundlePubdateSPS1_4(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.4"><article-meta>
            <pub-date pub-type="epub">
                <year>2010</year><month>5</month><day>13</day></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_documents_bundle_pubdate(self):
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("", "", ""))

    def test_set_documents_bundle_pubdate(self):
        self.sps_package.documents_bundle_pubdate = ("2012", "10", "21")
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "10", "21"))

    def test_set_incomplete_documents_bundle_pubdate(self):
        self.sps_package.documents_bundle_pubdate = ("2012", "", "")
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("2012", "", ""))


class TestMoveAppendixFromBodyToBack(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink">
            <body>
                <p>
                    <app-group>
                        <app id="anx01"><label>Anexo 1</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx01.jpg" />
                        </app>
                    </app-group>
                </p>
                <p />
                <p>
                    <app-group>
                        <app id="anx02"><label>Anexo 2</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx02.jpg" />
                        </app>
                    </app-group>
                </p>
            </body>
            <back></back>
        </article>"""
        xmltree = etree.fromstring(self.xml)
        self.app_ids = [f"anx0{num}" for num in range(1, 3)]
        self.sps_package = SPS_Package(xmltree, None)
        self.body = self.sps_package.xmltree.find("./body")
        self.back = self.sps_package.xmltree.find("./back")
        self.sps_package._move_appendix_from_body_to_back(self.body, self.back)

    def test_body_without_appedix(self):
        self.assertEqual(len(self.sps_package.xmltree.findall("./body//app-group")), 0)

    def test_back_with_appedix(self):
        app_group_tags = self.sps_package.xmltree.findall(".//back//app-group")
        self.assertEqual(len(app_group_tags), 2)
        for app_group_tag in app_group_tags:
            self.assertIn(app_group_tag.find("app").attrib["id"], self.app_ids)


class TestTransformContent(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink">
            <body>
                <p>
                    <app-group>
                        <app id="anx01"><label>Anexo 1</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx01.jpg" />
                        </app>
                    </app-group>
                </p>
                <p />
                <p>
                    <app-group>
                        <app id="anx02"><label>Anexo 2</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx02.jpg" />
                        </app>
                    </app-group>
                </p>
            </body>
            <back></back>
        </article>"""
        xmltree = etree.fromstring(self.xml)
        self.app_ids = [f"anx0{num}" for num in range(1, 3)]
        self.mk_sps_package_move_appedix_patcher = mock.patch(
            "documentstore_migracao.export.sps_package.SPS_Package._move_appendix_from_body_to_back"
        )
        self.mk_sps_package_move_appedix = (
            self.mk_sps_package_move_appedix_patcher.start()
        )
        self.mk_sps_package_transform_pubdate_patcher = mock.patch(
            "documentstore_migracao.export.sps_package.SPS_Package.transform_pubdate"
        )
        self.mk_sps_package_transform_pubdate = (
            self.mk_sps_package_transform_pubdate_patcher.start()
        )
        self.sps_package = SPS_Package(xmltree, None)
        self.body = self.sps_package.xmltree.find("./body")
        self.back = self.sps_package.xmltree.find("./back")
        self.sps_package.transform_content()

    def tearDown(self):
        self.mk_sps_package_move_appedix_patcher.stop()
        self.mk_sps_package_transform_pubdate_patcher.stop()

    def test_moves_appendix_from_body_to_back(self):
        self.mk_sps_package_move_appedix.assert_called_with(self.body, self.back)


class TestTransformContentWithSubArticle(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink">
            <body>
                <p>
                    <app-group>
                        <app id="anx01"><label>Anexo 1</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx01.jpg" />
                        </app>
                    </app-group>
                </p>
                <p />
                <p>
                    <app-group>
                        <app id="anx02"><label>Anexo 2</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx02.jpg" />
                        </app>
                    </app-group>
                </p>
            </body>
            <sub-article article-type="translation" id="TRpt" xml:lang="en">
                <body>
                    <p>
                        <app-group>
                            <app id="anx03"><label>Appendix 1</label>
                                <graphic xlink:href="/img/revistas/test/v2n3/a01anx03.jpg" />
                            </app>
                        </app-group>
                    </p>
                    <p />
                    <p>
                        <app-group>
                            <app id="anx04"><label>Appendix 2</label>
                                <graphic xlink:href="/img/revistas/test/v2n3/a01anx04.jpg" />
                            </app>
                        </app-group>
                    </p>
                </body>
            </sub-article>
        </article>"""
        xmltree = etree.fromstring(self.xml)
        self.app_ids = [f"anx0{num}" for num in range(1, 3)]
        self.mk_sps_package_move_appedix_patcher = mock.patch(
            "documentstore_migracao.export.sps_package.SPS_Package._move_appendix_from_body_to_back"
        )
        self.mk_sps_package_move_appedix = (
            self.mk_sps_package_move_appedix_patcher.start()
        )
        self.mk_sps_package_transform_pubdate_patcher = mock.patch(
            "documentstore_migracao.export.sps_package.SPS_Package.transform_pubdate"
        )
        self.mk_sps_package_transform_pubdate = (
            self.mk_sps_package_transform_pubdate_patcher.start()
        )
        self.sps_package = SPS_Package(xmltree, None)
        self.sps_package.transform_content()

    def tearDown(self):
        self.mk_sps_package_move_appedix_patcher.stop()
        self.mk_sps_package_transform_pubdate_patcher.stop()

    def test_moves_appendix_from_body_to_back_article_data(self):
        article_body = self.sps_package.xmltree.find("./body")
        article_back = article_body.getparent().find("./back")
        self.mk_sps_package_move_appedix.assert_any_call(article_body, article_back)

    def test_moves_appendix_from_body_to_back_sub_article_data(self):
        subarticle_body = self.sps_package.xmltree.find("./sub-article//body")
        subarticle_back = self.sps_package.xmltree.find("./sub-article//back")
        self.mk_sps_package_move_appedix.assert_any_call(
            subarticle_body, subarticle_back
        )


class TestTransformContentWithSubArticleAndBacks(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink">
            <body>
                <p>
                    <app-group>
                        <app id="anx01"><label>Anexo 1</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx01.jpg" />
                        </app>
                    </app-group>
                </p>
                <p />
                <p>
                    <app-group>
                        <app id="anx02"><label>Anexo 2</label>
                            <graphic xlink:href="/img/revistas/test/v2n3/a01anx02.jpg" />
                        </app>
                    </app-group>
                </p>
            </body>
            <back>
                <ref-list>
                    <ref id="B1">
                    <element-citation publication-type="journal">
                        <article-title>Article Title</article-title>
                    </element-citation>
                    </ref>
                </ref-list>
            </back>
            <sub-article article-type="translation" id="TRpt" xml:lang="en">
                <body>
                    <p>
                        <app-group>
                            <app id="anx03"><label>Appendix 1</label>
                                <graphic xlink:href="/img/revistas/test/v2n3/a01anx03.jpg" />
                            </app>
                        </app-group>
                    </p>
                    <p />
                    <p>
                        <app-group>
                            <app id="anx04"><label>Appendix 2</label>
                                <graphic xlink:href="/img/revistas/test/v2n3/a01anx04.jpg" />
                            </app>
                        </app-group>
                    </p>
                </body>
            </sub-article>
        </article>"""
        xmltree = etree.fromstring(self.xml)
        self.app_ids = [f"anx0{num}" for num in range(1, 3)]
        self.mk_sps_package_move_appedix_patcher = mock.patch(
            "documentstore_migracao.export.sps_package.SPS_Package._move_appendix_from_body_to_back"
        )
        self.mk_sps_package_move_appedix = (
            self.mk_sps_package_move_appedix_patcher.start()
        )
        self.mk_sps_package_transform_pubdate_patcher = mock.patch(
            "documentstore_migracao.export.sps_package.SPS_Package.transform_pubdate"
        )
        self.mk_sps_package_transform_pubdate = (
            self.mk_sps_package_transform_pubdate_patcher.start()
        )
        self.sps_package = SPS_Package(xmltree, None)
        self.sps_package.transform_content()

    def tearDown(self):
        self.mk_sps_package_move_appedix_patcher.stop()
        self.mk_sps_package_transform_pubdate_patcher.stop()

    def test_moves_appendix_from_body_to_back_article_data(self):
        article_body = self.sps_package.xmltree.find("./body")
        article_back = article_body.getparent().find("./back")
        self.mk_sps_package_move_appedix.assert_any_call(article_body, article_back)

    def test_moves_appendix_from_body_to_back_sub_article_data(self):
        subarticle_body = self.sps_package.xmltree.find("./sub-article//body")
        subarticle_back = self.sps_package.xmltree.find("./sub-article//back")
        self.mk_sps_package_move_appedix.assert_any_call(
            subarticle_body, subarticle_back
        )
