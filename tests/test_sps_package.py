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

    def test_set_documents_bundle_pubdate_to_none(self):
        self.xml = """<article specific-use="sps-1.9"><article-meta>
            <pub-date publication-format="electronic" date-type="collection">
                <year>2010</year><month>5</month></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)
        self.sps_package.documents_bundle_pubdate = None
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("", "", ""))


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

    def test_set_documents_bundle_pubdate_to_none(self):
        self.xml = """<article specific-use="sps-1.8"><article-meta>
            <pub-date pub-type="collection">
                <year>2010</year><month>5</month></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)
        self.sps_package.documents_bundle_pubdate = None
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("", "", ""))


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

    def test_set_documents_bundle_pubdate_to_none(self):
        self.xml = """<article specific-use="sps-1.4"><article-meta>
            <pub-date pub-type="epub-ppub">
                <year>2010</year><month>5</month></pub-date>
        </article-meta></article>"""
        xmltree = etree.fromstring(self.xml)
        self.sps_package = SPS_Package(xmltree, None)
        self.sps_package.documents_bundle_pubdate = None
        self.assertEqual(self.sps_package.documents_bundle_pubdate, ("", "", ""))


@mock.patch(
    "documentstore_migracao.export.sps_package.SPS_Package._move_appendix_from_body_to_back"
)
@mock.patch(
    "documentstore_migracao.export.sps_package.SPS_Package.transform_pubdate"
)
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
        self.sps_package = SPS_Package(xmltree, None)
        self.body = self.sps_package.xmltree.find("./body")
        self.back = self.sps_package.xmltree.find("./back")

    def test_calls_transform_pubdate(
        self, mk_transform_pubdate, mk_sps_package_move_appedix
    ):
        self.sps_package.transform_content()
        mk_transform_pubdate.assert_called_once()

    def test_calls_moves_appendix_from_body_to_back(
        self, mk_transform_pubdate, mk_sps_package_move_appedix
    ):
        self.sps_package.transform_content()
        mk_sps_package_move_appedix.assert_called_once()


class TestCompletePubDate(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9"><article-meta>
            <article-id pub-id-type="publisher-id" specific-use="scielo-v2">S0074-02761962000200006</article-id>
            {volume}
            {issue}
            {pub_date_collection}
            {pub_date_pub}
        </article-meta></article>"""

    def test_adds_document_pubdate_if_date_not_in_xml(self):
        volume = "<volume>50</volume>"
        issue = "<issue>1</issue>"
        pub_date_collection = """<pub-date date-type="collection" publication-format="electronic">
            <year>2010</year>
        </pub-date>"""
        xml_txt = self.xml.format(
            volume=volume,
            issue=issue,
            pub_date_collection=pub_date_collection,
            pub_date_pub="",
        )
        xmltree = etree.fromstring(xml_txt)
        xml_sps = SPS_Package(xmltree, None)
        xml_sps.complete_pub_date(("2020", "01", "24"), None)
        self.assertEqual(xml_sps.document_pubdate, ("2020", "01", "24"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("2010", "", ""))

    def test_does_not_change_document_pubdate_if_document_pubdate_is_none(self):
        volume = "<volume>50</volume>"
        issue = "<issue>1</issue>"
        pub_date_collection = """<pub-date date-type="collection" publication-format="electronic">
            <year>2010</year>
        </pub-date>"""
        xml_txt = self.xml.format(
            volume=volume,
            issue=issue,
            pub_date_collection=pub_date_collection,
            pub_date_pub="",
        )
        xmltree = etree.fromstring(xml_txt)
        xml_sps = SPS_Package(xmltree, None)
        xml_sps.complete_pub_date(None, None)
        self.assertEqual(xml_sps.document_pubdate, ("", "", ""))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("2010", "", ""))

    def test_fixes_bundle_pubdate_if_it_is_aop(self):
        pub_date_collection = """<pub-date date-type="collection" publication-format="electronic">
            <year>2010</year><month>5</month><day>13</day>
        </pub-date>"""
        xml_txt = self.xml.format(
            volume="",
            issue="",
            pub_date_collection=pub_date_collection,
            pub_date_pub="",
        )
        xmltree = etree.fromstring(xml_txt)
        xml_sps = SPS_Package(xmltree, None)
        xml_sps.complete_pub_date(("2020", "01", "24"), ("1997", "03", ""))
        self.assertEqual(xml_sps.document_pubdate, ("2020", "01", "24"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("", "", ""))

    def test_adds_bundle_pubdate_if_date_not_in_xml(self):
        volume = "<volume>50</volume>"
        issue = "<issue>1</issue>"
        pub_date_pub = """<pub-date date-type="pub" publication-format="electronic">
            <year>2010</year><month>5</month><day>13</day>
        </pub-date>"""
        xml_txt = self.xml.format(
            volume=volume,
            issue=issue,
            pub_date_collection="",
            pub_date_pub=pub_date_pub,
        )
        xmltree = etree.fromstring(xml_txt)
        xml_sps = SPS_Package(xmltree, None)
        xml_sps.complete_pub_date(("2010", "05", "13"), ("1997", "03", ""))
        self.assertEqual(xml_sps.document_pubdate, ("2010", "05", "13"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("1997", "03", ""))


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
        </article>"""
        xmltree = etree.fromstring(self.xml)
        self.app_ids = [f"anx0{num}" for num in range(1, 3)]
        self.sps_package = SPS_Package(xmltree, None)

    def test_body_without_appedix(self):
        self.sps_package._move_appendix_from_body_to_back()
        self.assertEqual(len(self.sps_package.xmltree.findall("./body//app-group")), 0)

    def test_back_with_appedix(self):
        self.sps_package._move_appendix_from_body_to_back()
        app_group_tags = self.sps_package.xmltree.findall(".//back//app-group")
        self.assertEqual(len(app_group_tags), 2)
        for app_group_tag in app_group_tags:
            self.assertIn(app_group_tag.find("app").attrib["id"], self.app_ids)


class TestMoveAppendixFromBodyToBackWithSubArticle(unittest.TestCase):
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
        self.app_ids = [f"anx0{num}" for num in range(1, 5)]
        self.sps_package = SPS_Package(xmltree, None)

    def test_from_body_to_back_article_data(self):
        self.sps_package._move_appendix_from_body_to_back()
        self.assertEqual(len(self.sps_package.xmltree.findall("./body//app-group")), 0)
        app_group_tags = self.sps_package.xmltree.findall("./back//app-group")
        self.assertEqual(len(app_group_tags), 2)
        for app_group_tag in app_group_tags:
            self.assertIn(app_group_tag.find("app").attrib["id"], self.app_ids[:2])

    def test_from_body_to_back_sub_article_data(self):
        self.sps_package._move_appendix_from_body_to_back()
        self.assertEqual(
            len(self.sps_package.xmltree.findall("./sub-article//body//app-group")), 0
        )
        app_group_tags = self.sps_package.xmltree.findall(
            "./sub-article//back//app-group"
        )
        self.assertEqual(len(app_group_tags), 2)
        for app_group_tag in app_group_tags:
            self.assertIn(app_group_tag.find("app").attrib["id"], self.app_ids[2:])


class TestMoveAppendixFromBodyToBackWithSubArticleAndBacks(unittest.TestCase):
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
        self.app_ids = [f"anx0{num}" for num in range(1, 5)]
        self.sps_package = SPS_Package(xmltree, None)

    def test_from_body_to_back_article_data(self):
        self.sps_package._move_appendix_from_body_to_back()
        self.assertEqual(len(self.sps_package.xmltree.findall("./body//app-group")), 0)
        app_group_tags = self.sps_package.xmltree.findall("./back//app-group")
        self.assertEqual(len(app_group_tags), 2)
        for app_group_tag in app_group_tags:
            self.assertIn(app_group_tag.find("app").attrib["id"], self.app_ids[:2])

    def test_from_body_to_back_sub_article_data(self):
        self.sps_package._move_appendix_from_body_to_back()
        self.assertEqual(
            len(self.sps_package.xmltree.findall("./sub-article//body//app-group")), 0
        )
        app_group_tags = self.sps_package.xmltree.findall(
            "./sub-article//back//app-group"
        )
        self.assertEqual(len(app_group_tags), 2)
        for app_group_tag in app_group_tags:
            self.assertIn(app_group_tag.find("app").attrib["id"], self.app_ids[2:])


class TestMoveAcknowledgementsFromBodyToBack(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="pt">
            <body>
                <p><bold>Agradecimentos</bold></p>
                <p>À Prof. Maria Santos, coordenadora do grupo de pesquisa X</p>
                <p> </p>
                <p><bold>Referencias</bold></p>
                <p></p>
            </body>
        </article>"""
        xmltree = etree.fromstring(
            self.xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
        )
        self.sps_package = SPS_Package(xmltree, None)

    def test_body_without_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        body_tag = self.sps_package.xmltree.find("./body")
        body_txt = etree.tostring(body_tag).decode("utf-8")
        self.assertNotIn("Agradecimentos", body_txt)
        self.assertNotIn(
            "À Prof. Maria Santos, coordenadora do grupo de pesquisa X", body_txt
        )
        self.assertIn("Referencias", body_txt)
        self.assertEqual(len(body_tag.getchildren()), 3)

    def test_back_with_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        ack_tag = self.sps_package.xmltree.find("./back/ack")
        self.assertIsNotNone(ack_tag)
        ack_children = ack_tag.getchildren()
        self.assertEqual(
            ack_children[0].text,
            "À Prof. Maria Santos, coordenadora do grupo de pesquisa X",
        )


class TestDoNotMoveAcknowledgementWordFromBodyText(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="pt">
            <body>
                <p><bold>Subtítulo do Texto</bold></p>
                <p></p>
                <p>O agradecimento é uma expressão de reconhecimento de uma ação.</p>
                <p>Texto de teste.</p>
            </body>
        </article>"""
        xmltree = etree.fromstring(
            self.xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
        )
        self.sps_package = SPS_Package(xmltree, None)

    def test_body_with_acknowledgement_in_body_content(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        body_tag = self.sps_package.xmltree.find("./body")
        body_txt = etree.tostring(body_tag).decode("utf-8")
        self.assertIn("agradecimento", body_txt)

    def test_back_without_acknowledgement(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        self.assertIsNone(self.sps_package.xmltree.find("./back/ack"))


class TestMoveAcknowledgementsFromBodyToExistingBack(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="pt">
            <body>
                <p><bold>Subtítulo do Texto</bold></p>
                <p></p>
                <p>O agradecimento é uma expressão de reconhecimento de uma ação.</p>
                <p>Texto de teste.</p>
                <p>
                    <font face="Verdana, Arial, Helvetica, sans-serif" size="3">AGRADECIMENTO</font>
                </p>
                <p></p>
                <p>
                    <font face="Verdana, Arial, Helvetica, sans-serif" size="2">Ao Fundo de Amparo à Pesquisa</font></p>
            </body>
            <back>
                <notes></notes>
            </back>
        </article>"""
        xmltree = etree.fromstring(
            self.xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
        )
        self.sps_package = SPS_Package(xmltree, None)

    def test_body_without_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        body_tag = self.sps_package.xmltree.find("./body")
        body_txt = etree.tostring(body_tag).decode("utf-8")
        self.assertNotIn("AGRADECIMENTO", body_txt)
        self.assertNotIn("Ao Fundo de Amparo à Pesquisa", body_txt)
        self.assertEqual(len(body_tag.getchildren()), 4)

    def test_existing_back_with_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        back_result = self.sps_package.xmltree.findall("./back")
        self.assertTrue(len(back_result) == 1)
        self.assertIsNotNone(back_result[0].find("./notes"))
        ack_tag = back_result[0].find("./ack")
        self.assertIsNotNone(ack_tag)
        ack_children = ack_tag.getchildren()
        self.assertEqual(ack_children[0].text, "Ao Fundo de Amparo à Pesquisa")


class TestMoveAcknowledgementsFromBodyToBackWithSubArticle(unittest.TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9" xmlns:xlink="http://www.w3.org/1999/xlink">
            <body>
                <p><bold>Agradecimentos </bold></p>
                <p></p>
                <p>À Prof. Maria Santos, coordenadora do grupo de pesquisa X</p>
            </body>
            <sub-article article-type="translation" id="TRpt" xml:lang="en">
                <body>
                    <p><bold> Acknowledgements</bold></p>
                    <p>We want to thank to Prof. Maria Santos, coordinator of X research group</p>
                </body>
            </sub-article>
            <sub-article article-type="translation" id="TRpt" xml:lang="es">
                <body>
                    <p><bold> Agradecimientos </bold></p>
                    <p></p>
                    <p>Prof. Maria Santos, coordinadora del grupo de pesquisa X</p>
                </body>
            </sub-article>
        </article>"""
        xmltree = etree.fromstring(
            self.xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
        )
        self.sps_package = SPS_Package(xmltree, None)

    def test_article_body_without_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        body_tag = self.sps_package.xmltree.find("./body")
        body_txt = etree.tostring(body_tag).decode("utf-8")
        self.assertNotIn("Agradecimentos", body_txt)
        self.assertNotIn(
            "À Prof. Maria Santos, coordenadora do grupo de pesquisa X", body_txt
        )
        self.assertEqual(len(body_tag.getchildren()), 0)

    def test_en_sub_article_body_without_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        body_tag = self.sps_package.xmltree.xpath('./sub-article[@xml:lang="en"]/body')[
            0
        ]
        body_txt = etree.tostring(body_tag).decode("utf-8")
        self.assertNotIn("Acknowledgements", body_txt)
        self.assertNotIn(
            "We want to thank to Prof. Maria Santos, coordinator of X research group",
            body_txt,
        )
        self.assertEqual(len(body_tag.getchildren()), 0)

    def test_es_sub_article_body_without_acknowledgements(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        body_tag = self.sps_package.xmltree.xpath('./sub-article[@xml:lang="es"]/body')[
            0
        ]
        body_txt = etree.tostring(body_tag).decode("utf-8")
        self.assertNotIn("Agradecimientos", body_txt)
        self.assertNotIn(
            "Prof. Maria Santos, coordinadora del grupo de pesquisa X", body_txt
        )
        self.assertEqual(len(body_tag.getchildren()), 0)

    def test_article_back_data(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        ack_tag = self.sps_package.xmltree.find("./back/ack")
        self.assertIsNotNone(ack_tag)
        ack_children = ack_tag.getchildren()
        self.assertEqual(
            ack_children[0].text,
            "À Prof. Maria Santos, coordenadora do grupo de pesquisa X",
        )

    def test_en_subarticle_back_data(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        ack_children = self.sps_package.xmltree.xpath(
            './sub-article[@xml:lang="en"]/back/ack'
        )[0].getchildren()
        self.assertEqual(
            ack_children[0].text,
            "We want to thank to Prof. Maria Santos, coordinator of X research group",
        )

    def test_es_subarticle_back_data(self):
        self.sps_package._move_acknowledgements_from_body_to_back()
        ack_children = self.sps_package.xmltree.xpath(
            './sub-article[@xml:lang="es"]/back/ack'
        )[0].getchildren()
        self.assertEqual(
            ack_children[0].text,
            "Prof. Maria Santos, coordinadora del grupo de pesquisa X",
        )


class TestUpdateMixedCitations(unittest.TestCase):
    def setUp(self):
        xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><back>
                <ref-list>
                    <ref id="B1">
                        <element-citation></element-citation>
                    </ref>
                    <ref id="B2">
                        <mixed-citation>Old mixed-citation</mixed-citation>
                        <element-citation></element-citation>
                    </ref>
                </ref-list>
            </back></article>"""
        self.package = SPS_Package(etree.fromstring(xml))
        self.references = {
            "1": "1. New mixed-citation",
            "2": "2 Updated mixed-citation",
        }

    def test_should_add_mixed_when_element_is_missing(self):
        self.package.update_mixed_citations(self.references)

        self.assertIn(b"<label>1</label>", etree.tostring(self.package.xmltree))
        self.assertIn(
            b"<mixed-citation>1. New mixed-citation</mixed-citation>",
            etree.tostring(self.package.xmltree),
        )

    def test_should_not_update_an_existing_mixed_citation_if_override_is_false(self):
        self.package.update_mixed_citations(self.references)

        self.assertNotIn(b"<label>2</label>", etree.tostring(self.package.xmltree))
        self.assertIn(
            b"<mixed-citation>Old mixed-citation</mixed-citation>",
            etree.tostring(self.package.xmltree),
        )

    def test_should_update_an_existing_mixed_citation_if_override_is_true(self):
        self.package.update_mixed_citations(self.references, override=True)

        self.assertIn(b"<label>2</label>", etree.tostring(self.package.xmltree))
        self.assertNotIn(
            b"<mixed-citation>Old mixed-citation</mixed-citation>",
            etree.tostring(self.package.xmltree),
        )
        self.assertIn(
            b"<mixed-citation>2 Updated mixed-citation</mixed-citation>",
            etree.tostring(self.package.xmltree),
        )

    def test_should_convert_html_tags_to_jats_tags(self):
        self.references["1"] = "<b>text</b> <i>text</i>"
        self.package.update_mixed_citations(self.references)

        self.assertIn(
            b"<mixed-citation><bold>text</bold> <italic>text</italic></mixed-citation>",
            etree.tostring(self.package.xmltree),
        )

    def test_should_not_update_the_mixed_citations_if_the_references_dict_have_wrong_indexes(
        self
    ):
        self.package.update_mixed_citations({"10": "New mixed-citation"})

        self.assertNotIn(
            b"<mixed-citation>New mixed-citation</mixed-citation>",
            etree.tostring(self.package.xmltree),
        )

    def test_should_not_update_the_label_tag_when_extracted_number_does_not_match_with_order_number(
        self
    ):
        references = {"1": "Reference without label"}
        self.package.update_mixed_citations(references)

        self.assertIn(
            b"<mixed-citation>Reference without label</mixed-citation>",
            etree.tostring(self.package.xmltree),
        )
        self.assertNotIn(b"<label>1</label>", etree.tostring(self.package.xmltree))


class TestGetRefItems(unittest.TestCase):
    def _get_sps_package(self, text):
        return SPS_Package(etree.fromstring(text), None)

    def test__get_ref_items_returns_ref_list_three_ref_items(self):
        text = """
        <article>
            <body></body>
            <back>
                <ref-list>
                    <ref>1</ref>
                    <ref>2</ref>
                    <ref>3</ref>
                </ref-list>
            </back>
        </article>
        """
        xml = etree.fromstring(text)
        body = xml.find(".//body")
        _sps_package = self._get_sps_package(text)
        ref_items = _sps_package._get_ref_items(body)
        self.assertEqual(ref_items[0].text, "1")
        self.assertEqual(ref_items[1].text, "2")
        self.assertEqual(ref_items[2].text, "3")

    def test__get_ref_items_returns_subarticle_ref_list_ref_items(self):
        text = """
        <article>
            <body></body>
            <back>
                <ref-list>
                    <ref>1</ref>
                    <ref>2</ref>
                    <ref>3</ref>
                </ref-list>
            </back>
            <sub-article>
                <body></body>
                <back>
                </back>
            </sub-article>
        </article>
        """
        xml = etree.fromstring(text)
        body = xml.find(".//sub-article/body")
        _sps_package = self._get_sps_package(text)
        ref_items = _sps_package._get_ref_items(body)
        self.assertEqual(len(ref_items), 3)


class TestRemoveBodyWhenFulltextIsOnlyAvailableInPDF(unittest.TestCase):
    def setUp(self):
        xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
            <self-uri xlink:href="url/arquivo.pdf" xml:lang="fr">Full text available only in PDF format (FR)</self-uri>
            <self-uri xlink:href="ufl/arquivo.pdf" xml:lang="pt">Texto completo somente em PDF (PT)</self-uri>
            <body>
             <p content-type="title">Título!</p>
             <p><a href="/pdf/mioc/v80n1/vol80(f1)_002-010.pdf">Texto completo disponível apenas em PDF.</a></p>
             <p><a href="/pdf/mioc/v80n1/vol80(f1)_002-010.pdf">Full text available only in PDF format.</a></p>
             <p></p>
            </body>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        self.sps_package = SPS_Package(xmltree, None)

    def test_remove_body_when_self_uri_are_available_and_text_points_to_full_text_in_pdf(
        self,
    ):
        self.sps_package.remove_article_body_when_text_is_available_only_in_pdf()
        self.assertIsNone(self.sps_package.xmltree.find(".//body"))

    def test_do_not_remove_body_when_self_uri_tag_is_not_present(self):
        article_meta = self.sps_package.xmltree.find(".//article-meta")
        tags = self.sps_package.xmltree.findall(".//self-uri")

        for tag in tags:
            article_meta.remove(tag)

        self.sps_package.remove_article_body_when_text_is_available_only_in_pdf()
        self.assertIsNotNone(self.sps_package.xmltree.find(".//body"))

    def test_do_not_remove_body_if_it_does_not_point_to_full_text(self):
        xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><article-meta>
            <self-uri xlink:href="fr_tomo14(f1)_104-116.pdf" xml:lang="fr">Full text available only in PDF format (FR)</self-uri>
            <self-uri xlink:href="/tomo14(f1)_104-116.pdf" xml:lang="pt">Texto completo somente em PDF (PT)</self-uri>
            <body>
             <p content-type="title">Título!</p>
            </body>
        </article-meta></article>"""
        xmltree = etree.fromstring(xml)
        sps_package = SPS_Package(xmltree, None)
        sps_package.remove_article_body_when_text_is_available_only_in_pdf()
        self.assertIsNotNone(self.sps_package.xmltree.find(".//body"))
