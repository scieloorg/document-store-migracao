import os
import unittest
from unittest.mock import patch, ANY

from xylose.scielodocument import Journal, Article
from documentstore_migracao.processing import extrated, conversion, reading, generation

from . import utils, SAMPLES_PATH, SAMPLES_JOURNAL, SAMPLES_XML_ARTICLE, SAMPLES_ARTICLE


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

            self.assertEqual(len(mk_conversion_article_xml.mock_calls), 7)

    @patch("documentstore_migracao.processing.conversion.conversion_article_xml")
    def test_conversion_article_ALLxml_with_exception(self, mk_conversion_article_xml):

        mk_conversion_article_xml.side_effect = KeyError("Test Error - CONVERSION")
        with utils.environ(SOURCE_PATH=SAMPLES_PATH):

            conversion.conversion_article_ALLxml()
            # with self.assertRaises(KeyError) as cm:
            #     conversion.conversion_article_ALLxml()
            #     self.assertEqual("Test Error - CONVERSION", str(cm.exception))


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
            self.assertEqual(len(mk_reading_article_xml.mock_calls), 7)

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


class TestProcessingGeneration(unittest.TestCase):
    def test_article_html_generator(self):

        with utils.environ(GENERATOR_PATH="/tmp"):
            filename = "/tmp/S0044-59672003000300001.pt.pt.html"
            try:
                generation.article_html_generator(
                    os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml")
                )
                with open(filename, "r") as f:
                    text = f.read()

            finally:
                os.remove(filename)

            self.assertIn("S0044-59672003000300001", text)

    @patch("documentstore_migracao.processing.generation.article_html_generator")
    def test_reading_article_ALLxml(self, mk_article_html_generator):

        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):
            generation.article_ALL_html_generator()
            mk_article_html_generator.assert_called_with(ANY)
            self.assertEqual(len(mk_article_html_generator.mock_calls), 7)

    @patch("documentstore_migracao.processing.generation.article_html_generator")
    def test_reading_article_ALLxml_with_exception(self, mk_article_html_generator):

        mk_article_html_generator.side_effect = KeyError("Test Error - Generation")
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH):

            with self.assertLogs("documentstore_migracao.processing.generation") as log:
                generation.article_ALL_html_generator()

            has_message = False
            for log_message in log.output:
                if "Test Error - Generation" in log_message:
                    has_message = True
            self.assertTrue(has_message)
