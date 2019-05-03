""" module to methods xml file """

import logging
import itertools

from lxml import etree
from xml.dom.minidom import parseString

from documentstore_migracao import config
from documentstore_migracao.utils import string, convert_html_body, files


logger = logging.getLogger(__name__)


def str2objXML(_string):
    _string = string.normalize(_string)
    try:
        return etree.fromstring("<body>%s</body>" % (_string))
    except etree.XMLSyntaxError as e:
        logger.exception(e)
        return etree.fromstring("<body></body>")


def file2objXML(file_path):
    return loadToXML(file_path)


def objXML2file(file_path, obj_xml, pretty=False):
    files.write_file_binary(
        file_path,
        etree.tostring(
            obj_xml,
            doctype=config.DOC_TYPE_XML,
            xml_declaration=True,
            method="xml",
            pretty_print=pretty,
        ),
    )


def prettyPrint_format(xml_string):
    return parseString(xml_string).toprettyxml()


def loadToXML(file):
    """Parses `file` to produce an etree instance.

    The XML can be retrieved given its filesystem path,
    an URL or a file-object.
    """
    parser = etree.XMLParser(remove_blank_text=True, no_network=True)
    xml = etree.parse(file, parser)
    return xml
