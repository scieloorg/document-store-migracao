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

        process(["--pathFile", "/tmp/example.xml"])
        mk_conversion_article_xml.assert_called_once_with("/tmp/example.xml")

    @patch("documentstore_migracao.processing.reading.reading_article_ALLxml")
    def test_arg_readFiles(self, mk_reading_article_ALLxml):

        process(["--readFiles"])
        mk_reading_article_ALLxml.assert_called_once_with()


class TestMainMain(unittest.TestCase):
    @patch("documentstore_migracao.main.process")
    def test_main_process(self, mk_process):

        mk_process.return_value = 0
        self.assertRaises(SystemExit, main)
        mk_process.assert_called_once_with(["test"])
