import gzip

from documentstore.domain import utcnow
from documentstore.services import DocumentRenditions


def _add_change(session, instance, entity, id=None):
    session.changes.add(
        {
            "timestamp": utcnow(),
            "entity": entity,
            "id": id or instance.id(),
            "content_gz": gzip.compress(instance.data_bytes()),
            "content_type": instance.data_type,
        }
    )


def add_document(session, document):
    session.documents.add(document)
    _add_change(session, document, "Document")


def add_journal(session, journal):
    session.journals.add(journal)
    _add_change(session, journal, "Journal")


def update_journal(session, journal):
    session.journals.update(journal)
    _add_change(session, journal, "Journal")


def add_bundle(session, bundle):
    session.documents_bundles.add(bundle)
    _add_change(session, bundle, "DocumentsBundle")


def update_bundle(session, bundle):
    session.documents_bundles.update(bundle)
    _add_change(session, bundle, "DocumentsBundle")


def add_renditions(session, document):
    _add_change(
        session, DocumentRenditions(document), "DocumentRendition", document.id()
    )


__all__ = [
    "add_document",
    "add_journal",
    "update_journal",
    "add_bundle",
    "update_bundle",
    "add_renditions",
]
