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
        os.path.join(config.get("CONVERSION_PATH"), xml_file),
        os.path.join(config.get("SUCCESS_PROCESSING_PATH"), xml_file),
    )


def list_dir(path):

    return [f for f in os.listdir(path) if f.endswith(".xml")]


def read_file(path):

    logger.debug("Lendo arquivo: %s", path)
    text = ""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    return text


def write_file(path, source):
    logger.debug("Gravando arquivo: %s", path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
