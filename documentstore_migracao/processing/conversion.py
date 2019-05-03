import os
import logging

from lxml import etree
from typing import List
from xylose.scielodocument import Journal, Issue
from documentstore_migracao.utils import files, xml, string, xylose_converter
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def conversion_article_xml(file_xml_path):

    obj_xmltree = xml.loadToXML(file_xml_path)
    obj_xml = obj_xmltree.getroot()

    obj_xml.set("specific-use", "sps-1.8")
    obj_xml.set("dtd-version", "1.1")

    xml_sps = SPS_Package(obj_xmltree)
    # CONVERTE O BODY DO AM PARA SPS
    xml_sps.transform_body()

    # CONSTROI O SCIELO-id NO XML CONVERTIDO
    xml_sps.create_scielo_id()

    languages = "-".join(xml_sps.languages)
    _, fname = os.path.split(file_xml_path)
    fname, fext = fname.rsplit(".", 1)

    new_file_xml_path = os.path.join(
        config.get("CONVERSION_PATH"), "%s.%s.%s" % (fname, languages, fext)
    )

    xml.objXML2file(new_file_xml_path, xml_sps.xmltree, pretty=True)


def conversion_article_ALLxml():

    logger.info("Iniciando Conversão do xmls")
    list_files_xmls = files.xml_files_list(config.get("SOURCE_PATH"))
    for file_xml in list_files_xmls:

        try:
            conversion_article_xml(os.path.join(config.get("SOURCE_PATH"), file_xml))

        except Exception as ex:
            logger.error(file_xml)
            logger.exception(ex)
            # raise


def conversion_journal_to_bundle(journal: dict) -> None:
    """Transforma um objeto Journal (xylose) para o formato
    de dados equivalente ao persistido pelo Kernel em um banco
    mongodb"""

    _journal = Journal(journal)
    _bundle = xylose_converter.journal_to_kernel(_journal)
    return _bundle


def conversion_journals_to_kernel(journals: list) -> list:
    """Transforma uma lista de periódicos não normalizados em
    uma lista de periódicos em formato Kernel"""

    logger.info("Convertendo %d periódicos para formato Kernel" % (len(journals)))
    return [conversion_journal_to_bundle(journal) for journal in journals]


def conversion_issues_to_xylose(issues: List[dict]) -> List[Issue]:
    """Converte uma lista de issues em formato JSON para uma
    lista de issues em formato xylose"""

    return [Issue({"issue": issue}) for issue in issues]


def conversion_issues_to_kernel(issues: List[Issue]) -> List[dict]:
    """Converte uma lista de issues em formato xylose para uma lista
    de issues em formato Kernel"""

    return [xylose_converter.issue_to_kernel(issue) for issue in issues]
