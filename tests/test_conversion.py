import tempfile
import json
import shutil
from unittest import TestCase, mock
from pathlib import Path

from lxml import etree

from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao.processing import conversion


def save_json_file(source_path, document_pid, article_metadata):
    json_file_path = Path(source_path).joinpath(Path(document_pid + ".json"))
    metadata = {
        "article": article_metadata,
    }
    with json_file_path.open("w") as json_file:
        json.dump(metadata, json_file)


class TestCompletePubDate(TestCase):
    def setUp(self):
        self.xml = """<article specific-use="sps-1.9"><article-meta>
            <article-id pub-id-type="publisher-id" specific-use="scielo-v2">S0074-02761962000200006</article-id>
            {volume}
            {issue}
            {pub_date_collection}
            {pub_date_pub}
        </article-meta></article>"""
        self.source_path = tempfile.mkdtemp(".")

    def tearDown(self):
        shutil.rmtree(self.source_path)

    def test_complete_pub_date_adds_document_pubdate_if_date_not_in_xml(self):
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
        metadata = {
            "v65": [{"_": "19970300"}],
            "v223": [{"_": "20200124"}],
        }
        save_json_file(self.source_path, xml_sps.scielo_pid_v2, metadata)
        with mock.patch.dict("os.environ", {"SOURCE_PATH": str(self.source_path)}):
            conversion.complete_pub_date(xml_sps)
        self.assertEqual(xml_sps.document_pubdate, ("2020", "01", "24"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("2010", "", ""))

    def test_complete_pub_date_adds_creation_date_if_date_not_in_xml_and_no_document_pubdate(
        self,
    ):
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
        metadata = {
            "v65": [{"_": "19970300"}],
            "v93": [{"_": "20000401"}],
        }
        save_json_file(self.source_path, xml_sps.scielo_pid_v2, metadata)
        with mock.patch.dict("os.environ", {"SOURCE_PATH": str(self.source_path)}):
            conversion.complete_pub_date(xml_sps)
        self.assertEqual(xml_sps.document_pubdate, ("2000", "04", "01"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("2010", "", ""))

    def test_complete_pub_date_adds_update_date_if_date_not_in_xml_and_no_document_pubdate_nor_creation_date(
        self,
    ):
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
        metadata = {
            "v65": [{"_": "19970300"}],
            "v91": [{"_": "19990319"}],
        }
        save_json_file(self.source_path, xml_sps.scielo_pid_v2, metadata)
        with mock.patch.dict("os.environ", {"SOURCE_PATH": str(self.source_path)}):
            conversion.complete_pub_date(xml_sps)
        self.assertEqual(xml_sps.document_pubdate, ("1999", "03", "19"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("2010", "", ""))

    def test_complete_pub_date_fix_pubdate_if_it_is_aop(self):
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
        metadata = {
            "v65": [{"_": "19970300"}],
            "v223": [{"_": "20200124"}],
        }
        save_json_file(self.source_path, xml_sps.scielo_pid_v2, metadata)
        with mock.patch.dict("os.environ", {"SOURCE_PATH": str(self.source_path)}):
            conversion.complete_pub_date(xml_sps)
        self.assertEqual(xml_sps.document_pubdate, ("2020", "01", "24"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("", "", ""))

    def test_complete_pub_date_adds_bundle_pubdate_if_date_not_in_xml(self):
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
        metadata = {
            "v65": [{"_": "19970300"}],
            "v223": [{"_": "20200124"}],
        }
        save_json_file(self.source_path, xml_sps.scielo_pid_v2, metadata)
        with mock.patch.dict("os.environ", {"SOURCE_PATH": str(self.source_path)}):
            conversion.complete_pub_date(xml_sps)
        self.assertEqual(xml_sps.document_pubdate, ("2010", "05", "13"))
        self.assertEqual(xml_sps.documents_bundle_pubdate, ("1997", "03", ""))
