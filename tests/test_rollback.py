from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch

import pymongo
from documentstore import exceptions as ds_exceptions
from documentstore import domain as ds_domain

from documentstore_migracao import exceptions
from documentstore_migracao.processing import rollback
from tests import SAMPLES_PATH


class TestDocumentStore(TestCase):
    def setUp(self):
        self.DBCollectionMock = MagicMock()

    def test_rollback_does_not_exist(self):
        self.DBCollectionMock.delete_one.side_effect = pymongo.errors.PyMongoError
        _document_store = rollback.DocumentStore(self.DBCollectionMock)
        with self.assertRaises(ds_exceptions.DoesNotExist) as exc_info:
            _document_store.rollback("document-id")
        self.assertIn(
            'Could not remove data with "{\'_id\': \'document-id\'}": ',
            str(exc_info.exception)
        )

    def test_rollback_deletion_failed(self):
        _command_result = Mock(deleted_count=0)
        self.DBCollectionMock.delete_one.return_value = _command_result
        _document_store = rollback.DocumentStore(self.DBCollectionMock)
        with self.assertRaises(ds_exceptions.DoesNotExist) as exc_info:
            _document_store.rollback("document-id")
        self.assertIn(
            'Could not remove data with "{\'_id\': \'document-id\'}": ',
            str(exc_info.exception)
        )

    def test_rollback_ok(self):
        _command_result = Mock(deleted_count=1)
        self.DBCollectionMock.delete_one.return_value = _command_result
        _document_store = rollback.DocumentStore(self.DBCollectionMock)
        _document_store.rollback("document-id")
        self.DBCollectionMock.delete_one.assert_called_once_with({"_id": "document-id"})


class TestChangesStore(TestCase):
    def setUp(self):
        self.DBCollectionMock = MagicMock()

    def test_rollback_does_not_exist(self):
        self.DBCollectionMock.delete_many.side_effect = pymongo.errors.PyMongoError
        _change_store = rollback.ChangesStore(self.DBCollectionMock)
        with self.assertRaises(ds_exceptions.DoesNotExist) as exc_info:
            _change_store.rollback("document-id")
        self.assertIn(
            'Could not remove data with "{\'id\': \'document-id\'}": ',
            str(exc_info.exception)
        )

    def test_rollback_deletion_failed(self):
        _command_result = Mock(deleted_count=0)
        self.DBCollectionMock.delete_many.return_value = _command_result
        _change_store = rollback.ChangesStore(self.DBCollectionMock)
        with self.assertRaises(ds_exceptions.DoesNotExist) as exc_info:
            _change_store.rollback("document-id")
        self.assertIn(
            'Could not remove data with "{\'id\': \'document-id\'}": ',
            str(exc_info.exception)
        )

    def test_rollback_ok(self):
        _command_result = Mock(deleted_count=1)
        self.DBCollectionMock.delete_many.return_value = _command_result
        _change_store = rollback.ChangesStore(self.DBCollectionMock)
        _change_store.rollback("document-id")
        self.DBCollectionMock.delete_many.assert_called_once_with({"id": "document-id"})


class TestRollbackSession(TestCase):

    def setUp(self):
        self.mongo_client = Mock()
        self.session = rollback.RollbackSession(self.mongo_client)

    def test_changes(self):
        self.assertIsInstance(self.session.changes, rollback.ChangesStore)

    def test_documents(self):
        self.assertIsInstance(self.session.documents, rollback.DocumentStore)


class TestRollbackBundle(TestCase):

    def setUp(self):
        self.session = Mock(spec=rollback.RollbackSession)
        self.fake_journals = rollback.get_journals_from_json(
            SAMPLES_PATH + "/base-isis-sample/title/title.json"
        )

    def test_raises_error_if_document_issn_not_found(self):
        doc_info = {
            "pid_v3": "document-id",
            "eissn": "2179-8087",
            "pissn": "1415-0980",
            "issn": "1415-0980",
            "pid": "document-pid-v2",
            "year": "2020",
            "volume": "1",
            "number": "2",
        }

        with self.assertRaises(exceptions.RollbackError) as exc_info:
            rollback.rollback_bundle(doc_info, self.session, self.fake_journals)
        self.assertEqual(
            'could not get journal for document "document-id"', str(exc_info.exception)
        )

    def test_raises_error_if_bundle_not_found(self):
        self.session.documents_bundles.fetch.side_effect = ds_exceptions.DoesNotExist
        doc_info = {
            "pid_v3": "document-id",
            "eissn": "2317-6326",
            "pissn": "0102-6720",
            "issn": "0102-6720",
            "pid": "document-pid-v2",
            "year": "2020",
            "volume": "1",
            "number": "2",
        }

        with self.assertRaises(exceptions.RollbackError) as exc_info:
            rollback.rollback_bundle(doc_info, self.session, self.fake_journals)
        self.assertEqual(
            'could not get bundle id "0102-6720-2020-v1-n2"', str(exc_info.exception)
        )

    def test_raises_error_if_aop_bundle_not_found(self):
        self.session.documents_bundles.fetch.side_effect = ds_exceptions.DoesNotExist
        doc_info = {
            "pid_v3": "document-id",
            "eissn": "2317-6326",
            "pissn": "0102-6720",
            "issn": "0102-6720",
            "pid": "document-pid-v2",
            "year": "2020",
        }

        with self.assertRaises(exceptions.RollbackError) as exc_info:
            rollback.rollback_bundle(doc_info, self.session, self.fake_journals)
        self.assertEqual(
            'could not get bundle id "0102-6720-aop"', str(exc_info.exception)
        )

    def test_update_bundle_without_rolledback_document(self):
        fake_bundle_manifest = {
            "_id" : "0102-6720-2020-v1-n2",
            "id" : "0102-6720-2020-v1-n2",
            "created" : "2020-08-09T06:49:55.118012Z",
            "updated" : "2020-08-09T06:49:55.118245Z",
            "items" : [
                {"id": "document-id", "order" : "00123"},
                {"id": "document-2", "order" : "00321"},
            ],
            "metadata" : {}
        }
        fake_bundle = ds_domain.DocumentsBundle(manifest=fake_bundle_manifest)
        self.session.documents_bundles.fetch.return_value = fake_bundle
        doc_info = {
            "pid_v3": "document-id",
            "eissn": "2317-6326",
            "pissn": "0102-6720",
            "issn": "0102-6720",
            "pid": "document-pid-v2",
            "year": "2020",
            "volume": "1",
            "number": "2",
        }

        rollback.rollback_bundle(doc_info, self.session, self.fake_journals)
        self.session.documents_bundles.update.assert_called_once_with(fake_bundle)
        self.assertNotIn(
            {"id": "document-id", "order" : "00123"}, fake_bundle.documents
        )


@patch.object(rollback, "rollback_bundle")
class TestRollbackDocument(TestCase):

    def setUp(self):
        self.session = Mock(spec=rollback.RollbackSession)
        self.fake_journals = rollback.get_journals_from_json(
            SAMPLES_PATH + "/base-isis-sample/title/title.json"
        )
        self.doc_info = {
            "pid_v3": "document-id",
            "eissn": "2317-6326",
            "pissn": "0102-6720",
            "issn": "0102-6720",
            "pid": "document-pid-v2",
            "year": "2020",
            "volume": "1",
            "number": "2",
        }

    def test_raises_error_if_no_pid_v3(self, mock_rollback_bundle):
        with self.assertRaises(exceptions.RollbackError) as exc_info:
            rollback.rollback_document({}, self.session, self.fake_journals)
        self.assertEqual("could not get PID V3 from doc info.", str(exc_info.exception))

    def test_rollback_changes(self, mock_rollback_bundle):
        rollback.rollback_document(self.doc_info, self.session, self.fake_journals)
        self.session.changes.rollback.assert_called_once_with("document-id")

    def test_rollback_documents(self, mock_rollback_bundle):
        rollback.rollback_document(self.doc_info, self.session, self.fake_journals)
        self.session.documents.rollback.assert_called_once_with("document-id")

    def test_rollback_bundle(self, mock_rollback_bundle):
        rollback.rollback_document(self.doc_info, self.session, self.fake_journals)
        mock_rollback_bundle.assert_called_once_with(
            self.doc_info, self.session, self.fake_journals
        )
