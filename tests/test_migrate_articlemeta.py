import unittest
from unittest.mock import patch

from documentstore_migracao.main.migrate_articlemeta import migrate_articlemeta_parser


class TestMigrateProcess(unittest.TestCase):
    @patch("documentstore_migracao.processing.extrated.extrated_all_data")
    def test_command_extrate(self, mk_extrated_all_data):

        migrate_articlemeta_parser(["extrate"])
        mk_extrated_all_data.assert_called_once_with()

    @patch("documentstore_migracao.processing.extrated.extrated_selected_journal")
    def test_command_extrate_arg_issn_journal(self, mk_extrated_selected_journal):

        migrate_articlemeta_parser(["extrate", "--issn-journal", "1234-5678"])
        mk_extrated_selected_journal.assert_called_once_with("1234-5678")

    @patch("documentstore_migracao.processing.conversion.conversion_article_ALLxml")
    def test_command_conversion(self, mk_conversion_article_ALLxml):

        migrate_articlemeta_parser(["conversion"])
        mk_conversion_article_ALLxml.assert_called_once_with()

    @patch("documentstore_migracao.processing.conversion.conversion_article_xml")
    def test_command_conversion_arg_pathFile(self, mk_conversion_article_xml):

        migrate_articlemeta_parser(["conversion", "--convetFile", "/tmp/example.xml"])
        mk_conversion_article_xml.assert_called_once_with("/tmp/example.xml")

    @patch("documentstore_migracao.processing.validation.validator_article_ALLxml")
    def test_command_validation(self, mk_validator_article_ALLxml):

        migrate_articlemeta_parser(["validation"])
        mk_validator_article_ALLxml.assert_called_once_with(False, False)

    @patch("documentstore_migracao.processing.validation.validator_article_xml")
    def test_command_validation_arg_valideFile(self, mk_validator_article_xml):

        migrate_articlemeta_parser(["validation", "--valideFile", "/tmp/example.xml"])
        mk_validator_article_xml.assert_called_once_with("/tmp/example.xml")

    def test_not_arg(self):

        with self.assertRaises(SystemExit) as cm:
            migrate_articlemeta_parser([])
            self.assertEqual("Vc deve escolher algum parametro", str(cm.exception))
