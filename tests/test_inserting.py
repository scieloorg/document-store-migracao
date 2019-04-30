import unittest
from unittest import mock
from documentstore_migracao.processing import inserting
from .apptesting import Session
from . import SAMPLE_ISSUES_KERNEL


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
