import os
import logging

from lxml import etree
from typing import List

from documentstore_migracao.utils import files, xml, string
from documentstore_migracao import config
from xylose.scielodocument import Journal
from documentstore_migracao.utils import xylose_converter

logger = logging.getLogger(__name__)


def conversion_article_xml(file_xml_path):
    article = files.read_file(file_xml_path)

    logger.info("file: %s", file_xml_path)
    obj_xml = etree.fromstring(article)
    obj_xml.set("specific-use", "sps-1.8")
    obj_xml.set("dtd-version", "1.1")

    for index, body in enumerate(obj_xml.xpath("//body"), start=1):
        logger.info("Processando body numero: %s" % index)

        obj_html_body = xml.parser_body_xml(body)
        # sobrecreve o html escapado anterior pelo novo xml tratado
        body.getparent().replace(body, obj_html_body)

    languages = "-".join(xml.get_languages(obj_xml))
    _, fname = os.path.split(file_xml_path)
    fname, fext = fname.rsplit(".", 1)

    new_file_xml_path = os.path.join(
        config.get("CONVERSION_PATH"), "%s.%s.%s" % (fname, languages, fext)
    )

    files.write_file(
        new_file_xml_path,
        xml.prettyPrint_format(
            string.remove_spaces(
                etree.tostring(
                    obj_xml,
                    doctype=config.DOC_TYPE_XML,
                    pretty_print=True,
                    xml_declaration=True,
                    encoding="utf-8",
                    method="xml",
                ).decode("utf-8")
            )
        ),
    )


def conversion_article_ALLxml():

    logger.info("Iniciando Conversão do xmls")
    list_files_xmls = files.list_dir(config.get("SOURCE_PATH"))
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
