""" module to processing to inserting methods """

import os
import logging

from documentstore_migracao.utils import files, xml, manifest
from documentstore_migracao import config, exceptions

from documentstore.domain import utcnow
from documentstore.exceptions import AlreadyExists


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


def import_document_by_database(folder: str, session_db, storage) -> None:

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

    scielo_id = xml.get_scielo_id(obj_xml)
    acrom = xml.get_journal_id(obj_xml)
    issn = xml.get_issn_journal(obj_xml)

    prefix = f"{issn}_{acrom}/{scielo_id}"
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


def inserting_document_store(session_db, storage) -> None:

    logger.info("Iniciando Envio dos do xmls")
    list_folders = files.list_files(config.get("SPS_PKG_PATH"))

    for folder in list_folders:

        try:
            import_document_by_database(
                os.path.join(config.get("SPS_PKG_PATH"), folder), session_db, storage
            )

        except Exception as ex:
            logger.info(
                "não foi possível submeter o conteúdo do diretório %s: %s", folder, ex
            )
            raise
