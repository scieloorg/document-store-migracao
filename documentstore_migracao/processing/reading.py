import os

from lxml import etree
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config


import logging
logger = logging.getLogger(__name__)


def reading_article_xml():

    logger.info("Iniciando Leituras do xmls")
    list_files_xmls = os.listdir(config.SOURCE_PATH)
    for file_xml in list_files_xmls:

        article = files.read_file(
            os.path.join(config.SOURCE_PATH, file_xml)
        )

        try:
            obj_xml = etree.fromstring(article)
            medias = xml.find_medias(obj_xml)

            if medias:
                logger.info("%s possui midias", file_xml)


        except Exception as ex:
            logger.error(file_xml)
            logger.error(ex)
