""" module to methods xml file """

import logging
from lxml import etree
from xml.dom.minidom import parseString
from documentstore_migracao.utils import string, convert_html_body

logger = logging.getLogger(__name__)


def str2objXML(str):
    _string = string.normalize(str)
    try:
        return etree.fromstring("<body>%s</body>" % (str))
    except etree.XMLSyntaxError as e:
        # import pdb;pdb.set_trace()
        # logger.exception(e)
        return etree.fromstring("<body></body>")


def find_medias(obj_body):

    media = []
    # IMG
    imgs = obj_body.findall(".//graphic") + obj_body.findall(".//inline-graphic")
    for img in imgs:
        src_txt = "{http://www.w3.org/1999/xlink}href"
        logger.info("\t IMG %s", img.attrib[src_txt])
        path_img = img.attrib[src_txt]
        media.append(path_img)

        f_name, f_ext = string.extract_filename_ext_by_path(path_img)
        img.set(src_txt, "%s%s" % (f_name, f_ext))

    # FILES
    tags_a = obj_body.findall("a[@href]")
    for a in tags_a:
        href = a.attrib["href"]
        if href.startswith("/img/"):
            logger.info("\t FILE %s", href)
            media.append(href)

            f_name, f_ext = string.extract_filename_ext_by_path(href)
            img.set("href", "%s%s" % (f_name, f_ext))

    return media


def parser_body_xml(obj_body):

    txt_body = getattr(obj_body.find("./p"), "text", "")
    convert = convert_html_body.HTML2SPSPipeline()
    html = convert.deploy(txt_body)

    return html[1]


def prettyPrint_format(xml_string):
    return parseString(xml_string).toprettyxml()


def get_languages(obj_xml):
    """The language of the main document plus all translations.
    """
    return obj_xml.xpath(
        '/article/@xml:lang | //sub-article[@article-type="translation"]/@xml:lang'
    )
