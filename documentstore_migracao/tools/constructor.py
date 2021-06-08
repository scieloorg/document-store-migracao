import os
import logging

import fs
from lxml import etree
from tqdm import tqdm
from fs import path
from fs.walk import Walker

from documentstore_migracao.utils import files, string, xml, pid_manager
from documentstore_migracao.utils import scielo_ids_generator
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def register_pid_v3(pid_database_engine, xml_sps):
    pid_v2 = xml_sps.scielo_pid_v2
    pid_v3 = xml_sps.scielo_pid_v3
    pid_prev = xml_sps.aop_pid

    if not pid_v3:
        # procura pid_v3 na base pid_manager
        pid_v3 = (
            pid_prev and
            pid_manager.get_pid_v3_by_v2(pid_database_engine, pid_prev) or
            pid_v2 and
            pid_manager.get_pid_v3_by_v2(pid_database_engine, pid_v2) or
            scielo_ids_generator.generate_scielo_pid()
        )
        xml_sps.scielo_pid_v3 = pid_v3

    # há pid_v3 no XML
    for v2 in (pid_prev, pid_v2):
        if v2:
            record = pid_manager.get_record(pid_database_engine, v2, pid_v3)
            if not record:
                pid_manager.create_pid(pid_database_engine, v2, pid_v3)


def article_xml_constructor(file_xml_path: str, dest_path: str, pid_database_engine, in_place: bool) -> None:

    logger.debug("file: %s", file_xml_path)

    parsed_xml = xml.loadToXML(file_xml_path)
    xml_sps = SPS_Package(parsed_xml)

    register_pid_v3(pid_database_engine, xml_sps)

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
