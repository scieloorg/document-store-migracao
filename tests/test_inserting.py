import unittest
from unittest.mock import patch
from .apptesting import Session
from . import SAMPLE_ISSUES_KERNEL

import os
import shutil

from documentstore_migracao.processing import inserting
from documentstore_migracao import config
from documentstore.domain import DocumentsBundle


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
        if not os.path.isdir(config.get("ERRORS_PATH")):
            os.makedirs(config.get("ERRORS_PATH"))

    def tearDown(self):
        shutil.rmtree(config.get("ERRORS_PATH"))

    def test_get_documents_bundle(self):
        session_db = Session()
        manifest = inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        session_db.documents_bundles.add(manifest)
        data = dict(
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
        result = inserting.get_documents_bundle(session_db, data)
        self.assertIsInstance(result, DocumentsBundle)
        self.assertEqual(result.id(), "0001-3714-1998-v29-n3")

    def test_get_documents_bundle_not_found(self):
        session_db = Session()
        data = dict(
            [
                ("eissn", "1234-5678"),
                ("pissn", "0003-3714"),
                ("issn", "0987-0987"),
                ("year", "1998"),
                ("volume", "29"),
                ("number", "3"),
                ("supplement", None),
            ]
        )
        self.assertRaises(ValueError, inserting.get_documents_bundle, session_db, data)

    @patch(
        "documentstore_migracao.processing.inserting.link_documents_bundles_with_documents"
    )
    def test_register_documents_in_documents_bundle(
        self, mk_link_documents_bundle_with_documents
    ):
        data1 = dict(
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
