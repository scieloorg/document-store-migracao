import unittest
from unittest import mock
from documentstore_migracao.export import issue
from documentstore_migracao.processing import pipeline
from documentstore_migracao import exceptions
from .utils import environ
from . import SAMPLES_PATH


class TestIssuePipeline(unittest.TestCase):
    @mock.patch("documentstore_migracao.processing.reading.read_issues_from_json")
    @mock.patch("documentstore_migracao.export.issue.extract_isis")
    def test_pipeline_must_run_extract_when_it_asked_for(
        self, extract_isis_mock, read_issues_from_json_mock
    ):
        pipeline.process_isis_issue(extract=True)
        extract_isis_mock.run.assert_called_once_with(base="issue")
        read_issues_from_json_mock.assert_called_once()

    @mock.patch("documentstore_migracao.processing.reading.read_issues_from_json")
    @mock.patch("documentstore_migracao.export.issue.extract_isis")
    def test_pipeline_does_not_run_extract_when_it_doesnt_asked_for(
        self, extract_isis_mock, read_issues_from_json_mock
    ):
        pipeline.process_isis_issue(extract=False)
        extract_isis_mock.run.assert_not_called()
        read_issues_from_json_mock.assert_called_once()

    @mock.patch("documentstore_migracao.export.issue.extract_issues_from_isis")
    def test_execution_stops_if_program_raises_extract_exception(
        self, extract_isis_mock
    ):
        extract_isis_mock.side_effect = exceptions.ExtractError

        with self.assertRaises(SystemExit):
            pipeline.process_isis_issue(extract=True)

    @mock.patch("documentstore_migracao.export.issue.extract_issues_from_isis")
    def test_execution_stops_if_program_raises_fetchenvvariabl_exception(
        self, extract_isis_mock
    ):
        extract_isis_mock.side_effect = exceptions.FetchEnvVariableError

        with self.assertRaises(SystemExit):
            pipeline.process_isis_issue(extract=True)

    @mock.patch("documentstore_migracao.processing.reading.read_issues_from_json")
    def test_log_if_processing_file_does_not_exists(self, read_issues_from_json_mock):
        read_issues_from_json_mock.side_effect = FileNotFoundError

        with self.assertLogs(level="ERROR") as log:
            pipeline.process_isis_issue(extract=False)
            self.assertIn("ERROR", log.output[0])
