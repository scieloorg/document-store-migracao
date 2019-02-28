import logging

from documentstore_migracao.utils import xml
from copy import deepcopy

logger = logging.getLogger(__name__)


class ConvertHTMLBody:

    parser_tags = ("p", "div", "img", "li", "ol", "ul", "i", "b", "a")

    def __init__(self, str_xml):
        self.obj_xml = xml.str2objXML(str_xml)

    def get_body_element(self):
        self.process()
        return self.obj_xml

    def process(self):
        for tag in self.parser_tags:
            logger.info("buscando tag '%s'", tag)
            nodes = self.obj_xml.findall(".//%s" % tag)

            for node in nodes:
                getattr(self, "parser_%s" % tag)(node)
            logger.info("Total de %s tags processadas", len(nodes))

    def parser_p(self, node):
        node.attrib.clear()

    def parser_div(self, node):
        node.tag = "sec"
        _id = node.attrib.pop("id", "node")
        node.attrib.clear()
        if _id:
            node.set("id", _id)

    def parser_img(self, node):
        node.tag = "graphic"
        _attrib = deepcopy(node.attrib)
        src = _attrib.pop("src")

        node.attrib.clear()
        node.attrib.update(_attrib)
        node.set("{http://www.w3.org/1999/xlink}href", src)

    def parser_li(self, node):
        node.tag = "list-item"

    def parser_ol(self, node):
        node.tag = "list"
        node.set("list-type", "order")

    def parser_ul(self, node):
        node.tag = "list"
        node.set("list-type", "bullet")

    def parser_i(self, node):
        node.tag = "italic"

    def parser_b(self, node):
        node.tag = "bold"

    def parser_a(self, node):
        _attrib = deepcopy(node.attrib)
        href = _attrib.pop("href", "")

        if "mailto" in href:
            node.tag = "email"
            note.text = href.replace("mailto:", "")
            _attrib = {}

        elif "http://" in href:
            node.tag = "ext-link"
            _attrib.update(
                {"ext-link-type": "uri", "{http://www.w3.org/1999/xlink}href": href}
            )
        elif "#" in href:
            node.tag = "xref"

            root = node.getroottree()
            ref_node = root.findall("//*[@id='%s']" % href)

            _attrib.update(
                {
                    "rid": href.replace("#", ""),
                    "ref-type": ref_node and ref_node.tag or "author-notes",
                }
            )

        node.attrib.clear()
        node.attrib.update(_attrib)
