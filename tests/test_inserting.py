import unittest
from unittest.mock import patch, Mock, MagicMock, ANY, call
from copy import deepcopy
from .apptesting import Session
from . import (
    SAMPLE_ISSUES_KERNEL,
    SAMPLE_AOPS_KERNEL,
    SAMPLE_KERNEL_JOURNAL,
    SAMPLES_PATH,
)

import os
import shutil

from documentstore_migracao.processing import inserting
from documentstore_migracao.utils import manifest
from documentstore_migracao import config
from documentstore.domain import DocumentsBundle
from documentstore.exceptions import DoesNotExist


class TestLinkDocumentsBundleWithDocuments(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        manifest = inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        self.session.documents_bundles.add(manifest)
        self.documents_bundle = self.session.documents_bundles.fetch(manifest.id())

    def test_should_link_documents_bundle_with_documents(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle, ["doc-1", "doc-2"], self.session
        )

        self.assertEqual(["doc-1", "doc-2"], self.documents_bundle.documents)

    def test_should_not_insert_duplicated_documents(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle, ["doc-1", "doc-1"], self.session
        )

        self.assertEqual(["doc-1"], self.documents_bundle.documents)

    def test_should_register_changes(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle, ["doc-1", "doc-2"], self.session
        )

        _changes = self.session.changes.filter()

        self.assertEqual(1, len(_changes))
        self.assertEqual(self.documents_bundle.id(), _changes[0]["id"])
        self.assertEqual("DocumentsBundle", _changes[0]["entity"])


class TestProcessingInserting(unittest.TestCase):
    def setUp(self):
        self.data = dict(
            [
                ("eissn", "1234-5678"),
                ("pissn", "0001-3714"),
                ("issn", "0987-0987"),
                ("year", "1998"),
                ("volume", "29"),
                ("number", "3"),
                ("supplement", None),
            ]
        )
        self.aop_data = dict(
            [
                ("eissn", "0001-3714"),
                ("issn", "0001-3714"),
                ("year", "2019"),
            ]
        )
        if not os.path.isdir(config.get("ERRORS_PATH")):
            os.makedirs(config.get("ERRORS_PATH"))

    def tearDown(self):
        shutil.rmtree(config.get("ERRORS_PATH"))

    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.issue_id"
    )
    def test_get_documents_bundle_uses_scielo_ids_generator_issue_id_if_issue(
        self, mk_issue_bundle_id
    ):
        result = inserting.get_documents_bundle(MagicMock(), self.data)
        mk_issue_bundle_id.assert_called_with(
            ANY,
            self.data["year"],
            self.data["volume"],
            self.data["number"],
            self.data["supplement"],
        )

    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.aops_bundle_id"
    )
    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.issue_id"
    )
    def test_get_documents_bundle_uses_scielo_ids_generator_aops_bundle_id_if_aop(
        self, mk_issue_bundle_id, mk_aops_bundle_id
    ):
        result = inserting.get_documents_bundle(MagicMock(), self.aop_data)
        mk_aops_bundle_id.assert_called()
        mk_issue_bundle_id.assert_not_called()

    def test_get_documents_bundle_success(self):
        session_db = Session()
        session_db.documents_bundles.add(
            inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        )
        session_db.documents_bundles.add(
            inserting.ManifestDomainAdapter(SAMPLE_AOPS_KERNEL[0])
        )
        result = inserting.get_documents_bundle(session_db, self.data)
        self.assertIsInstance(result, DocumentsBundle)
        self.assertEqual(result.id(), "0001-3714-1998-v29-n3")

    def test_get_documents_bundle_raises_exception_if_issue_and_not_found(self):
        session_db = MagicMock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        self.assertRaises(
            ValueError, inserting.get_documents_bundle, session_db, self.data
        )

    @patch("documentstore_migracao.processing.inserting.create_aop_bundle")
    def test_get_documents_bundle_creates_aop_bundle_is_aop_and_not_found(
        self, mk_create_aop_bundle
    ):
        issns = ["1234-0001", "1234-0002", "1234-0003"]
        data = {
            "eissn": issns[0],
            "pissn": issns[1],
            "issn": issns[2],
            "year": "2019",
        }
        session_db = MagicMock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        mk_create_aop_bundle.side_effect = DoesNotExist
        self.assertRaises(
            ValueError, inserting.get_documents_bundle, session_db, data
        )
        mk_create_aop_bundle.assert_has_calls(
            [call(session_db, issn) for issn in issns], True
        )

    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.aops_bundle_id"
    )
    @patch("documentstore_migracao.processing.inserting.create_aop_bundle")
    def test_get_documents_bundle_raises_exception_if_creates_aop_bundle_none(
        self, mk_create_aop_bundle, mk_aops_bundle_id
    ):
        session_db = MagicMock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        mk_create_aop_bundle.side_effect = DoesNotExist
        self.assertRaises(
            ValueError,
            inserting.get_documents_bundle,
            session_db,
            self.aop_data
        )

    @patch("documentstore_migracao.processing.inserting.create_aop_bundle")
    def test_get_documents_bundle_returns_created_aop_bundle(
        self, mk_create_aop_bundle
    ):
        session_db = MagicMock()
        mocked_aop_bundle = Mock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        mk_create_aop_bundle.return_value = mocked_aop_bundle
        result = inserting.get_documents_bundle(session_db, self.aop_data)
        self.assertEqual(result, mocked_aop_bundle)

    def test_create_aop_bundle_gets_journal(
        self
    ):
        issn = "1234-0001"
        session_db = MagicMock()
        inserting.create_aop_bundle(session_db, issn)
        session_db.journals.fetch.assert_called_once_with(issn)

    def test_create_aop_bundle_raises_exception_if_journal_not_found(
        self
    ):
        issn = "1234-0001"
        session_db = MagicMock()
        session_db.journals.fetch.side_effect = DoesNotExist
        self.assertRaises(
            DoesNotExist,
            inserting.create_aop_bundle,
            session_db,
            issn
        )

    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.aops_bundle_id"
    )
    def test_create_aop_bundle_uses_scielo_ids_generator_aops_bundle_id(
        self, mk_aops_bundle_id
    ):
        session_db = MagicMock()
        session_db.journals.fetch.return_value = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        inserting.create_aop_bundle(session_db, "0001-3714")
        mk_aops_bundle_id.assert_called_once_with("0001-3714")

    @patch("documentstore_migracao.processing.inserting.utcnow")
    @patch("documentstore_migracao.processing.inserting.ManifestDomainAdapter")
    def test_create_aop_bundle_registers_aop_bundle(
        self, MockManifestDomainAdapter, mk_utcnow
    ):
        mk_utcnow.return_value = "2019-01-02T05:00:00.000000Z"
        expected = {
            "_id" : "0001-3714-aop",
            "created" : "2019-01-02T05:00:00.000000Z",
            "updated" : "2019-01-02T05:00:00.000000Z",
            "items" : [],
            "metadata" : {},
            "id" : "0001-3714-aop",
        }
        mk_bundle_manifest = Mock()
        MockManifestDomainAdapter.return_value = mk_bundle_manifest
        session_db = MagicMock()
        session_db.journals.fetch.return_value = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        MockManifestDomainAdapter.assert_any_call(manifest=expected)
        session_db.documents_bundles.add.assert_called_once_with(data=mk_bundle_manifest)
        session_db.changes.add.assert_any_call(
            {
                "timestamp": "2019-01-02T05:00:00.000000Z",
                "entity": "DocumentsBundle",
                "id": "0001-3714-aop",
            }
        )

    @patch("documentstore_migracao.processing.inserting.utcnow")
    def test_create_aop_bundle_links_aop_bundle_to_journal(
        self, mk_utcnow
    ):
        mk_utcnow.return_value = "2019-01-02T05:00:00.000000Z"
        mocked_journal_data = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        mk_bundle_manifest = Mock()
        session_db = MagicMock()
        session_db.journals.fetch.return_value = mocked_journal_data
        inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        session_db.journals.update.assert_called()
        session_db.changes.add.assert_any_call(
            {
                "timestamp": "2019-01-02T05:00:00.000000Z",
                "entity": "journal",
                "id": SAMPLE_KERNEL_JOURNAL["id"],
            }
        )
        self.assertEqual(mocked_journal_data.ahead_of_print_bundle, "0001-3714-aop")

    def test_create_aop_bundle_returns_bundle(self):
        session_db = Session()
        mocked_journal_data = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        session_db.journals.add(mocked_journal_data)
        result = inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        self.assertIsInstance(result, DocumentsBundle)
        self.assertEqual(result.id(), "0001-3714-aop")

    @patch(
        "documentstore_migracao.processing.inserting.link_documents_bundles_with_documents"
    )
    def test_register_documents_in_documents_bundle(
        self, mk_link_documents_bundle_with_documents
    ):
        data1 = self.data
        data2 = dict(
            [
                ("eissn", "0003-3714"),
                ("issn", "0003-3714"),
                ("year", "1998"),
                ("volume", "29"),
                ("number", "3"),
                ("supplement", None),
            ]
        )
        documents_sorted_in_bundles = {
            "0001-3714-1998-29-03": {
                "items": ["0001-3714-1998-v29-n3-01", "0001-3714-1998-v29-n3-02"],
                "data": data1,
            },
            "0003-3714-1998-29-03": {
                "items": ["0003-3714-1998-v29-n3-01", "0003-3714-1998-v29-n3-02"],
                "data": data2,
            },
        }

        err_filename = os.path.join(
            config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
        )

        session_db = Session()
        manifest = inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        session_db.documents_bundles.add(manifest)

        inserting.register_documents_in_documents_bundle(
            session_db, documents_sorted_in_bundles
        )

        self.assertEqual(os.path.isfile(err_filename), True)
        with open(err_filename) as fp:
            content = fp.read()

            self.assertEqual(content, "0003-3714-1998-29-03\n")

    @patch("documentstore_migracao.processing.inserting.get_documents_bundle")
    def test_register_documents_in_documents_bundle_get_aop_bundle(
        self, mk_get_documents_bundle
    ):
        documents_sorted_in_bundles = {
            "0001-3714-1998-29-03": {
                "items": ["0001-3714-1998-v29-n3-01", "0001-3714-1998-v29-n3-02"],
                "data": self.data,
            },
            "0003-3714-aop": {
                "items": ["0003-3714-aop-01", "0003-3714-aop-02"],
                "data": self.aop_data,
            },
        }
        session_db = Session()
        inserting.register_documents_in_documents_bundle(
            session_db, documents_sorted_in_bundles
        )
        mk_get_documents_bundle.assert_any_call(
            session_db, self.data
        )
        mk_get_documents_bundle.assert_any_call(
            session_db, self.aop_data
        )


class TestDocumentManifest(unittest.TestCase):
    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def setUp(self, mock_minio_storage):
        self.package_path = os.path.join(SAMPLES_PATH, "S0036-36342008000100001")
        self.renditions_names = ["a01v50n1.html", "a01v50n1.pdf"]
        self.renditions_urls_mock = [
            "prefix/some-md5-hash-1.html",
            "prefix/some-md5-hash-2.pdf",
        ]

        mock_minio_storage.register.side_effect = self.renditions_urls_mock
        self.renditions = inserting.get_document_renditions(
            self.package_path, self.renditions_names, "prefix", mock_minio_storage
        )

    def test_rendition_should_contains_file_name(self):
        self.assertEqual("a01v50n1.html", self.renditions[0]["filename"])
        self.assertEqual("a01v50n1.pdf", self.renditions[1]["filename"])

    def test_rendition_should_contains_url_link(self):
        self.assertEqual(self.renditions_urls_mock[0], self.renditions[0]["url"])
        self.assertEqual(self.renditions_urls_mock[1], self.renditions[1]["url"])

    def test_rendition_should_contains_size_bytes(self):
        self.assertEqual(5, self.renditions[0]["size_bytes"])
        self.assertEqual(111671, self.renditions[1]["size_bytes"])

    def test_rendition_should_contains_mimetype(self):
        self.assertEqual("text/html", self.renditions[0]["mimetype"])
        self.assertEqual("application/pdf", self.renditions[1]["mimetype"])
