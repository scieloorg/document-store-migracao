import os
import logging
import json
from typing import List

from lxml import etree
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config, exceptions


logger = logging.getLogger(__name__)


def reading_article_xml(file_xml_path, move_success=True):

    article = files.read_file(file_xml_path)
    obj_xml = etree.fromstring(article)
    medias = xml.find_medias(obj_xml)

    if medias:
        logger.info("%s possui midias", file_xml_path)

    if move_success:
        files.move_xml_conversion2success(
            file_xml_path.replace(config.get("CONVERSION_PATH"), "")
        )


def reading_article_ALLxml():

    logger.info("Iniciando Leituras do xmls")
    list_files_xmls = files.list_dir(config.get("CONVERSION_PATH"))
    for file_xml in list_files_xmls:

        try:
            reading_article_xml(
                os.path.join(config.get("CONVERSION_PATH"), file_xml),
                move_success=False,
            )

        except Exception as ex:
            logger.error(file_xml)
            logger.exception(ex)


def read_journals_from_json(file_path: str = "title.json") -> List[dict]:
    """Ler um arquivo json contendo uma lista de periódicos e
    retorna os dados dos periódicos em formato de tipos Python

    :param `file_path`: Complemento de path para o arquivo json de periódicos
    """

    json_path = os.path.join(config.get("SOURCE_PATH"), file_path)

    return json.loads(files.read_file(json_path))
