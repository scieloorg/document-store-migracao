import unittest
from unittest.mock import patch

from documentstore_migracao.main import process, main


class TestMainProcess(unittest.TestCase):
    @patch("documentstore_migracao.processing.extrated.extrated_all_data")
    def test_arg_extrateFiles(self, mk_extrated_all_data):

        process(["--extrateFiles"])
        mk_extrated_all_data.assert_called_once_with()

    @patch("documentstore_migracao.processing.extrated.extrated_selected_journal")
    def test_arg_issn_journal(self, mk_extrated_selected_journal):

        process(["--issn-journal", "1234-5678"])
        mk_extrated_selected_journal.assert_called_once_with("1234-5678")

    @patch("documentstore_migracao.processing.conversion.conversion_article_ALLxml")
    def test_arg_conversionFiles(self, mk_conversion_article_ALLxml):

        process(["--conversionFiles"])
        mk_conversion_article_ALLxml.assert_called_once_with()

    @patch("documentstore_migracao.processing.conversion.conversion_article_xml")
    def test_arg_pathFile(self, mk_conversion_article_xml):

        process(["--convetFile", "/tmp/example.xml"])
        mk_conversion_article_xml.assert_called_once_with("/tmp/example.xml")

    @patch("documentstore_migracao.processing.reading.reading_article_ALLxml")
    def test_arg_readFiles(self, mk_reading_article_ALLxml):

        process(["--readFiles"])
        mk_reading_article_ALLxml.assert_called_once_with()

    @patch("documentstore_migracao.processing.validation.validator_article_ALLxml")
    def test_arg_validationFiles(self, mk_validator_article_ALLxml):

        process(["--validationFiles"])
        mk_validator_article_ALLxml.assert_called_once_with(False, False)

    @patch("documentstore_migracao.processing.generation.article_ALL_html_generator")
    def test_arg_generationFiles(self, mk_article_ALL_html_generator):

        process(["--generationFiles"])
        mk_article_ALL_html_generator.assert_called_once_with()

    @patch("documentstore_migracao.processing.validation.validator_article_xml")
    def test_arg_valideFile(self, mk_validator_article_xml):

        process(["--valideFile", "/tmp/example.xml"])
        mk_validator_article_xml.assert_called_once_with("/tmp/example.xml")

    @patch("documentstore_migracao.processing.reading.reading_article_xml")
    def test_arg_readFile(self, mk_reading_article_xml):

        process(["--readFile", "/tmp/example.xml"])
        mk_reading_article_xml.assert_called_once_with("/tmp/example.xml", False)

    @patch("documentstore_migracao.processing.constructor.article_ALL_constructor")
    def test_arg_constructionFiles(self, mk_article_ALL_constructor):

        process(["--constructionFiles"])
        mk_article_ALL_constructor.assert_called_once_with()

    def test_not_arg(self):

        with self.assertRaises(SystemExit) as cm:
            process([])
            self.assertEqual("Vc deve escolher algum parametro", str(cm.exception))


class TestMainMain(unittest.TestCase):
    @patch("documentstore_migracao.main.process")
    def test_main_process(self, mk_process):

        mk_process.return_value = 0
        self.assertRaises(SystemExit, main)
        mk_process.assert_called_once_with(["test"])
