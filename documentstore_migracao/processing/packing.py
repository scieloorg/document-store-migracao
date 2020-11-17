import os
import shutil
import logging
import json

from tqdm import tqdm
from urllib.parse import urlparse
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao.processing.extracted import PoisonPill, DoJobsConcurrently


logger = logging.getLogger(__name__)


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

    SPS_PKG_PATH = config.get("SPS_PKG_PATH")
    INCOMPLETE_SPS_PKG_PATH = config.get("INCOMPLETE_SPS_PKG_PATH")

    pkg_path = os.path.join(SPS_PKG_PATH, original_filename)
    incomplete_pkg_path = os.path.join(INCOMPLETE_SPS_PKG_PATH, original_filename)

    asset_replacements = list(set(sps_package.replace_assets_names()))
    logger.debug("%s possui %s ativos digitais", file_xml_path, len(asset_replacements))

    renditions, renditions_metadata = sps_package.get_renditions_metadata()
    logger.debug("%s possui %s renditions", file_xml_path, len(renditions))

    package_path = packing_assets(
        asset_replacements + renditions,
        pkg_path,
        incomplete_pkg_path,
        sps_package.package_name
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

    try:
        file_path = ''

        for path in [
            os.path.join(config.get('SOURCE_PDF_FILE'), asset_path),
            os.path.join(config.get('SOURCE_IMG_FILE'), asset_path),
        ]:
            if os.path.exists(path):
                file_path = os.path.join(path, asset_path)

        content = files.read_file_binary(file_path)
    except IOError as e:
        try:
            msg = str(e)
        except TypeError:
            msg = "Unknown error"
        logger.error(e)
        return msg
    else:
        files.write_file_binary(dest_path_file, content)


def packing_assets(asset_replacements, pkg_path, incomplete_pkg_path, pkg_name):
    """Tem a responsabilidade de ``empacotar`` os ativos digitais e retorna o
    path do pacote.

    Args:
        asset_replacements: lista com os ativos
        pkg_path: caminho do pacote
        incomplete_pkg_path: caminho para os pacotes incompletos
        pkg_name: nome do pacote

    Retornos:
        retorna o caminho ``pkg_path`` ou incomplete_pkg_path

    Exceções:
        Não lança exceções.
    """
    errors = []
    if not os.path.isdir(pkg_path):
        files.make_empty_dir(pkg_path)

    for old_path, new_fname in asset_replacements:
        error = get_asset(old_path, new_fname, pkg_path)
        if error:
            errors.append((old_path, new_fname, error))

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
        if len(errors) > 0:
            error_messages = "\n".join(["%s %s %s" % _err for _err in errors])
            files.write_file(errors_filename, error_messages)
        return incomplete_pkg_path
    return pkg_path
