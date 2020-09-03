""" module to rollback imported data """
import json
import logging

import pymongo
from documentstore import adapters as ds_adapters
from documentstore import exceptions as ds_exceptions
from xylose.scielodocument import Journal

from documentstore_migracao import exceptions, config
from documentstore_migracao.utils import (
    scielo_ids_generator,
)


logger = logging.getLogger(__name__)


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


def get_journals_from_json(journals_file_path: str) -> dict:
    with open(journals_file_path) as journals_file:
        journals = json.load(journals_file)
        data_journal = {}
        for journal in journals:
            o_journal = Journal(journal)
            if o_journal.print_issn:
                data_journal[o_journal.print_issn] = o_journal.scielo_issn
            if o_journal.electronic_issn:
                data_journal[o_journal.electronic_issn] = o_journal.scielo_issn
            if o_journal.scielo_issn:
                data_journal[o_journal.scielo_issn] = o_journal.scielo_issn
        return data_journal


def get_issn_by_document(journals: dict, document: dict):
    for issn_type in ("eissn", "pissn", "issn"):
        if document.get(issn_type) is not None:
            issn_value = document[issn_type].strip()
            if journals.get(issn_value) is not None:
                logger.debug(
                    'Document "%s" published in ISSN "%s"',
                    document["pid_v3"],
                    journals[issn_value],
                )
                return journals[issn_value]


def get_bundle_id(issn_id: str, doc_info: dict) -> None:
    if doc_info.get("volume") or doc_info.get("number"):
        return scielo_ids_generator.issue_id(
            issn_id,
            doc_info.get("year"),
            doc_info.get("volume"),
            doc_info.get("number"),
            doc_info.get("supplement"),
        )

    return scielo_ids_generator.aops_bundle_id(issn_id)


def rollback_bundle(doc_info: dict, session: object, journals: dict):
    _issn_id = get_issn_by_document(journals, doc_info)
    if not _issn_id:
        raise exceptions.RollbackError(
            f'could not get journal for document "{doc_info["pid_v3"]}"'
        )

    _bundle_id = get_bundle_id(_issn_id, doc_info)
    try:
        _bundle = session.documents_bundles.fetch(_bundle_id)
    except ds_exceptions.DoesNotExist:
        raise exceptions.RollbackError(f'could not get bundle id "{_bundle_id}"')
    else:
        logger.debug(
            'Removing document "%s" from bundle "%s"', doc_info["pid_v3"], _bundle_id
        )
        _bundle.remove_document(doc_info["pid_v3"])
        session.documents_bundles.update(_bundle)


def rollback_document(
    doc_info: dict, session: object, journals: dict, poison_pill=PoisonPill()
) -> None:
    """Desfaz documento de uma instância do Kernel como se não tivesse sido inserido,
    removendo registros feitos durante o processo de importação."""

    if poison_pill.poisoned:
        return

    try:
        pid_v3 = doc_info["pid_v3"]
    except KeyError:
        raise exceptions.RollbackError("could not get PID V3 from doc info.")
    else:
        logger.debug("Starting the rollback step for document PID V3 '%s'...", pid_v3)

        # Rollback Document changes
        session.changes.rollback(pid_v3)

        # Rollback Document
        session.documents.rollback(pid_v3)

        # Rollback DocumentsBundle
        rollback_bundle(doc_info, session, journals)

        return {"pid_v3": doc_info["pid_v3"], "status": "ROLLEDBACK"}


def rollback_kernel_documents(
    extracted_title_path: str,
) -> None:
    """
    Baseado no arquivo `output_path`, desfaz o import dos documentos, o relacionamento 
    no `document bundle`s e o registro de mudança"""

    journals = get_journals_from_json(extracted_title_path)

