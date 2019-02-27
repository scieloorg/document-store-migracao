import os
import logging

from lxml import etree
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def reading_article_xml(file_xml_path, move_success=True):

    article = files.read_file(file_xml_path)
    try:
        obj_xml = etree.fromstring(article)
        medias = xml.find_medias(obj_xml)

        if medias:
            logger.info("%s possui midias", file_xml_path)

    except Exception as ex:
        logger.error(file_xml_path)
        logger.exception(ex)

        move_success = False

    if move_success:
        move_xml_conversion2success(file_xml_path.replce(config.CONVERSION_PATH, ""))


def reading_article_ALLxml():

    logger.info("Iniciando Leituras do xmls")
    list_files_xmls = files.list_dir(config.CONVERSION_PATH)
    for file_xml in list_files_xmls:

        try:
            reading_article_xml(
                os.path.join(config.CONVERSION_PATH, file_xml), move_success=False
            )

        except Exception as ex:
            logger.exception(ex)
