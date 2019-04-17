""" module to utils methods to file """

import os
import shutil
import logging

from documentstore_migracao import config

logger = logging.getLogger(__name__)


def setup_processing_folder():

    paths = config.INITIAL_PATH
    for path in paths:
        create_dir(path)


def extract_filename_ext_by_path(inputFilepath):

    filename_w_ext = os.path.basename(inputFilepath)
    c_filename, file_extension = os.path.splitext(filename_w_ext)
    filename, _ = os.path.splitext(c_filename)
    return filename, file_extension


def move_xml_to(xml_file, source_path, destiny_path):

    shutil.move(
        os.path.join(source_path, xml_file), os.path.join(destiny_path, xml_file)
    )


def create_dir(path):
    if not os.path.exists(path):
        logger.debug("Criando pasta : %s", path)
        os.makedirs(path)


def make_empty_dir(path):
    if os.path.isdir(path):
        for item in os.listdir(path):
            file_path = os.path.join(path, item)
            try:
                os.unlink(file_path)
            except OSError:
                raise
    else:
        os.makedirs(path)


def create_path_by_file(path, file_xml_path):

    filename, _ = extract_filename_ext_by_path(file_xml_path)
    dest_path = os.path.join(path, filename)
    create_dir(dest_path)
    return dest_path


def xml_files_list(path):
    if path and os.path.isdir(path):
        return [f for f in os.listdir(path) if f.endswith(".xml")]
    return []


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


def write_file_binary(path, source):
    logger.debug("Gravando arquivo binario: %s", path)
    with open(path, "wb") as f:
        f.write(source)
