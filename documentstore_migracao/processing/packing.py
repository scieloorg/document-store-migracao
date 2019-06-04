import os
import shutil
import logging

from tqdm import tqdm
from requests.compat import urljoin
from lxml import etree
from documentstore_migracao.utils import files, request, xml
from documentstore_migracao import config
from documentstore_migracao.export.sps_package import SPS_Package


logger = logging.getLogger(__name__)


def pack_article_xml(file_xml_path):
    original_filename, ign = files.extract_filename_ext_by_path(file_xml_path)

    obj_xml = xml.file2objXML(file_xml_path)

    sps_package = SPS_Package(obj_xml, original_filename)

    SPS_PKG_PATH = config.get("SPS_PKG_PATH")
    INCOMPLETE_SPS_PKG_PATH = config.get("INCOMPLETE_SPS_PKG_PATH")

    pkg_path = os.path.join(SPS_PKG_PATH, original_filename)
    bad_pkg_path = os.path.join(INCOMPLETE_SPS_PKG_PATH, original_filename)

    files.make_empty_dir(pkg_path)

    asset_replacements = list(set(sps_package.replace_assets_names()))
    logger.info("%s possui %s ativos digitais", file_xml_path, len(asset_replacements))

    package_path = packing_assets(
        asset_replacements, pkg_path, bad_pkg_path, sps_package.package_name
    )

    xml.objXML2file(
        os.path.join(package_path, "%s.xml" % (sps_package.package_name)), obj_xml
    )


def pack_article_ALLxml():

    logger.info("Empacotando os documentos XML")
    list_files_xmls = files.xml_files_list(config.get("VALID_XML_PATH"))
    for file_xml in tqdm(list_files_xmls):

        try:
            pack_article_xml(os.path.join(config.get("VALID_XML_PATH"), file_xml))

        except (PermissionError, OSError, etree.Error) as ex:
            logger.error("Falha no empacotamento de %s" % file_xml)
            logger.exception(ex)


def download_asset(old_path, new_fname, dest_path):
    """Returns msg, if error"""
    if old_path.startswith("http"):
        location = old_path
    else:
        location = urljoin(config.get("STATIC_URL_FILE"), old_path)
    try:
        request_file = request.get(location, timeout=int(config.get("TIMEOUT") or 10))
    except request.HTTPGetError as e:
        try:
            msg = str(e)
        except TypeError:
            msg = "Unknown error"
        logger.error(e)
        return msg
    else:
        filename_m, ext_m = files.extract_filename_ext_by_path(old_path)
        files.write_file_binary(
            os.path.join(dest_path, "%s%s" % (new_fname, ext_m)), request_file.content
        )


def packing_assets(asset_replacements, pkg_path, bad_pkg_path, pkg_name):
    """
    Retorna o caminho do pacote (pkg_path ou bad_pkg_path)
    """
    errors = []
    if not os.path.isdir(pkg_path):
        files.make_empty_dir(pkg_path)

    for old_path, new_fname in asset_replacements:
        error = download_asset(old_path, new_fname, pkg_path)
        if error:
            errors.append((old_path, new_fname, error))

    if len(errors) > 0:
        # garante que existe pastas diferentes para
        # pacotes completos e incompletos
        if pkg_path == bad_pkg_path:
            bad_pkg_path += "_INCOMPLETE"
        # move pacote incompleto para a pasta de pacotes incompletos
        files.make_empty_dir(bad_pkg_path)
        for item in os.listdir(pkg_path):
            shutil.move(os.path.join(pkg_path, item), bad_pkg_path)
        shutil.rmtree(pkg_path)
        # gera relatorio de erros
        errors_filename = os.path.join(bad_pkg_path, "%s.err" % pkg_name)
        if len(errors) > 0:
            error_messages = "\n".join(["%s %s %s" % _err for _err in errors])
            files.write_file(errors_filename, error_messages)
        return bad_pkg_path
    return pkg_path
