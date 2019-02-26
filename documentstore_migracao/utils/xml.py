""" module to methods xml file """

import unicodedata
from lxml import etree

import logging

logger = logging.getLogger(__name__)


def find_medias(txt_xml):

    txt_body = getattr(txt_xml.find("body/p"), "text", "")
    html = etree.fromstring(
        "<div>%s</div>" % (unicodedata.normalize("NFKD", " ".join(txt_body.split())))
    )

    media = []
    # IMG
    imgs = html.findall(".//img")
    for img in imgs:
        logger.info("\t IMG", img.attrib["src"])
        media.append(img.attrib["src"])

    # FILES
    tags_a = html.findall("a[@href]")
    for a in tags_a:
        href = a.attrib["href"]
        if href.startswith("/img/"):
            logger.info("\t FILE", a.attrib)
            media.append(href)

    return media