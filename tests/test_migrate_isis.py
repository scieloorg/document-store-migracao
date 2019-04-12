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


class TestJournalPipeline(unittest.TestCase):
    def setUp(self):
        self.journal_sample_mst = os.path.join(
            SAMPLES_PATH, "base-isis-sample", "title", "title.mst"
        )

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    @mock.patch("documentstore_migracao.processing.pipeline.extract_isis")
    def test_pipeline_must_run_extract_when_it_asked_for(
        self, extract_isis_mock, read_json_file_mock
    ):
        pipeline.import_journals("~/json/title.json")
        read_json_file_mock.assert_called_once_with("~/json/title.json")

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    def test_pipeline_should_log_exceptions(self, read_json_file_mock):
        read_json_file_mock.side_effect = FileNotFoundError

        with self.assertLogs(level="DEBUG") as log:
            pipeline.import_journals("~/json/title.json")
            self.assertIn("DEBUG", log.output[0])


class IsisCommandLineTests(unittest.TestCase):
    @mock.patch("documentstore_migracao.main.extract_isis")
    @mock.patch("documentstore_migracao.main.argparse.ArgumentParser.error")
    def test_extract_subparser_requires_mst_file_path_and_output_file(
        self, error_mock, extract_isis_mock
    ):
        main.migrate_isis("extract".split())
        error_mock.assert_called_with(
            "the following arguments are required: file, --output"
        )

    @mock.patch("documentstore_migracao.main.extract_isis")
    def test_extract_subparser_should_call_extract_isis_command(
        self, extract_isis_mock
    ):
        main.migrate_isis("extract /path/to/file.mst --output /jsons/file.json".split())
        extract_isis_mock.create_output_dir.assert_called_once_with("/jsons/file.json")
        extract_isis_mock.run.assert_called_once_with(
            "/path/to/file.mst", "/jsons/file.json"
        )

    @mock.patch("documentstore_migracao.main.argparse.ArgumentParser.error")
    def test_import_journals_requires_json_path_and_type_of_entity(self, error_mock):
        main.migrate_isis("import".split())
        error_mock.assert_called_with(
            "the following arguments are required: file, --type"
        )

    @mock.patch("documentstore_migracao.main.pipeline.import_journals")
    def test_import_journals_should_call_pipeline(self, import_journals_mock):
        main.migrate_isis("import /jsons/file.json --type journal".split())
        import_journals_mock.assert_called_once_with("/jsons/file.json")

    @mock.patch("documentstore_migracao.main.argparse.ArgumentParser.print_help")
    def test_should_print_help_if_arguments_does_not_match(self, print_help_mock):
        main.migrate_isis([])
        print_help_mock.assert_called()
