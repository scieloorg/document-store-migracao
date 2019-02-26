""" module to utils methods to file """

import os
import shutil
import logging

from documentstore_migracao import config

logger = logging.getLogger(__name__)


def setup_processing_folder():

    paths = [config.LOGGER_PATH, config.SOURCE_PATH, config.SUCCESS_PROCESSING_PATH]

    for path in paths:
        if not os.path.exists(path):
            logger.debug("Criando pasta : %s", path)
            os.makedirs(path)


def move_xml_source2success(xml_souce, xml_success):

    shutil.move(
        os.path.join(config.SOURCE_PATH, xml_souce),
        os.path.join(config.SUCCESS_PROCESSING, xml_success),
    )


def read_file(path):

    logger.debug("Lendo arquivo: %s", path)
    file = open(path, "r")
    text = file.read()
    file.close()

    return text


def write_file(path, source):

    logger.debug("Gravando arquivo: %s", path)
    file = open(path, "w")
    file.write(source)
    file.close()
