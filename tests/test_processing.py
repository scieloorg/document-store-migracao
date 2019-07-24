import os
import unittest
from lxml import etree
from unittest.mock import patch, ANY, call, Mock, MagicMock

from xylose.scielodocument import Journal, Article
from documentstore_migracao.processing import (
    extracted,
    conversion,
    validation,
    reading,
    inserting,
)

from . import (
    utils,
    SAMPLES_PATH,
    SAMPLES_JOURNAL,
    SAMPLES_XML_ARTICLE,
    SAMPLES_ARTICLE,
    COUNT_SAMPLES_FILES,
    SAMPLE_KERNEL_JOURNAL,
)


class TestProcessingExtracted(unittest.TestCase):
    @patch("documentstore_migracao.processing.extracted.article.ext_article_txt")
    def test_extract_all_data(self, mk_extract_article_txt):

        mk_extract_article_txt.return_value = SAMPLES_XML_ARTICLE
        with utils.environ(SOURCE_PATH="/tmp"):
            try:
                extracted.extract_all_data(["S0036-36341997000100001"])

                self.assertTrue(os.path.exists("/tmp/S0036-36341997000100001.xml"))
            finally:
                os.remove("/tmp/S0036-36341997000100001.xml")


class TestProcessingConversion(unittest.TestCase):
    @patch("documentstore_migracao.processing.conversion.SPS_Package")
    @patch("documentstore_migracao.processing.conversion.xml")
    def test_convert_article_xml_sets_sps_and_dtd_versions(
        self, mk_utils_xml, MockSPS_Package
    ):
        mk_obj_xml = MagicMock()
        mk_obj_xmltree = MagicMock()
        mk_obj_xmltree.getroot.return_value = mk_obj_xml
        mk_utils_xml.loadToXML.return_value = mk_obj_xmltree
        conversion.convert_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )
        mk_obj_xml.set.assert_has_calls(
            [call("specific-use", "sps-1.9"), call("dtd-version", "1.1")]
        )

    @patch("documentstore_migracao.processing.conversion.SPS_Package")
    @patch("documentstore_migracao.processing.conversion.xml")
    def test_convert_article_xml_creates_sps_package_instance(
        self, mk_utils_xml, MockSPS_Package
    ):
        mk_obj_xmltree = MagicMock()
        mk_utils_xml.loadToXML.return_value = mk_obj_xmltree
        conversion.convert_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )
        MockSPS_Package.assert_called_once_with(mk_obj_xmltree)

    @patch("documentstore_migracao.processing.conversion.SPS_Package")
    @patch("documentstore_migracao.processing.conversion.xml")
    def test_convert_article_xml_calls_sps_package_transform_body(
        self, mk_utils_xml, MockSPS_Package
    ):
        mk_xml_sps = MagicMock()
        MockSPS_Package.return_value = mk_xml_sps
        conversion.convert_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )
        mk_xml_sps.transform_body.assert_called_once()

    @patch("documentstore_migracao.processing.conversion.SPS_Package")
    @patch("documentstore_migracao.processing.conversion.xml")
    def test_convert_article_xml_calls_sps_package_transform_pubdate(
        self, mk_utils_xml, MockSPS_Package
    ):
        mk_xml_sps = MagicMock()
        MockSPS_Package.return_value = mk_xml_sps
        conversion.convert_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )
        mk_xml_sps.transform_pubdate.assert_called_once()

    def test_convert_article_xml(self):

        conversion.convert_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )

    @patch("documentstore_migracao.processing.conversion.convert_article_xml")
    def test_convert_article_ALLxml(self, mk_convert_article_xml):

        with utils.environ(SOURCE_PATH=SAMPLES_PATH):
            conversion.convert_article_ALLxml()
            mk_convert_article_xml.assert_called_with(ANY)

            self.assertEqual(
                len(mk_convert_article_xml.mock_calls), COUNT_SAMPLES_FILES
            )

    @patch("documentstore_migracao.processing.conversion.convert_article_xml")
    def test_convert_article_ALLxml_with_exception(self, mk_convert_article_xml):

        mk_convert_article_xml.side_effect = KeyError("Test Error - CONVERSION")
        with utils.environ(SOURCE_PATH=SAMPLES_PATH):

            conversion.convert_article_ALLxml()


class TestReadingJournals(unittest.TestCase):
    def setUp(self):
        self.journals_json_path = os.path.join(
            SAMPLES_PATH, "base-isis-sample", "title", "title.json"
        )

    def test_should_load_file_successfull(self):
        data = reading.read_json_file(self.journals_json_path)

        self.assertTrue(type(data), list)
        self.assertEqual(
            data[0].get("v140")[0]["_"],
            "Colégio Brasileiro de Cirurgia Digestiva - CBCD",
        )

        self.assertEqual(len(data), 3)


class TestConversionJournalJson(unittest.TestCase):
    def setUp(self):
        self.json_journal = {
            "v100": [{"_": "sample"}],
            "v68": [{"_": "spl"}],
            "v940": [{"_": "20190128"}],
            "v50": [{"_": "C"}],
            "v400": [{"_": "0001-3714"}],
            "v435": [{"t": "ONLIN", "_": "0001-3714"}],
        }

    def test_should_return_a_bundle(self):
        journal = conversion.conversion_journal_to_bundle(self.json_journal)
        self.assertEqual(SAMPLE_KERNEL_JOURNAL, journal)

    def test_should_return_a_list_of_bundle(self):
        journals = conversion.conversion_journals_to_kernel([self.json_journal])
        self.assertEqual([SAMPLE_KERNEL_JOURNAL], journals)


class TestProcessingValidation(unittest.TestCase):
    def test_validate_article_xml(self):

        result = validation.validate_article_xml(
            os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml")
        )
        self.assertIn(
            "Element p is not declared in p list of possible children", result.keys()
        )

    def test_validate_article_xml_not_print(self):

        result = validation.validate_article_xml(
            os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml"), False
        )
        self.assertIn(
            "Element p is not declared in p list of possible children", result.keys()
        )

    def test_validate_article_xml_XMLSPSVersionError(self):

        result = validation.validate_article_xml(
            os.path.join(SAMPLES_PATH, "S0102-86501998000100007_invalid.xml")
        )
        self.assertIn(
            "cannot get the SPS version from /article/@specific-use", result.keys()
        )

    def test_validate_article_xml_valid(self):

        result = validation.validate_article_xml(
            os.path.join(SAMPLES_PATH, "0034-8910-rsp-48-2-0347-valid.xml"), False
        )
        self.assertEqual({}, result)

    @patch("documentstore_migracao.processing.validation.validate_article_xml")
    def test_validate_article_ALLxml(self, mk_validate_article_xml):
        mk_validate_article_xml.return_value = {
            "Element p is not declared in p list of possible children": {
                "count": 2,
                "lineno": [410, 419],
                "filename": {
                    os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml")
                },
                "message": [
                    "Element p is not declared in p" " list of possible children",
                    "Element p is not declared in p" " list of possible children",
                ],
            }
        }
        list_files_xmls = [
            "S0044-59672003000300001.pt.xml",
            "S0102-86501998000100007.xml",
            "S0102-86501998000100002.xml",
            "S0036-36341997000100003.xml",
            "S0036-36341997000100002.xml",
            "S0036-36341997000100001.xml",
        ]
        calls = [
            call(os.path.join(SAMPLES_PATH, file_xml), False)
            for file_xml in list_files_xmls
        ]

        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):
            validation.validate_article_ALLxml()
            mk_validate_article_xml.assert_has_calls(calls, any_order=True)

    @patch("documentstore_migracao.processing.validation.validate_article_xml")
    def test_validate_article_ALLxml_with_exception(self, mk_validate_article_xml):

        mk_validate_article_xml.side_effect = KeyError("Test Error - Validation")
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):

            with self.assertRaises(KeyError) as cm:
                validation.validate_article_ALLxml()

                self.assertEqual("Test Error - Validation", str(cm.exception))

    @patch("documentstore_migracao.processing.validation.XMLValidator")
    def test_validation_should_fail_if_lxml_raise_an_exception(self, mk_xmlvalidator):
        mk_xmlvalidator.parse.side_effect = etree.XMLSyntaxError(
            "some error", 1, 1, 1, "fake_path/file.xml"
        )
        result = validation.validate_article_xml("fake_path/file.xml")
        self.assertEqual(
            {
                "some error (file.xml, line 1)": {
                    "count": 1,
                    "lineno": [1],
                    "message": ["some error (file.xml, line 1)"],
                    "filename": {"fake_path/file.xml"},
                }
            },
            result,
        )
