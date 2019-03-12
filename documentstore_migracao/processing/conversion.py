import os
import logging

from lxml import etree
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def conversion_article_xml(file_xml_path):
    article = files.read_file(file_xml_path)

    obj_xml = etree.fromstring(article)
    obj_xml.set("specific-use", "sps-1.8")
    obj_xml.set("dtd-version", "1.1")

    obj_html_body = xml.parser_body_xml(obj_xml)

    # sobrecreve o html escapado anterior pelo novo xml tratado
    remove = obj_xml.find("body")
    remove.getparent().replace(remove, obj_html_body)

    new_file_xml_path = os.path.join(
        config.get("CONVERSION_PATH"), os.path.split(file_xml_path)[1]
    )
    files.write_file(
        new_file_xml_path,
        etree.tostring(
            obj_xml,
            doctype=config.DOC_TYPE_XML,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
            method="xml",
        ).decode("utf-8"),
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
            raise
