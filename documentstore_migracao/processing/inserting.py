""" module to processing to inserting methods """

import os
import logging

from documentstore_migracao.utils import files, xml
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def document_store_by_database(folder: str, session_db, storage) -> None:

    logger.info("Processando a Pasta %s", folder)
    list_files = files.list_files(folder)

    obj_xml = None
    prefix = ""
    xml_files = files.xml_files_list(folder)
    medias_files = [mf for mf in list_files if mf not in xml_files]

    for x_file in xml_files:
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
        documentstore_data = {"data": url_xml, "assets": assets}
        print(scielo_id)
        print(documentstore_data)


def inserting_document_store(session_db, storage) -> None:

    logger.info("Iniciando Envio dos do xmls")
    list_folders = files.list_files(config.get("DOWNLOAD_PATH"))

    for folder in list_folders[:10]:

        try:
            document_store_by_database(
                os.path.join(config.get("DOWNLOAD_PATH"), folder), session_db, storage
            )

        except Exception as ex:
            logger.error(folder)
            logger.exception(ex)
            raise
