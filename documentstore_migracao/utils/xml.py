""" module to methods xml file """

import re
import logging
import unicodedata

from lxml import etree
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def str2objXML(string):
    return etree.fromstring(
        "<div>%s</div>" % (unicodedata.normalize("NFKD", " ".join(string.split())))
    )


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


def parcer_body_xml(obj_xml):

    txt_body = getattr(obj_xml.find("body/p"), "text", "")
    regex = r"(<\s*\/?\s*)(%s)(\s*([^>]*)?\s*>)"

    for tag, new_tag in config.TAG_HTML_FROM_TO.items():
        txt_body = re.sub(regex % tag, r"\1%s\3" % new_tag, txt_body)

    html = str2objXML(txt_body)

    return html
