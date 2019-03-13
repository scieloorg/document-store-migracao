import os
import logging

from packtools import XMLValidator

from documentstore_migracao.utils import files
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def validator_article_xml(file_xml_path, print_error=True):

    logger.info(file_xml_path)
    xmlvalidator = XMLValidator.parse(file_xml_path)
    is_valid, errors = xmlvalidator.validate()

    result = {}
    if not is_valid:
        for error in errors:
            if print_error:
                logger.error("%s - %s - %s", error.level, error.line, error.message)

            result.setdefault(error.message, 0)
            result[error.message] += 1

    return result


def validator_article_ALLxml():

    logger.info("Iniciando Validação dos xmls")
    list_files_xmls = files.list_dir(config.get("CONVERSION_PATH"))

    result = {}
    for file_xml in list_files_xmls[:10]:

        try:
            errors = validator_article_xml(
                os.path.join(config.get("CONVERSION_PATH"), file_xml), False
            )
            for k_error, v_error in errors.items():
                result.setdefault(k_error, 0)

                result[k_error] += v_error

        except Exception as ex:
            logger.exception(ex)
            raise

    analase = sorted(result.items(), key=lambda x: x[1], reverse=True)
    for k_result, v_result in result.items():
        logger.error("%s - %s", k_result, v_result)
