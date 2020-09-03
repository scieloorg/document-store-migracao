""" module to rollback imported data """
import pymongo
from documentstore import adapters as ds_adapters
from documentstore import exceptions as ds_exceptions


class DSMBaseStore(ds_adapters.BaseStore):

    def __init__(self, collection):
        self._collection = collection

    def _execute_delete(self, delete_func: callable, filter: dict) -> None:
        try:
            _result = delete_func(filter)
        except pymongo.errors.PyMongoError as exc:
            raise ds_exceptions.DoesNotExist(
                f'Could not remove data with "{filter}": {exc}'
            ) from None
        else:
            if not _result.deleted_count > 0:
                raise ds_exceptions.DoesNotExist(
                    f'Could not remove data with "{filter}": '
                    f'delete command returned "{_result.deleted_count}"'
                )

    def delete_one(self, filter: dict) -> None:
        self._execute_delete(self._collection.delete_one, filter)

    def delete_many(self, filter: dict) -> None:
        self._execute_delete(self._collection.delete_many, filter)


class DocumentStore(DSMBaseStore):

    def rollback(self, id: str) -> None:
        """Delela documento com o ID informado."""
        self.delete_one({"_id": id})


class ChangesStore(DSMBaseStore):

    def rollback(self, id: str) -> None:
        """Deleta todos os registros de mudança registrados para o ID informado."""
        self.delete_many({"id": id})


class RollbackSession(ds_adapters.Session):
    """Extensão de `documentstore.adapters.Session` para manuteção dos dados no banco de
    dados do Kernel."""

    @property
    def documents(self):
        return DocumentStore(self._mongodb_client.documents)

    @property
    def changes(self):
        return ChangesStore(self._mongodb_client.changes)

