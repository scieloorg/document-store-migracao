""" module to utils methods to file """

import os
import shutil
import logging
import hashlib
from typing import List, Tuple, Set

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
    files = list_files(path)
    return list(filter(lambda f: f.endswith(".xml"), files))


def list_files(path):
    try:
        return os.listdir(path)
    except FileNotFoundError:
        return []


def read_file(path):

    logger.debug("Lendo arquivo: %s", path)
    text = ""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    return text


def read_file_binary(path):

    logger.debug("Lendo arquivo em modo binário: %s", path)
    text = ""
    with open(path, mode="rb") as f:
        text = f.read()

    return text


def write_file(path, source, mode="w"):
    logger.debug("Gravando arquivo: %s", path)
    with open(path, mode, encoding="utf-8") as f:
        f.write(source)


def write_file_binary(path, source):
    logger.debug("Gravando arquivo binario: %s", path)
    with open(path, "wb") as f:
        f.write(source)


def sha1(path):
    logger.debug("Lendo arquivo: %s", path)
    _sum = hashlib.sha1()
    with open(path, "rb") as file:
        while True:
            chunk = file.read(1024)
            if not chunk:
                break
            _sum.update(chunk)
    return _sum.hexdigest()


def register_latest_stage(stages_file_path: str, stage_id: str) -> None:
    """Adiciona um `stage_id` na última linha de um
    arquivo de controle"""

    with open(stages_file_path, "a") as file:
        file.write(f"{stage_id}\n")


def fetch_stage_file_path(content: List[str], func_name: str) -> str:
    """Retorna o path para um arquivo temporário contendo
    uma lista de `stage_id`"""

    name = hashlib.md5("".join(content).encode()).hexdigest()
    return os.path.join(config.get("CACHE_PATH"), func_name, name)


def create_stage_file(stage_file_path):
    """Cria um arquivo para conter a lista de estágios
    já realizados"""

    directory = os.path.dirname(stage_file_path)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    register_latest_stage(stage_file_path, "")


def fetch_stages_to_do(path: str, all_stages: List[str]) -> Tuple[Set[str], Set[str], str]:
    """Retorna a lista de estágios a serem processados
    e a quantidade de estágios já realizados"""

    with open(path, "r") as file:
        stages_already_done = file.readlines()
        stages_to_do = set(all_stages) - set(stages_already_done)
        return stages_to_do, stages_already_done, path


def fetch_stages_info(content: List[str], func_name: str) -> Tuple[Set[str], Set[str], str]:
    """Fachada que executa os passos necessários para
    criar o arquivo de cache que **contém** os estágios já realizados
    por uma função.

    Retorna uma tupla contendo informações sobre o arquivo de estágios:
    stages_to_do        :: Lista contendo os `estágios` a serem realizados
    stages_already_done  :: Quantidade de estágios finalizados
    path                :: Path para os arquivo contendo os estágios já
                           realizados
    """

    stages_file_path = fetch_stage_file_path(content=content, func_name=func_name)
    create_stage_file(stage_file_path=stages_file_path)

    return fetch_stages_to_do(path=stages_file_path, all_stages=content)


def get_files_in_path(path: str, extension) -> List[str]:
    """Retorna uma lista com os arquivos encontrados em um determinado path"""
    if os.path.isfile(path):
        return [path]

    files = []
    for root, _, folder_files in os.walk(path):
        files.extend(
            [
                os.path.realpath(os.path.join(root, file))
                for file in folder_files
                if file.endswith(extension)
            ]
        )

    return files
