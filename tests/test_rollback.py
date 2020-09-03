from unittest import TestCase
from unittest.mock import Mock, MagicMock

import pymongo
from documentstore import exceptions as ds_exceptions

from documentstore_migracao.processing import rollback


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
