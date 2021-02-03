import os
import shutil
import logging
import json
import difflib

from tqdm import tqdm
from urllib.parse import urlparse
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config
from documentstore_migracao.export.sps_package import (
    SPS_Package,
    SourceJson,
    NotAllowedtoChangeAttributeValueError,
    InvalidAttributeValueError
)
from documentstore_migracao.processing.extracted import PoisonPill, DoJobsConcurrently


logger = logging.getLogger(__name__)

ISSNs = {}


class AssetNotFoundError(Exception):
    ...


def get_source_json(scielo_pid_v2):
    SOURCE_PATH = config.get("SOURCE_PATH")
    file_json_path = os.path.join(SOURCE_PATH, scielo_pid_v2 + ".json")
    with open(file_json_path, "r") as fp:
        json_content = fp.read()
    return SourceJson(json_content)


def pack_article_xml(file_xml_path, poison_pill=PoisonPill()):
    """Empacoda um xml e seus ativos digitais.

    Args:
        file_xml_path: Caminho para o XML
        poison_pill: Injeta um PosionPill()

    Retornos:
        Sem retornos.

        Persiste o XML no ``package_path``

    Exemplo:
        packing.pack_article_xml(
                os.path.join("S0044-59672003000300002.xml")
            )

    Exceções:
        Não lança exceções.
    """
    if poison_pill.poisoned:
        return

    original_filename, ign = files.extract_filename_ext_by_path(file_xml_path)

    obj_xml = xml.file2objXML(file_xml_path)

    sps_package = SPS_Package(obj_xml, original_filename)
    sps_package.fix(
        "article_id_which_id_type_is_other",
        sps_package.scielo_pid_v2 and sps_package.scielo_pid_v2[-5:],
        silently=True
    )
    new_issns = ISSNs and ISSNs.get(sps_package.scielo_pid_v2[1:10])
    if new_issns:
        sps_package.fix("issns", new_issns, silently=True)

    SPS_PKG_PATH = config.get("SPS_PKG_PATH")
    INCOMPLETE_SPS_PKG_PATH = config.get("INCOMPLETE_SPS_PKG_PATH")

    pkg_path = os.path.join(SPS_PKG_PATH, original_filename)
    incomplete_pkg_path = os.path.join(INCOMPLETE_SPS_PKG_PATH, original_filename)

    asset_replacements = list(set(sps_package.replace_assets_names()))
    logger.debug("%s possui %s ativos digitais", file_xml_path, len(asset_replacements))

    source_json = get_source_json(sps_package.scielo_pid_v2)
    renditions, renditions_metadata = source_json.get_renditions_metadata()
    logger.debug("%s possui %s renditions", file_xml_path, len(renditions))

    package_path = packing_assets(
        asset_replacements + renditions,
        pkg_path,
        incomplete_pkg_path,
        sps_package.package_name,
        sps_package.scielo_pid_v2,
    )

    files.write_file(
        os.path.join(package_path, "manifest.json"),
        json.dumps(renditions_metadata)
    )
    xml.objXML2file(
        os.path.join(package_path, "%s.xml" % (sps_package.package_name)), obj_xml
    )


def pack_article_ALLxml():
    """Gera os pacotes SPS a partir de um lista de XML validos.

    Args:
       Não há argumentos

    Retornos:
        Sem retornos.

        Persiste o XML no ``package_path``

    Exemplo:
        pack_article_ALLxml()

    Exceções:
        Não lança exceções.
    """

    xmls = [
        os.path.join(config.get("VALID_XML_PATH"), xml)
        for xml in files.xml_files_list(config.get("VALID_XML_PATH"))
    ]

    jobs = [{"file_xml_path": xml} for xml in xmls]

    with tqdm(total=len(xmls), initial=0) as pbar:

        def update_bar(pbar=pbar):
            pbar.update(1)

        DoJobsConcurrently(
            pack_article_xml,
            jobs=jobs,
            max_workers=int(config.get("THREADPOOL_MAX_WORKERS")),
            update_bar=update_bar,
        )


def get_asset(old_path, new_fname, dest_path):
    """Obtém os ativos digitais no sistema de arquivo e realiza a persistência
    no ``dest_path``.

    Args:
        old_path: Caminho do ativo
        new_fname: Novo nome para o ativo
        dest_path: Pasta de destino

    Retornos:
        Sem retornos.

        Persiste o ativo no ``dest_path``

    Exceções:
        IOError
        TypeError
    """
    if old_path.startswith("http"):
        asset_path = urlparse(old_path).path
    else:
        asset_path = old_path

    asset_path = asset_path.strip('/')

    # Verifica se o arquivo ja foi baixado anteriormente
    filename_m, ext_m = files.extract_filename_ext_by_path(old_path)
    dest_path_file = os.path.join(dest_path, "%s%s" % (new_fname.strip(), ext_m))
    if os.path.exists(dest_path_file):
        logger.debug("Arquivo já armazenado na pasta de destino: %s", dest_path_file)
        return

    paths = [
        os.path.join(config.get('SOURCE_IMG_FILE'), asset_path),
        os.path.join(config.get('SOURCE_PDF_FILE'), asset_path),
    ]
    if (filename_m, ext_m) == ("seta", ".gif"):
        seta_path = os.path.join(
            config.get('SOURCE_IMG_FILE'), "img", "seta.gif")
        paths.insert(0, seta_path)

    try:
        for path in paths:
            path = find_file(path)
            if path:
                break
        content = files.read_file_binary(path)
    except (TypeError, FileNotFoundError, IOError):
        raise AssetNotFoundError(f"Not found {old_path}")
    else:
        files.write_file_binary(dest_path_file, content)


def packing_assets(asset_replacements, pkg_path, incomplete_pkg_path, pkg_name,
                   scielo_pid_v2):
    """Tem a responsabilidade de ``empacotar`` os ativos digitais e retorna o
    path do pacote.

    Args:
        asset_replacements: lista com os ativos
        pkg_path: caminho do pacote
        incomplete_pkg_path: caminho para os pacotes incompletos
        pkg_name: nome do pacote
        scielo_pid_v2: PID v2

    Retornos:
        retorna o caminho ``pkg_path`` ou incomplete_pkg_path

    Exceções:
        Não lança exceções.
    """
    errors = []
    if not os.path.isdir(pkg_path):
        files.make_empty_dir(pkg_path)

    for old_path, new_fname in asset_replacements:
        try:
            get_asset(old_path, new_fname, pkg_path)
        except AssetNotFoundError as e:
            logger.error(
                "%s", {
                    "pid": scielo_pid_v2,
                    "pkg_name": pkg_name,
                    "old_path": old_path,
                    "new_fname": new_fname,
                    "msg": str(e),
                })
            errors.append((old_path, new_fname, str(e)))

    if len(errors) > 0:
        # garante que existe pastas diferentes para
        # pacotes completos e incompletos
        if pkg_path == incomplete_pkg_path:
            incomplete_pkg_path += "_INCOMPLETE"
        # move pacote incompleto para a pasta de pacotes incompletos
        files.make_empty_dir(incomplete_pkg_path)
        for item in os.listdir(pkg_path):
            shutil.move(os.path.join(pkg_path, item), incomplete_pkg_path)
        shutil.rmtree(pkg_path)
        # gera relatorio de erros
        errors_filename = os.path.join(incomplete_pkg_path, "%s.err" % pkg_name)
        error_messages = "\n".join(["%s %s %s" % _err for _err in errors])
        files.write_file(errors_filename, error_messages)
        return incomplete_pkg_path
    return pkg_path


def find_file(file_path):
    """
    A partir de um dado path, pega o nome de arquivo mais semelhante
    """
    dirname = os.path.dirname(file_path)
    basename = os.path.basename(file_path)
    try:
        files = os.listdir(dirname)
    except FileNotFoundError:
        return None
    else:
        found = case_insensitive_find(basename, files)
        if found:
            return os.path.join(dirname, found)


def case_insensitive_find(word, words):
    """
    Obtém a palavra que seja mais similar possível dentre uma lista de palavras
    A palavra obtida deve ser do mesmo tamanho
    Mas pode ter variações entre maiúsculas e minúsculas
    """
    if word in words:
        return word

    _words = [w for w in words if len(w) == len(word)]

    similar_items = difflib.get_close_matches(word, _words)
    for item in similar_items:
        if item.upper() == word.upper():
            return item

    for item in _words:
        if item.upper() == word.upper():
            return item
