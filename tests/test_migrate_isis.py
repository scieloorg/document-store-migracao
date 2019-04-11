import os
import subprocess
import unittest
from unittest import mock
from documentstore_migracao.utils import extract_isis
from documentstore_migracao.processing import pipeline
from documentstore_migracao import exceptions, main, config
from . import SAMPLES_PATH


class ExtractIsisTests(unittest.TestCase):
    @mock.patch("documentstore_migracao.utils.extract_isis.subprocess")
    def test_should_raise_file_not_found_exception(self, subprocess_mock):
        subprocess_mock.run.side_effect = FileNotFoundError

        with self.assertRaises(exceptions.ExtractError):
            extract_isis.run("file.mst", "file.json")

    @mock.patch("documentstore_migracao.utils.extract_isis.subprocess")
    def test_extract_isis_should_log_steps(self, subprocess_mock):
        with self.assertLogs(level="DEBUG") as log:
            extract_isis.run("file.mst", "file.json")
            self.assertEqual(2, len(log.output))
            self.assertIn("Extracting database file: file.mst", log.output[0])
            self.assertIn(
                "Writing extracted result as JSON file in: file.json", log.output[1]
            )

    @mock.patch("documentstore_migracao.utils.extract_isis.subprocess")
    def teste_should_raise_called_process_erro(self, subprocess_mock):
        subprocess_mock.run.side_effect = subprocess.CalledProcessError(1, 2)

        with self.assertRaises(exceptions.ExtractError):
            extract_isis.run("file.mst", "file.json")

    @mock.patch("documentstore_migracao.utils.extract_isis.os.makedirs")
    @mock.patch("documentstore_migracao.utils.extract_isis.os.path.exists")
    def test_should_create_an_output_dir(self, path_exists_mock, makedirs_mock):
        path_exists_mock.return_value = False
        extract_isis.create_output_dir("/random/dir/file.json")
        makedirs_mock.assert_called_once_with("/random/dir")

    @mock.patch("documentstore_migracao.utils.extract_isis.os.makedirs")
    @mock.patch("documentstore_migracao.utils.extract_isis.os.path.exists")
    def test_should_not_try_to_create_an_existing_dir(
        self, path_exists_mock, makedirs_mock
    ):
        path_exists_mock.return_value = True
        extract_isis.create_output_dir("/random/dir/file.json")
        makedirs_mock.assert_not_called()
