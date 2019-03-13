import logging
import plumber
from lxml import etree
from copy import deepcopy
from documentstore_migracao.utils import xml as utils_xml

logger = logging.getLogger(__name__)


def _process(xml, tag, func):
    logger.debug("\tbuscando tag '%s'", tag)
    nodes = xml.findall(".//%s" % tag)
    for node in nodes:
        func(node)
    logger.info("Total de %s tags '%s' processadas", len(nodes), tag)


class HTML2SPSPipeline(object):
    def __init__(self):
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.FontPipe(),
            self.RemoveEmptyPipe(),
            self.BRPipe(),
            self.PPipe(),
            self.DivPipe(),
            self.ImgPipe(),
            self.LiPipe(),
            self.OlPipe(),
            self.UlPipe(),
            self.IPipe(),
            self.BPipe(),
            self.APipe(),
            self.StrongPipe(),
            self.TdPPipe(),
        )

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            xml = utils_xml.str2objXML(data)
            return data, xml

    class FontPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            etree.strip_tags(xml, "font")
            return data

    class RemoveEmptyPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            count = 0
            for node in xml.xpath("*"):
                text = node.text
                children = node.getchildren()

                if not (text and text.strip()) and not len(children):
                    node.getparent().remove(node)

                    count += 1
                    logger.debug("removendo tag em branco '%s'", node.tag)

            logger.info("Total de %s tags em branco removidas", count)
            return data

    class BRPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            nodes = xml.findall(".//br")
            for node in nodes:
                node.tag = "break"

            return data

    class PPipe(plumber.Pipe):
        def parser_node(self, node):
            _id = node.attrib.pop("id", None)
            node.attrib.clear()
            if _id:
                node.set("id", _id)

        def transform(self, data):
            raw, xml = data

            _process(xml, "p", self.parser_node)
            return data

    class DivPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "sec"
            _id = node.attrib.pop("id", None)
            node.attrib.clear()
            if _id:
                node.set("id", _id)

        def transform(self, data):
            raw, xml = data

            _process(xml, "div", self.parser_node)
            return data

    class ImgPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "graphic"
            _attrib = deepcopy(node.attrib)
            src = _attrib.pop("src")

            node.attrib.clear()
            node.set("{http://www.w3.org/1999/xlink}href", src)

        def transform(self, data):
            raw, xml = data

            _process(xml, "img", self.parser_node)
            return data

    class LiPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "list-item"
            node.attrib.clear()

        def transform(self, data):
            raw, xml = data

            _process(xml, "li", self.parser_node)
            return data

    class OlPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "list"
            node.set("list-type", "order")

        def transform(self, data):
            raw, xml = data

            _process(xml, "ol", self.parser_node)
            return data

    class UlPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "list"
            node.set("list-type", "bullet")

        def transform(self, data):
            raw, xml = data

            _process(xml, "ul", self.parser_node)
            return data

    class IPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "italic"

        def transform(self, data):
            raw, xml = data

            _process(xml, "i", self.parser_node)
            return data

    class BPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "bold"

        def transform(self, data):
            raw, xml = data

            _process(xml, "b", self.parser_node)
            return data

    class APipe(plumber.Pipe):

        def parser_node(self, node):
            _attrib = deepcopy(node.attrib)
            try:
                href = _attrib.pop("href")
            except KeyError:
                logger.debug("\tTag 'a' sem href removendo node do xml")
                node.getparent().remove(node)
                return

            if "mailto" in href:
                node.tag = "email"
                node.text = href.replace("mailto:", "")
                _attrib = {}

            elif href.startswith('http'):
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

        def transform(self, data):
            raw, xml = data

            _process(xml, "a", self.parser_node)
            return data

    class StrongPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "bold"

        def transform(self, data):
            raw, xml = data

            _process(xml, "strong", self.parser_node)
            return data

    class TdPPipe(plumber.Pipe):
        def parser_node(self, node):
            etree.strip_tags(node, "p")
            etree.strip_tags(node, "span")
            etree.strip_tags(node, "small")
            _attrib = deepcopy(node.attrib)

            # REMOVE WIDTH AND HEIGHT
            _attrib.pop("width", None)
            _attrib.pop("height", None)

            for key in _attrib.keys():
                _attrib[key] = _attrib[key].lower()

            node.attrib.clear()
            node.attrib.update(_attrib)

        def transform(self, data):
            raw, xml = data

            _process(xml, "td", self.parser_node)
            return data

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)
