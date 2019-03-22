import os
import logging

from packtools import XMLValidator

from documentstore_migracao.utils import files, dicts
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

            message = error.message[:60]
            data = {"count": 1, "files": (error.line, file_xml_path)}
            dicts.merge(result, message, data)

    return result


def validator_article_ALLxml():

    logger.info("Iniciando Validação dos xmls")
    list_files_xmls = files.list_dir(config.get("CONVERSION_PATH"))

    result = {}
    for file_xml in list_files_xmls:

        try:
            errors = validator_article_xml(
                os.path.join(config.get("CONVERSION_PATH"), file_xml), False
            )
            for k_error, v_error in errors.items():
                dicts.merge(result, k_error, v_error)

        except Exception as ex:
            logger.exception(ex)
            raise

    analase = sorted(result.items(), key=lambda x: x[1]["count"], reverse=True)
    for k_result, v_result in analase:
        logger.error("%s - %s", k_result, v_result["count"])
        if "graphic" in k_result:
            for line, file in dicts.group(v_result["files"], 2):
                logger.error("\t %s - %s", line, file)
