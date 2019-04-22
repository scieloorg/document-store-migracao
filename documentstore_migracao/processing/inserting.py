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
    xml_files = files.xml_files_list(folder)
    medias_files = [mf for mf in list_files if mf not in xml_files]

    for x_file in xml_files:
        xml_path = os.path.join(folder, x_file)
        obj_xml = xml.loadToXML(xml_path)
        url_xml = storage.register(xml_path)

    assets = []
    for m_file in medias_files:

        assets.append(
            {
                "asset_id": m_file,
                "asset_url": storage.register(os.path.join(folder, m_file)),
            }
        )

    if obj_xml:
        documentstore_data = {"data": url_xml, "assets": assets}
        scielo_id = xml.get_scielo_id(obj_xml)
        if scielo_id:
            print(scielo_id)
            # result = request.put(
            #     request.join(
            #         config.get("DOCUMENT_STORE_URL"), "/documents/%s" % scielo_id
            #     ),
            #     data=json.dumps(documentstore_data),
            # )
            # logger.info("Retorno Documents-Store: %s", result.status_code)


def inserting_document_store(session_db, storage) -> None:

    logger.info("Iniciando Envio dos do xmls")
    list_folders = files.list_files(config.get("DOWNLOAD_PATH"))

    for folder in list_folders:

        try:
            document_store_by_database(
                os.path.join(config.get("DOWNLOAD_PATH"), folder), session_db, storage
            )

        except Exception as ex:
            logger.error(folder)
            logger.exception(ex)
            raise
