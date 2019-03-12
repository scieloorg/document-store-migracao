import os
import logging

from packtools import XMLValidator

from documentstore_migracao.utils import files
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def validator_article_xml(file_xml_path):

    logger.info(file_xml_path)
    xmlvalidator = XMLValidator.parse(file_xml_path)
    is_valid, errors = xmlvalidator.validate()

    if not is_valid:
        for error in errors:
            logger.error("%s - %s - %s", error.level, error.line, error.message)


def validator_article_ALLxml():

    logger.info("Iniciando Validação dos xmls")
    list_files_xmls = files.list_dir(config.get("CONVERSION_PATH"))
    for file_xml in list_files_xmls:

        try:
            validator_article_xml(os.path.join(config.get("CONVERSION_PATH"), file_xml))
        except Exception as ex:
            logger.exception(ex)
            raise
