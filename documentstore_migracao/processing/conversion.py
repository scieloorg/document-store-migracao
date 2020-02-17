import os
import logging
import json
from typing import List
from pathlib import Path

from tqdm import tqdm
from lxml import etree
from xylose.scielodocument import Journal, Issue, Article

from documentstore_migracao.utils import files, xml, string, xylose_converter
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def get_article_dates(article):
    def _parse_date(str_date):
        _str_date = "".join(str_date.split("-"))
        return (
            _str_date[:4] if int(_str_date[:4]) > 0 else "",
            _str_date[4:6] if int(_str_date[4:6]) > 0 else "",
            _str_date[6:8]
            if len(_str_date[6:8]) > 0 and int(_str_date[6:8]) > 0
            else "",
        )

    document_pubdate = (
        article.document_publication_date
        or article.creation_date
        or article.update_date
    )
    document_pubdate = _parse_date(document_pubdate) if document_pubdate else None
    issue_pubdate = _parse_date(article.issue_publication_date)
    return document_pubdate, issue_pubdate


def convert_article_xml(file_xml_path):

    obj_xmltree = xml.loadToXML(file_xml_path)
    obj_xml = obj_xmltree.getroot()

    obj_xml.set("specific-use", "sps-1.9")
    obj_xml.set("dtd-version", "1.1")

    xml_sps = SPS_Package(obj_xmltree)
    # CONVERTE O BODY DO AM PARA SPS
    xml_sps.transform_body()
    # Transforma XML em SPS 1.9
    xml_sps.transform_content()
    # Completa datas presentes na base artigo e ausente no XML
    json_file_path = Path(config.get("SOURCE_PATH")).joinpath(
        Path(xml_sps.scielo_pid_v2 + ".json")
    )
    article = xylose_converter.json_file_to_xylose_article(json_file_path)
    document_pubdate, issue_pubdate = get_article_dates(article)
    xml_sps.complete_pub_date(document_pubdate, issue_pubdate)

    # CONSTROI O SCIELO-id NO XML CONVERTIDO
    xml_sps.create_scielo_id()

    # Remove a TAG <counts> do XML
    xml_sps.transform_article_meta_count()

    # Remove body when text is available only in PDF
    xml_sps.remove_article_body_when_text_is_available_only_in_pdf()

    languages = "-".join(xml_sps.languages)
    _, fname = os.path.split(file_xml_path)
    fname, fext = fname.rsplit(".", 1)

    new_file_xml_path = os.path.join(
        config.get("CONVERSION_PATH"), "%s.%s.%s" % (fname, languages, fext)
    )

    xml.objXML2file(new_file_xml_path, xml_sps.xmltree, pretty=True)


def convert_article_ALLxml():

    logger.info("Iniciando Conversão do xmls")
    list_files_xmls = files.xml_files_list(config.get("SOURCE_PATH"))
    for file_xml in tqdm(list_files_xmls):
        logger.info("CONVERTER %s" % file_xml)
        try:
            convert_article_xml(
                os.path.join(config.get("SOURCE_PATH"), file_xml))
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
