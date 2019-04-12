import os
import logging
from lxml import etree
from packtools import XML
from documentstore_migracao.utils import files, constructor_xml, string
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def article_xml_constructor(file_xml_path):

    logger.info("file: %s", file_xml_path)

    parsed_xml = XML(file_xml_path, no_network=False)
    constructor = constructor_xml.ConstructorXMLPipeline()
    obj_xml = constructor.deploy(parsed_xml)

    new_file_xml_path = os.path.join(
        config.get("CONSTRUCTOR_PATH"), os.path.basename(file_xml_path)
    )

    files.write_file(
        new_file_xml_path,
        string.remove_spaces(
            etree.tostring(
                obj_xml[1],
                doctype=config.DOC_TYPE_XML,
                pretty_print=True,
                xml_declaration=True,
                encoding="utf-8",
                method="xml",
            ).decode("utf-8")
        ),
    )


def article_ALL_constructor():
    paths = [config.get("CONVERSION_PATH"), config.get("VALID_XML_PATH")]
    paths = [path for path in paths if path]

    logger.info("Iniciando Construção dos XMLs")
    for path in paths:
        list_files_xmls = files.xml_files_list(path)
        for file_xml in list_files_xmls:

            try:
                article_xml_constructor(os.path.join(path, file_xml))

            except Exception as ex:
                logger.error(file_xml)
                logger.exception(ex)
                raise
