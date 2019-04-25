import os
import logging
import shutil

from packtools import XMLValidator, exceptions

from documentstore_migracao.utils import files, dicts
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def validator_article_xml(file_xml_path, print_error=True):

    result = {}
    logger.info(file_xml_path)
    try:
        xmlvalidator = XMLValidator.parse(file_xml_path)
        is_valid, errors = xmlvalidator.validate()
    except exceptions.XMLSPSVersionError as e:
        result[str(e)] = {
            "count": 1,
            "lineno": [1],
            "message": [str(e)],
            "filename": {file_xml_path},
        }
        return result

    if not is_valid:
        for error in errors:
            if print_error:
                logger.error("%s - %s - %s", error.level, error.line, error.message)

            message = error.message[:80]
            data = {
                "count": 1,
                "lineno": [error.line],
                "message": [error.message],
                "filename": {file_xml_path},
            }
            dicts.merge(result, message, data)

    return result


def validator_article_ALLxml(move_to_processed_source=False, move_to_valid_xml=False):
    logger.info("Iniciando Validação dos xmls")
    list_files_xmls = files.xml_files_list(config.get("CONVERSION_PATH"))

    success_path = config.get("VALID_XML_PATH")
    errors_path = config.get("XML_ERRORS_PATH")
    func = shutil.move if move_to_valid_xml else shutil.copyfile

    result = {}
    for file_xml in list_files_xmls:

        filename, _ = files.extract_filename_ext_by_path(file_xml)
        converted_file = os.path.join(config.get("CONVERSION_PATH"), file_xml)

        try:
            errors = validator_article_xml(converted_file, False)

            for k_error, v_error in errors.items():
                dicts.merge(result, k_error, v_error)

            if errors_path:
                manage_error_file(
                    errors,
                    os.path.join(errors_path, "%s.err" % filename),
                    converted_file,
                )

            if not errors:
                if success_path:
                    func(converted_file, os.path.join(success_path, file_xml))

                if move_to_processed_source:
                    files.move_xml_to(
                        "%s.xml" % filename,
                        config.get("SOURCE_PATH"),
                        config.get("PROCESSED_SOURCE_PATH"),
                    )

        except Exception as ex:
            logger.exception(ex)
            raise

    analase = sorted(result.items(), key=lambda x: x[1]["count"], reverse=True)
    for k_result, v_result in analase:
        logger.error("%s - %s", k_result, v_result["count"])


def manage_error_file(errors, err_file, converted_file):
    if os.path.isfile(err_file):
        try:
            os.unlink(err_file)
        except:
            pass

    if errors:
        msg = []
        for err, data in errors.items():
            msg.append(err)
            msg.extend(
                [
                    "{}:{}".format(ln, text)
                    for ln, text in zip(data["lineno"], data["message"])
                ]
            )

        files.write_file(
            err_file,
            "%s %s\n%s" % (files.read_file(converted_file), "=" * 80, "\n".join(msg)),
        )
