import os
import logging

import fs
from lxml import etree
from tqdm import tqdm
from fs import path
from fs.walk import Walker

from documentstore_migracao.utils import files, string, xml
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def article_xml_constructor(file_xml_path: str, dest_path: str, in_place: bool) -> None:

    logger.debug("file: %s", file_xml_path)

    parsed_xml = xml.loadToXML(file_xml_path)
    xml_sps = SPS_Package(parsed_xml)

    # CONSTROI O SCIELO-id NO XML CONVERTIDO
    xml_sps.create_scielo_id()

    if in_place:
        new_file_xml_path = file_xml_path
    else:
        new_file_xml_path = os.path.join(dest_path, os.path.basename(file_xml_path))

    xml.objXML2file(new_file_xml_path, xml_sps.xmltree, pretty=True)


def article_ALL_constructor(source_path: str, dest_path: str, in_place:bool=False) -> None:

    logger.info("Iniciando Construção dos XMLs")
    walker = Walker(filter=["*.xml"], exclude=["*.*.xml"])

    list_files_xmls = walker.files(fs.open_fs(source_path))
    for file_xml in tqdm(list_files_xmls):
        file_xml = source_path + file_xml
        try:
            article_xml_constructor(file_xml, dest_path, in_place)
        except Exception as ex:
            logger.info("não foi possível gerar o XML do Arquivo %s: %s", file_xml, ex)
