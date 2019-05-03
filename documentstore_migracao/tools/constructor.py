import os
import logging
from lxml import etree
from packtools import XML
from documentstore_migracao.utils import files, constructor_xml, string
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def article_xml_constructor(file_xml_path: str, dest_path: str) -> None:

    logger.info("file: %s", file_xml_path)

    parsed_xml = xml.loadToXML(file_xml_path)
    xml_sps = SPS_Package(parsed_xml)

    # CONSTROI O SCIELO-id NO XML CONVERTIDO
    xml_sps.create_scielo_id()

    new_file_xml_path = os.path.join(dest_path, os.path.basename(file_xml_path))
    xml.objXML2file(new_file_xml_path, xml_sps.xmltree, pretty=True)


def article_ALL_constructor(source_path: str, dest_path: str) -> None:

    logger.info("Iniciando Construção dos XMLs")
    list_files_xmls = files.xml_files_list(source_path)
    for file_xml in list_files_xmls:

        try:
            article_xml_constructor(os.path.join(source_path, file_xml), dest_path)
        except Exception as ex:
            logger.info("não foi possível gerar o XML do Arquivo %s: %s", file_xml, ex)
