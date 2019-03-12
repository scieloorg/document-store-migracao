""" module to methods xml file """

import re
import logging
import unicodedata

from lxml import etree
from documentstore_migracao.utils.convert_html_body import HTML2SPSPipeline

logger = logging.getLogger(__name__)


def str2objXML(string):
    _string = unicodedata.normalize("NFKD", " ".join(string.split()))
    try:
        return etree.fromstring("<body>%s</body>" % (string))
    except etree.XMLSyntaxError as e:
        logger.exception(e)
        return etree.fromstring("<body></body>")


def find_medias(obj_xml):

    html = obj_xml.find("body")
    media = []
    # IMG
    imgs = html.findall(".//graphic")
    for img in imgs:
        logger.info("\t IMG %s", img.attrib["src"])
        media.append(img.attrib["src"])

    # FILES
    tags_a = html.findall("a[@href]")
    for a in tags_a:
        href = a.attrib["href"]
        if href.startswith("/img/"):
            logger.info("\t FILE %s", a.attrib)
            media.append(href)

    return media


def parser_body_xml(obj_xml):

    txt_body = getattr(obj_xml.find("body/p"), "text", "")
    convert = HTML2SPSPipeline()
    html = convert.deploy(txt_body)

    return html[1]
