import os
import unittest
from unittest.mock import patch, ANY, call, Mock

from xylose.scielodocument import Journal, Article
from documentstore_migracao.processing import (
    extrated,
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


class TestProcessingExtrated(unittest.TestCase):
    def setUp(self):
        self.obj_journal = Journal(SAMPLES_JOURNAL)

    @patch("documentstore_migracao.processing.extrated.article.get_articles")
    def test_extrated_journal_data(self, mk_get_articles):

        mk_get_articles.return_value = [Article(SAMPLES_ARTICLE)]
        with utils.environ(SOURCE_PATH="/tmp"):
            extrated.extrated_journal_data(self.obj_journal)

            self.assertTrue(os.path.isfile("/tmp/S0036-36341997000100001.xml"))
            os.remove("/tmp/S0036-36341997000100001.xml")

    @patch("documentstore_migracao.processing.extrated.files.write_file")
    @patch("documentstore_migracao.processing.extrated.article.get_not_xml_article")
    @patch("documentstore_migracao.processing.extrated.article.get_articles")
    def test_extrated_journal_data_notCall(
        self, mk_get_articles, mk_get_not_xml_article, mk_write_file
    ):

        mk_get_articles.return_value = [Article(SAMPLES_ARTICLE)]
        mk_get_not_xml_article.return_value = None

        with utils.environ(SOURCE_PATH="/tmp"):
            extrated.extrated_journal_data(self.obj_journal)
            mk_write_file.assert_not_called()

    @patch("documentstore_migracao.processing.extrated.extrated_journal_data")
    def test_extrated_selected_journal(self, mk_extrated_journal_data):

        with utils.environ(SCIELO_COLLECTION="spa"):
            extrated.extrated_selected_journal(SAMPLES_JOURNAL["issns"])
            mk_extrated_journal_data.assert_called_once_with(ANY)

    @patch("documentstore_migracao.processing.extrated.journal.get_journals")
    @patch("documentstore_migracao.processing.extrated.extrated_journal_data")
    def test_extrated_all_data(self, mk_extrated_journal_data, mk_get_journals):

        mk_get_journals.return_value = [self.obj_journal]
        extrated.extrated_all_data()
        mk_extrated_journal_data.assert_called_once_with(self.obj_journal)


class TestProcessingConversion(unittest.TestCase):
    def test_conversion_article_xml(self):

        conversion.conversion_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )

    @patch("documentstore_migracao.processing.conversion.conversion_article_xml")
    def test_conversion_article_ALLxml(self, mk_conversion_article_xml):

        with utils.environ(SOURCE_PATH=SAMPLES_PATH):
            conversion.conversion_article_ALLxml()
            mk_conversion_article_xml.assert_called_with(ANY)

            self.assertEqual(
                len(mk_conversion_article_xml.mock_calls), COUNT_SAMPLES_FILES
            )

    @patch("documentstore_migracao.processing.conversion.conversion_article_xml")
    def test_conversion_article_ALLxml_with_exception(self, mk_conversion_article_xml):

        mk_conversion_article_xml.side_effect = KeyError("Test Error - CONVERSION")
        with utils.environ(SOURCE_PATH=SAMPLES_PATH):

            conversion.conversion_article_ALLxml()
            # with self.assertRaises(KeyError) as cm:
            #     conversion.conversion_article_ALLxml()
            #     self.assertEqual("Test Error - CONVERSION", str(cm.exception))


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
            "v400": [{"_": "10000-000A"}],
            "v435": [{"t": "ONLIN", "_": "0001-3714"}],
        }

    def test_should_return_a_bundle(self):
        journal = conversion.conversion_journal_to_bundle(self.json_journal)
        self.assertEqual(SAMPLE_KERNEL_JOURNAL, journal)

    def test_should_return_a_list_of_bundle(self):
        journals = conversion.conversion_journals_to_kernel([self.json_journal])
        self.assertEqual([SAMPLE_KERNEL_JOURNAL], journals)


class TestProcessingValidation(unittest.TestCase):
    def test_validator_article_xml(self):

        result = validation.validator_article_xml(
            os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml")
        )
        self.assertIn(
            "Element p is not declared in p list of possible children", result.keys()
        )

    def test_validator_article_xml_not_print(self):

        result = validation.validator_article_xml(
            os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml"), False
        )
        self.assertIn(
            "Element p is not declared in p list of possible children", result.keys()
        )

    def test_validator_article_xml_XMLSPSVersionError(self):

        result = validation.validator_article_xml(
            os.path.join(SAMPLES_PATH, "S0102-86501998000100007_invalid.xml")
        )
        self.assertIn(
            "cannot get the SPS version from /article/@specific-use", result.keys()
        )

    def test_validator_article_xml_valid(self):

        result = validation.validator_article_xml(
            os.path.join(SAMPLES_PATH, "0034-8910-rsp-48-2-0347-valid.xml"), False
        )
        self.assertEqual({}, result)

    @patch("documentstore_migracao.processing.validation.validator_article_xml")
    def test_validator_article_ALLxml(self, mk_validator_article_xml):
        mk_validator_article_xml.return_value = {
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
            validation.validator_article_ALLxml()
            mk_validator_article_xml.assert_has_calls(calls, any_order=True)

    @patch("documentstore_migracao.processing.validation.validator_article_xml")
    def test_validator_article_ALLxml_with_exception(self, mk_validator_article_xml):

        mk_validator_article_xml.side_effect = KeyError("Test Error - Validation")
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):

            with self.assertRaises(KeyError) as cm:
                validation.validator_article_ALLxml()

                self.assertEqual("Test Error - Validation", str(cm.exception))


class TestProcessingInserting(unittest.TestCase):
    @patch("documentstore_migracao.processing.inserting.register_document")
    def test_inserting_document_store(self, mk_import_document_by_database):

        session_db = Mock()
        storage = Mock()

        with utils.environ(SPS_PKG_PATH=SAMPLES_PATH):
            inserting.inserting_document_store(session_db, storage)

        mk_import_document_by_database.assert_called_with(ANY, session_db, storage)

    def test_import_document_by_database(self):

        session_db = Mock()
        storage = Mock()
        storage.register().return_value = "http://localhost:9000/img/exemple.jpg"

        inserting.register_document(
            os.path.join(SAMPLES_PATH, "S0044-59672003000300002_sps_completo"),
            session_db,
            storage,
        )

        session_db.documents.add.assert_called_with(data=ANY)
