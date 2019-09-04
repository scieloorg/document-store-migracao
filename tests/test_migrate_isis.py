import os
import subprocess
import unittest
from unittest import mock
from documentstore_migracao.utils import extract_isis
from documentstore_migracao.processing import pipeline, conversion
from documentstore_migracao import exceptions, config
from documentstore_migracao.main.migrate_isis import migrate_isis_parser
from .apptesting import Session
from . import (
    SAMPLES_PATH,
    SAMPLE_KERNEL_JOURNAL,
    SAMPLE_ISSUES_JSON,
    SAMPLE_ISSUES_KERNEL,
    SAMPLE_JOURNALS_JSON,
)
from documentstore.exceptions import AlreadyExists


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

        self.session = Session()

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    @mock.patch("documentstore_migracao.processing.pipeline.extract_isis")
    def test_pipeline_should_read_correct_json_file(
        self, extract_isis_mock, read_json_file_mock
    ):
        pipeline.import_journals("~/json/title.json", self.session)
        read_json_file_mock.assert_called_once_with("~/json/title.json")

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    def test_pipeline_should_log_exceptions(self, read_json_file_mock):
        read_json_file_mock.side_effect = FileNotFoundError

        with self.assertLogs(level="DEBUG") as log:
            pipeline.import_journals("~/json/title.json", self.session)
            self.assertIn("DEBUG", log.output[0])

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    @mock.patch(
        "documentstore_migracao.processing.conversion.conversion_journals_to_kernel"
    )
    def test_should_import_journal(self, journals_to_kernel_mock, read_json_mock):
        journals_to_kernel_mock.return_value = [SAMPLE_KERNEL_JOURNAL]
        pipeline.import_journals("~/json/title.json", self.session)

        expected = SAMPLE_KERNEL_JOURNAL["_id"]
        self.assertEqual(expected, self.session.journals.fetch(expected).id())

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    @mock.patch(
        "documentstore_migracao.processing.conversion.conversion_journals_to_kernel"
    )
    def test_should_raise_already_exists_if_insert_journal_with_same_id(
        self, journals_to_kernel_mock, read_json_mock
    ):
        journals_to_kernel_mock.return_value = [SAMPLE_KERNEL_JOURNAL]

        with self.assertLogs(level="INFO") as log:
            pipeline.import_journals("~/json/title.json", self.session)
            pipeline.import_journals("~/json/title.json", self.session)
            self.assertIn("pipeline", log[1][0])

    @mock.patch("documentstore_migracao.processing.reading.read_json_file")
    @mock.patch(
        "documentstore_migracao.processing.conversion.conversion_journals_to_kernel"
    )
    def test_should_add_journal_in_changes(
        self, journals_to_kernel_mock, read_json_mock
    ):
        journals_to_kernel_mock.return_value = [SAMPLE_KERNEL_JOURNAL]
        pipeline.import_journals("~/json/title.json", self.session)

        _id_expected = SAMPLE_KERNEL_JOURNAL["id"]
        _changes = self.session.changes.filter()

        self.assertEqual(1, len(_changes))
        self.assertEqual(_id_expected, _changes[0]["id"])


class IsisCommandLineTests(unittest.TestCase):
    def setUp(self):
        self.session = Session

    @mock.patch("documentstore_migracao.main.migrate_isis.extract_isis")
    @mock.patch(
        "documentstore_migracao.main.migrate_isis.argparse.ArgumentParser.error"
    )
    def test_extract_subparser_requires_mst_file_path_and_output_file(
        self, error_mock, extract_isis_mock
    ):
        migrate_isis_parser("extract".split())
        error_mock.assert_called_with(
            "the following arguments are required: file, --output"
        )

    @mock.patch("documentstore_migracao.main.migrate_isis.extract_isis")
    def test_extract_subparser_should_call_extract_isis_command(
        self, extract_isis_mock
    ):
        migrate_isis_parser(
            "extract /path/to/file.mst --output /jsons/file.json".split()
        )
        extract_isis_mock.create_output_dir.assert_called_once_with("/jsons/file.json")
        extract_isis_mock.run.assert_called_once_with(
            "/path/to/file.mst", "/jsons/file.json"
        )

    @mock.patch(
        "documentstore_migracao.main.migrate_isis.argparse.ArgumentParser.error"
    )
    def test_import_journals_requires_json_path_and_type_of_entity(self, error_mock):
        migrate_isis_parser("import".split())
        error_mock.assert_called_with(
            "the following arguments are required: --uri, --db, file, --type"
        )

    @mock.patch("documentstore_migracao.main.migrate_isis.pipeline.import_journals")
    def test_import_journals_should_call_pipeline(self, import_journals_mock):
        migrate_isis_parser(
            """import /jsons/file.json --type journal
            --uri mongodb://uri --db db-name""".split()
        )
        import_journals_mock.assert_called_once()

    @mock.patch(
        "documentstore_migracao.main.migrate_isis.argparse.ArgumentParser.print_help"
    )
    def test_should_print_help_if_arguments_does_not_match(self, print_help_mock):
        migrate_isis_parser([])
        print_help_mock.assert_called()

    @mock.patch("documentstore_migracao.main.migrate_isis.pipeline.import_issues")
    def test_import_should_call_issues_pipeline_when_import_type_is_issue(
        self, import_issues_mock
    ):
        migrate_isis_parser(
            """import /jsons/file.json --type issue
            --uri mongodb://uri --db db-name""".split()
        )
        import_issues_mock.assert_called_once()

    @mock.patch(
        "documentstore_migracao.main.migrate_isis.pipeline.import_documents_bundles_link_with_journal"
    )
    def test_import_should_import_linked_journals_bundles(
        self, import_documents_bundles_link_with_journal_mock
    ):
        migrate_isis_parser(
            """import /jsons/file.json --type documents-bundles-link
            --uri mongodb://uri --db db-name""".split()
        )

        import_documents_bundles_link_with_journal_mock.assert_called_once()

    @mock.patch(
        "documentstore_migracao.processing.pipeline.link_documents_bundles_with_journals"
    )
    @mock.patch(
        "documentstore_migracao.main.migrate_isis.argparse.ArgumentParser.error"
    )
    def test_merge_subparser_requires_json_paths_and_output_file(
        self, error_mock, link_documents_bundles_with_journals_mock
    ):
        migrate_isis_parser("link".split())
        error_mock.assert_called_with(
            "the following arguments are required: issues, --output"
        )

    @mock.patch(
        "documentstore_migracao.processing.pipeline.link_documents_bundles_with_journals"
    )
    def test_link_command_should_link_journals_and_bundles(
        self, link_documents_bundles_with_journals_mock
    ):
        migrate_isis_parser("""link issues.json --output linked.json""".split())

        link_documents_bundles_with_journals_mock.assert_called_once_with(
            "issues.json", "linked.json"
        )


class TestIssuePipeline(unittest.TestCase):
    def setUp(self):
        self.issues_json = [
            {
                "v32": [{"_": "5"}],
                "v31": [{"_": "40"}],
                "v35": [{"_": "2448-167X"}],
                "v41": [{"_": "pr"}],
                "v65": [{"_": "20190129"}],
            },
            {
                "v32": [{"_": "ahead"}],
                "v31": [{"_": "40"}],
                "v35": [{"_": "2448-167X"}],
                "v65": [{"_": "20190129"}],
            },
        ]

        self.session = Session()

    def test_filter_should_remove_pressreleases_and_ahead_issues(self):
        issues = conversion.conversion_issues_to_xylose(self.issues_json)
        issues = pipeline.filter_issues(issues)
        self.assertEqual(0, len(issues))

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_pipeline_should_read_correct_json_file(self, read_json_file_mock):
        pipeline.import_issues("~/json/issues.json", self.session)
        read_json_file_mock.assert_called_once_with("~/json/issues.json")

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_pipeline_should_insert_issue_in_database_and_register_change(
        self, read_json_file_mock
    ):
        read_json_file_mock.return_value = SAMPLE_ISSUES_JSON
        pipeline.import_issues("~/json/issues.json", self.session)
        expected = SAMPLE_ISSUES_KERNEL[0]["_id"]

        self.assertEqual(expected, self.session.documents_bundles.fetch(expected).id())

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_should_insert_issue_in_changes(self, read_json_file_mock):
        read_json_file_mock.return_value = SAMPLE_ISSUES_JSON
        pipeline.import_issues("~/json/issues.json", self.session)
        _changes = self.session.changes.filter()

        self.assertEqual(1, len(_changes))
        self.assertEqual("0001-3714-1998-v29-n3", _changes[0]["id"])

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_should_raise_already_exception_if_try_to_insert_same_id_twice(
        self, read_json_file_mock
    ):
        read_json_file_mock.return_value = SAMPLE_ISSUES_JSON

        with self.assertLogs(level="INFO") as log:
            pipeline.import_issues("~/json/issues.json", self.session)
            pipeline.import_issues("~/json/issues.json", self.session)
            self.assertIn("pipeline", log[1][0])


class TestLinkDocumentsBundlesWithJournals(unittest.TestCase):
    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    @mock.patch(
        "documentstore_migracao.processing.pipeline.extract_isis.create_output_dir"
    )
    @mock.patch("builtins.open")
    def test_should_create_output_folder(
        self, open_mock, create_output_dir_mock, read_json_file_mock
    ):

        read_json_file_mock.return_value = []
        pipeline.link_documents_bundles_with_journals(
            "~/issues.json", "~/json/output.json"
        )
        create_output_dir_mock.return_value = None
        create_output_dir_mock.assert_called_once()

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    @mock.patch(
        "documentstore_migracao.processing.pipeline.extract_isis.create_output_dir"
    )
    @mock.patch("builtins.open")
    def test_should_read_issues(
        self, open_mock, create_output_dir_mock, read_json_file_mock
    ):
        read_json_file_mock.side_effect = [SAMPLE_ISSUES_JSON]
        pipeline.link_documents_bundles_with_journals(
            "~/issues.json", "~/json/output.json"
        )
        self.assertEqual(1, read_json_file_mock.call_count)

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    @mock.patch(
        "documentstore_migracao.processing.pipeline.extract_isis.create_output_dir"
    )
    @mock.patch("builtins.open")
    def test_should_write_output_file(
        self, open_mock, create_output_dir_mock, read_json_file_mock
    ):
        read_json_file_mock.side_effect = [SAMPLE_ISSUES_JSON]
        open_mock.side_effect = mock.mock_open()

        pipeline.link_documents_bundles_with_journals(
            "~/issues.json", "~/json/output.json"
        )

        open_mock.assert_called_once_with("~/json/output.json", "w")
        open_mock = open_mock()
        open_mock.write.assert_called_once()
        self.assertIn("0001-3714", str(open_mock.write.call_args))


class TestImportDocumentsBundlesLink(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.session.journals.add(
            pipeline.ManifestDomainAdapter(manifest=SAMPLE_KERNEL_JOURNAL)
        )

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_read_journal_bundle_file(self, read_json_file_mock):
        read_json_file_mock.return_value = {}
        pipeline.import_documents_bundles_link_with_journal(
            "~/json/output.json", self.session
        )
        read_json_file_mock.assert_called_once_with("~/json/output.json")

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_should_update_journals_with_document_bundle_ids(self, read_json_file_mock):
        read_json_file_mock.return_value = {
            "0001-3714": [
                {
                    "id": "0034-8910-1978-v12-n2",
                    "number": "2",
                    "order": "2",
                    "supplement": "",
                    "volume": "12",
                    "year": "1978",
                }
            ]
        }

        pipeline.import_documents_bundles_link_with_journal(
            "~/json/output.json", self.session
        )
        _journal = self.session.journals.fetch("0001-3714")
        _changes = self.session.changes.filter()

        self.assertIn(
            {
                "id": "0034-8910-1978-v12-n2",
                "number": "2",
                "order": "2",
                "supplement": "",
                "volume": "12",
                "year": "1978",
            },
            _journal.issues,
        )
        self.assertEqual(1, len(_changes))

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_should_not_update_journals_with_document_bundle(self, read_json_file_mock):
        read_json_file_mock.return_value = {"0001-3714": []}

        pipeline.import_documents_bundles_link_with_journal(
            "~/json/output.json", self.session
        )
        _journal = self.session.journals.fetch("0001-3714")

        self.assertEqual([], _journal.issues)

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_should_not_update_journals_with_duplicated_bundles(
        self, read_json_file_mock
    ):
        read_json_file_mock.return_value = {
            "0001-3714": [
                {
                    "id": "issue-1",
                    "order": "0001",
                    "number": "01",
                    "volume": "01",
                    "year": "2019",
                    "supplement": "supplement",
                },
                {
                    "id": "issue-2",
                    "order": "0002",
                    "number": "02",
                    "volume": "02",
                    "year": "2019",
                    "supplement": "supplement",
                },
                {
                    "id": "issue-2",
                    "order": "0002",
                    "number": "02",
                    "volume": "02",
                    "year": "2019",
                    "supplement": "supplement",
                },
            ]
        }
        pipeline.import_documents_bundles_link_with_journal(
            "~/json/output.json", self.session
        )
        _journal = self.session.journals.fetch("0001-3714")

        self.assertEqual(
            [
                {
                    "id": "issue-1",
                    "order": "0001",
                    "number": "01",
                    "volume": "01",
                    "year": "2019",
                    "supplement": "supplement",
                },
                {
                    "id": "issue-2",
                    "order": "0002",
                    "number": "02",
                    "volume": "02",
                    "year": "2019",
                    "supplement": "supplement",
                },
            ],
            _journal.issues,
        )

    @mock.patch("documentstore_migracao.processing.pipeline.reading.read_json_file")
    def test_should_log_dabase_exceptions(self, read_json_file_mock):
        read_json_file_mock.side_effect = [
            {
                "0001-3714": [
                    {
                        "id": "issue-1",
                        "order": "0001",
                        "number": "01",
                        "volume": "01",
                        "year": "2019",
                        "supplement": "supplement",
                    },
                    {
                        "id": "issue-1",
                        "order": "0001",
                        "number": "01",
                        "volume": "01",
                        "year": "2019",
                        "supplement": "supplement",
                    },
                    {
                        "id": "issue-2",
                        "order": "0002",
                        "number": "02",
                        "volume": "02",
                        "year": "2019",
                        "supplement": "supplement",
                    },
                ]
            },
            {"missing-journal": []},
        ]

        with self.assertLogs(level="DEBUG") as log:
            pipeline.import_documents_bundles_link_with_journal(
                "~/json/output.json", self.session
            )
            self.assertIn(
                "Bundle issue-1 already exists in journal 0001-3714", log[-1][-1]
            )

        with self.assertLogs(level="DEBUG") as log:
            pipeline.import_documents_bundles_link_with_journal(
                "~/json/output.json", self.session
            )
            self.assertIn(
                "Journal missing-journal does not exists, cannot link bundles.",
                log[-1][-1],
            )
