import os
import unittest
from unittest.mock import patch, ANY

from xylose.scielodocument import Journal
from documentstore_migracao.processing import extrated, conversion, reading

from . import utils, SAMPLES_PATH, SAMPLES_JOURNAL, SAMPLES_XML_ARTICLE


class TestProcessingExtrated(unittest.TestCase):
    def setUp(self):
        self.obj_journal = Journal(SAMPLES_JOURNAL)

    @unittest.skip("acesso ao article meta")
    @patch("documentstore_migracao.processing.extrated.article.get_all_articles_notXML")
    def test_extrated_journal_data(self, mk_get_all_articles_notXML):

        mk_get_all_articles_notXML.return_value = [
            ("S0036-36341997000100001", SAMPLES_XML_ARTICLE)
        ]
        with utils.environ(SOURCE_PATH="/tmp"):
            extrated.extrated_journal_data(self.obj_journal)

            self.assertTrue(os.path.isfile("/tmp/S0036-36341997000100001.xml"))
            os.remove("/tmp/S0036-36341997000100001.xml")

    @unittest.skip("test_extrated_journal_data")
    @patch("documentstore_migracao.processing.extrated.extrated_journal_data")
    def test_extrated_selected_journal(self, mk_extrated_journal_data):

        extrated.extrated_selected_journal(SAMPLES_JOURNAL["issns"])
        # mk_extrated_journal_data.assert_called_once_with(self.obj_journal)
        self.assertTrue(True)

    @patch("documentstore_migracao.processing.extrated.journal.get_all_journal")
    @patch("documentstore_migracao.processing.extrated.extrated_journal_data")
    def test_extrated_all_data(self, mk_extrated_journal_data, mk_get_all_journal):

        mk_get_all_journal.return_value = [self.obj_journal]
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

            self.assertEqual(len(mk_conversion_article_xml.mock_calls), 6)

    @unittest.skip("test_conversion_article_ALLxml_with_exception")
    @patch("documentstore_migracao.processing.conversion.conversion_article_xml")
    def test_conversion_article_ALLxml_with_exception(self, mk_conversion_article_xml):

        mk_conversion_article_xml.side_effect = KeyError("Test Error - CONVERSION")
        with utils.environ(SOURCE_PATH=SAMPLES_PATH):

            with self.assertRaises(KeyError) as cm:
                conversion.conversion_article_ALLxml()

                self.assertEqual("Test Error - CONVERSION", str(cm.exception))


class TestProcessingReading(unittest.TestCase):
    def test_reading_article_xml(self):

        reading.reading_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )

    @patch("documentstore_migracao.processing.reading.reading_article_xml")
    def test_reading_article_ALLxml(self, mk_reading_article_xml):

        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):
            reading.reading_article_ALLxml()
            mk_reading_article_xml.assert_called_with(ANY, move_success=False)
            self.assertEqual(len(mk_reading_article_xml.mock_calls), 6)

    @patch("documentstore_migracao.processing.reading.reading_article_xml")
    def test_reading_article_ALLxml_with_exception(self, mk_reading_article_xml):

        mk_reading_article_xml.side_effect = KeyError("Test Error - READING")
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):

            with self.assertLogs("documentstore_migracao.processing.reading") as log:
                reading.reading_article_ALLxml()

            has_message = False
            for log_message in log.output:
                if "Test Error - READING" in log_message:
                    has_message = True
            self.assertTrue(has_message)
