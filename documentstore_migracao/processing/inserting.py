""" module to processing to inserting methods """

import os
import logging
from typing import List

from documentstore_migracao.utils import files, xml, manifest, scielo_ids_generator

from documentstore_migracao import config, exceptions
from documentstore_migracao.export.sps_package import DocumentsSorter

from documentstore.domain import utcnow, DocumentsBundle
from documentstore.exceptions import AlreadyExists, DoesNotExist
from documentstore.interfaces import Session


logger = logging.getLogger(__name__)


class ManifestDomainAdapter:
    """Complementa o manifesto produzido na fase de transformação
    para o formato exigido pelos adapters do Kernel para
    realizar a inserção no MongoDB"""

    def __init__(self, manifest):
        self._manifest = manifest

    def id(self) -> str:
        return self.manifest["id"]

    @property
    def manifest(self) -> dict:
        return self._manifest


def register_document(folder: str, session_db, storage) -> None:

    logger.info("Processando a Pasta %s", folder)
    list_files = files.list_files(folder)

    obj_xml = None
    prefix = ""
    xml_files = files.xml_files_list(folder)
    medias_files = set(list_files) - set(xml_files)

    if len(xml_files) > 1:
        raise exceptions.XMLError("Existe %s xmls no pacote SPS", len(xml_files))
    else:
        try:
            x_file = xml_files[0]
        except IndexError as ex:
            raise exceptions.XMLError("Não existe XML no pacote SPS: %s", ex)

    xml_path = os.path.join(folder, x_file)
    obj_xml = xml.loadToXML(xml_path)

    xml_sps = SPS_Package(obj_xml)

    prefix = xml_sps.media_prefix
    url_xml = storage.register(xml_path, prefix)

    assets = []
    for m_file in medias_files:
        assets.append(
            {
                "asset_id": m_file,
                "asset_url": storage.register(os.path.join(folder, m_file), prefix),
            }
        )

    if obj_xml:
        manifest_data = ManifestDomainAdapter(
            manifest=manifest.get_document_bundle_manifest(obj_xml, url_xml, assets)
        )

        try:
            session_db.documents.add(data=manifest_data)
            session_db.changes.add(
                {"timestamp": utcnow(), "entity": "Document", "id": manifest_data.id()}
            )
            logger.info("Document-store save: %s", manifest_data.id())
        except AlreadyExists as exc:
            logger.exception(exc)

    return obj_xml, manifest_data.id()


def get_documents_bundle(session_db, data):
    issns = list(set([data.get(issn_type) for issn_type in ("eissn", "pissn", "issn")]))

    bad_docs_bundle_id = []
    for issn in issns:
        if issn:
            docs_bundle_id = scielo_ids_generator.documents_bundle_id(
                issn,
                data.get("year"),
                data.get("volume"),
                data.get("number"),
                data.get("supplement"),
            )
            try:
                documents_bundle = session_db.documents_bundles.fetch(docs_bundle_id)
            except DoesNotExist:
                bad_docs_bundle_id.append(docs_bundle_id)
            else:
                return documents_bundle
    raise ValueError(
        "Nenhum documents_bundle encontrado %s" % ", ".join(bad_docs_bundle_id)
    )


def inserting_document_store(session_db, storage) -> None:
    documents_sorter = DocumentsSorter()
    register_documents(session_db, storage, documents_sorter)
    register_documents_in_documents_bundle(
        session_db, documents_sorter.documents_bundles_with_sorted_documents
    )


def register_documents(session_db, storage, documents_sorter) -> None:
    logger.info("Iniciando Envio dos do xmls")
    list_folders = files.list_files(config.get("SPS_PKG_PATH"))

    err_filename = os.path.join(config.get("ERRORS_PATH"), "insert_documents.err")

    for folder in list_folders:
        try:
            document_path = os.path.join(config.get("SPS_PKG_PATH"), folder)
            registration_result = register_document(document_path, session_db, storage)
            if registration_result:
                document_xml, document_id = registration_result
                documents_sorter.insert_document(document_id, document_xml)

        except Exception as ex:
            msg = "Falha ao registrar documento %s: %s" % (document_path, ex)
            logger.error(msg)
            files.write_file(err_filename, msg, "a")


def link_documents_bundles_with_documents(
    documents_bundle: DocumentsBundle, documents: List[str], session: Session
):
    """Função responsável por atualizar o relacionamento entre
    documents bundles e documents no nível de banco de dados"""

    for document in documents:
        try:
            documents_bundle.add_document(document)
        except AlreadyExists:
            logger.info(
                "Document %s already exists in documents bundle %s"
                % (document, documents_bundle)
            )

    session.documents_bundles.update(documents_bundle)

    session.changes.add(
        {
            "timestamp": utcnow(),
            "entity": "DocumentsBundle",
            "id": documents_bundle.id(),
        }
    )


def register_documents_in_documents_bundle(
    session_db, documents_sorted_in_bundles
) -> None:

    err_filename = os.path.join(
        config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
    )

    not_registered = []

    for key, documents_bundle in documents_sorted_in_bundles.items():
        data = documents_bundle["data"]
        items = documents_bundle["items"]
        try:
            documents_bundle = get_documents_bundle(session_db, data)
        except ValueError as error:
            files.write_file(err_filename, key + "\n", "a")
            not_registered.append(key)
        else:
            link_documents_bundles_with_documents(documents_bundle, items, session_db)
