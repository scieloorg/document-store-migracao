import unittest
from unittest.mock import patch

from documentstore_migracao.main import main, main_migrate_isis


class TestMain(unittest.TestCase):
    @patch("documentstore_migracao.main.migrate_articlemeta_parser")
    def test_main_migrate_articlemeta_parser(self, mk_process):

        mk_process.return_value = 0
        self.assertRaises(SystemExit, main)
        mk_process.assert_called_once_with(["test"])

    @patch("documentstore_migracao.main.migrate_isis_parser")
    def test_main_migrate_isis_parser(self, mk_process):

        mk_process.return_value = 0
        self.assertRaises(SystemExit, main_migrate_isis)
        mk_process.assert_called_once_with(["test"])
