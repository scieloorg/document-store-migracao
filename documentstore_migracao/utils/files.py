""" module to utils methods to file """

import os
import shutil
import logging

from documentstore_migracao import config

logger = logging.getLogger(__name__)


def setup_processing_folder():

    paths = config.INITIAL_PATH
    for path in paths:
        if not os.path.exists(path):
            logger.debug("Criando pasta : %s", path)
            os.makedirs(path)


def move_xml_conversion2success(xml_file):

    shutil.move(
        os.path.join(config.CONVERSION_PATH, xml_souce),
        os.path.join(config.SUCCESS_PROCESSING, xml_success),
    )


def list_dir(path):

    return [f for f in os.listdir(path) if f.endswith(".xml")]


def read_file(path):

    logger.debug("Lendo arquivo: %s", path)
    file = open(path, "r", encoding="utf-8")
    text = file.read()
    file.close()

    return text


def write_file(path, source):

    logger.debug("Gravando arquivo: %s", path)
    file = open(path, "w", encoding="utf-8")
    file.write(source)
    file.close()
