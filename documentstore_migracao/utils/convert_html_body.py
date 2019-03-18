import logging
import plumber
from lxml import etree
from copy import deepcopy
from documentstore_migracao.utils import xml as utils_xml
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def _process(xml, tag, func):
    logger.debug("\tbuscando tag '%s'", tag)
    nodes = xml.findall(".//%s" % tag)
    for node in nodes:
        func(node)
    logger.info("Total de %s tags '%s' processadas", len(nodes), tag)


def replace_node_content(xml, node, new_text):

    return xml


def wrap_node(node, elem_wrap='p'):
    tag = node.tag
    p = etree.Element(elem_wrap)
    _node = deepcopy(node)
    p.append(_node)
    etree.strip_tags(p, tag)
    for n in node.findall("*"):
        node.remove(n)
    node.text = ""
    node.append(p)
    return node


class HTML2SPSPipeline(object):
    def __init__(self):
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.DeprecatedHTMLTagsPipe(),
            self.RemoveExcedingStyleTagsPipe(),
            self.RemoveEmptyPipe(),
            self.RemoveStyleAttributesPipe(),
            self.BRPipe(),
            self.PPipe(),
            self.DivPipe(),
            self.ImgPipe(),
            self.LiPipe(),
            self.OlPipe(),
            self.UlPipe(),
            self.IPipe(),
            self.EmPipe(),
            self.UPipe(),
            self.BPipe(),
            self.APipe(),
            self.StrongPipe(),
            self.TdCleanPipe(),
            self.BlockquotePipe(),
            self.HrPipe(),
        )

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            xml = utils_xml.str2objXML(data)
            return data, xml

    class DeprecatedHTMLTagsPipe(plumber.Pipe):
        TAGS = ["font", "small", "big", "dir", "span"]

        def transform(self, data):
            raw, xml = data
            for tag in self.TAGS:
                nodes = xml.findall(".//" + tag)
                if len(nodes) > 0:
                    etree.strip_tags(xml, tag)
                nodes = xml.findall(".//" + tag)
                if len(nodes) > 0:
                    logger.info("DEVERIA TER REMOVIDO:%s ", tag)
                    for item in nodes:
                        logger.info(etree.tostring(item))
            return data

    class RemoveExcedingStyleTagsPipe(plumber.Pipe):
        TAGS = ("b", "i", "em", "strong", "u")

        def transform(self, data):
            raw, xml = data
            for tag in self.TAGS:
                for node in xml.findall('.//'+tag):
                    text = ''.join(node.itertext()).strip()
                    if not text:
                        node.tag = "STRIPTAG"
            etree.strip_tags(xml, "STRIPTAG")
            return data

    class RemoveEmptyPipe(plumber.Pipe):
        EXCEPTIONS = ["br", "img", "hr"]

        def remove_empty_tags(self, xml):
            removed_tags = []
            for node in xml.xpath("//*"):
                if node.tag not in self.EXCEPTIONS:
                    if not node.findall("*"):
                        text = node.text or ""
                        text = text.strip()
                        if not text:
                            if node.getparent():
                                removed_tags.append(node.tag)
                                node.getparent().remove(node)
            return removed_tags

        def transform(self, data):
            raw, xml = data
            total_removed_tags = []
            remove = True
            while remove:
                removed_tags = self.remove_empty_tags(xml)
                total_removed_tags.extend(removed_tags)
                remove = len(removed_tags) > 0
            if len(total_removed_tags) > 0:
                logger.info(
                    "Total de %s tags vazias removidas", len(total_removed_tags)
                )
                logger.info(
                    "Tags removidas:%s ",
                    ", ".join(sorted(list(set(total_removed_tags)))),
                )
            return data

    class RemoveStyleAttributesPipe(plumber.Pipe):
        EXCEPT_FOR = [
            "caption",
            "col",
            "colgroup",
            "style-content",
            "table",
            "tbody",
            "td",
            "tfoot",
            "th",
            "thead",
            "tr",
        ]

        def transform(self, data):
            raw, xml = data
            count = 0
            for node in xml.xpath(".//*"):
                if node.tag in self.EXCEPT_FOR:
                    continue
                _attrib = deepcopy(node.attrib)
                style = _attrib.pop("style", None)
                if style:
                    count += 1
                    logger.debug("removendo style da tag '%s'", node.tag)
                node.attrib.clear()
                node.attrib.update(_attrib)
            logger.info("Total de %s tags com style", count)
            return data

    class BRPipe(plumber.Pipe):
        ALLOWED_IN = [
            "aff",
            "alt-title",
            "article-title",
            "chem-struct",
            "disp-formula",
            "product",
            "sig",
            "sig-block",
            "subtitle",
            "td",
            "th",
            "title",
            "trans-subtitle",
            "trans-title",
        ]

        def replace_CHANGE_BR_by_close_p_open_p(self, xml):
            _xml = etree.tostring(xml)
            _xml = _xml.replace(b"<CHANGE_BR/>", b"</p><p>")
            return etree.fromstring(_xml)

        def transform(self, data):
            raw, xml = data
            changed = False
            nodes = xml.findall("*[br]")
            for node in nodes:
                if node.tag in self.ALLOWED_IN:
                    for br in node.findall("br"):
                        br.tag = "break"
                elif node.tag == "p":
                    for br in node.findall("br"):
                        br.tag = "CHANGE_BR"
                        changed = True
            etree.strip_tags(xml, "br")
            if changed:
                return data[0], self.replace_CHANGE_BR_by_close_p_open_p(xml)
            return data

    class PPipe(plumber.Pipe):
        def parser_node(self, node):
            _id = node.attrib.pop("id", None)
            node.attrib.clear()
            if _id:
                node.set("id", _id)

            etree.strip_tags(node, "big")

            parent = node.getparent()
            if not parent.tag in config.ALLOYED_TAGS_TO_P:
                logger.warning("Tag `p` in `%s`", parent.tag)

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
        ALLOWED_CHILDREN = ('label', 'title', 'p', 'def-list', 'list')

        def parser_node(self, node):
            node.tag = "list-item"
            node.attrib.clear()
            tags = {n.tag for n in node.findall('*')}
            not_allowed = [tag for tag in tags
                           if tag not in self.ALLOWED_CHILDREN]
            if len(not_allowed) > 0:
                node = wrap_node(node, 'p')

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
            node.attrib.pop("list", None)

        def transform(self, data):
            raw, xml = data

            _process(xml, "ul", self.parser_node)
            return data

    class IPipe(plumber.Pipe):
        def parser_node(self, node):
            etree.strip_tags(node, "break")
            node.tag = "italic"
            node.attrib.clear()

        def transform(self, data):
            raw, xml = data

            _process(xml, "i", self.parser_node)
            return data

    class BPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "bold"
            etree.strip_tags(node, "break")
            etree.strip_tags(node, "span")
            etree.strip_tags(node, "p")
            node.attrib.clear()

        def transform(self, data):
            raw, xml = data

            _process(xml, "b", self.parser_node)
            return data

    class APipe(plumber.Pipe):
        def _parser_node_mailto(self, node, _attrib, href):
            node.tag = "email"
            node.text = href.replace("mailto:", "")
            _attrib = {}
            return _attrib

        def _parser_node_link(self, node, _attrib, href):
            node.tag = "ext-link"

            # Remove Traget in link
            _attrib.pop("target", None)
            _attrib.update(
                {"ext-link-type": "uri", "{http://www.w3.org/1999/xlink}href": href}
            )
            return _attrib

        def _parser_node_anchor(self, node, _attrib, href):
            node.tag = "xref"

            # remover name e title
            _attrib.pop("title", None)
            _attrib.pop("name", None)

            root = node.getroottree()
            ref_node = root.findall("//*[@id='%s']" % href)
            if ref_node:
                _attrib.update({"rid": href.replace("#", ""), "ref-type": ref_node.tag})
            return _attrib

        def parser_node(self, node):
            _attrib = deepcopy(node.attrib)
            try:
                href = _attrib.pop("href")
            except KeyError:
                logger.debug("\tTag 'a' sem href removendo node do xml")
                node.getparent().remove(node)
                return

            if "mailto" in href or "@" in href:
                _attrib = self._parser_node_mailto(node, _attrib, href)

            elif (
                href.startswith("htt")
                or href.startswith("ftp")
                or href.startswith("/")
                or href.startswith("../")
                or href.startswith("www")
                or href.startswith("file")
            ):
                _attrib = self._parser_node_link(node, _attrib, href)

            elif "#" in href:
                _attrib = self._parser_node_anchor(node, _attrib, href)

            etree.strip_tags(node, "break")

            node.attrib.clear()
            node.attrib.update(_attrib)

        def transform(self, data):
            raw, xml = data

            _process(xml, "a", self.parser_node)
            return data

    class StrongPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "bold"
            node.attrib.clear()
            etree.strip_tags(node, "span")
            etree.strip_tags(node, "p")

        def transform(self, data):
            raw, xml = data

            _process(xml, "strong", self.parser_node)
            return data

    class TdCleanPipe(plumber.Pipe):
        UNEXPECTED_INNER_TAGS = ["p", "span", "small", "dir"]
        EXPECTED_ATTRIBUTES = [
            "abbr",
            "align",
            "axis",
            "char",
            "charoff",
            "colspan",
            "content-type",
            "headers",
            "id",
            "rowspan",
            "scope",
            "style",
            "valign",
            "xml:base",
        ]

        def parser_node(self, node):
            for tag in self.UNEXPECTED_INNER_TAGS:
                etree.strip_tags(node, tag)
            _attrib = {}
            for key in node.attrib.keys():
                if key in self.EXPECTED_ATTRIBUTES:
                    _attrib[key] = node.attrib[key].lower()
            node.attrib.clear()
            node.attrib.update(_attrib)

        def transform(self, data):
            raw, xml = data

            _process(xml, "td", self.parser_node)
            return data

    class EmPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "italic"
            node.attrib.clear()
            etree.strip_tags(node, "break")

        def transform(self, data):
            raw, xml = data

            _process(xml, "em", self.parser_node)
            return data

    class UPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "underline"

        def transform(self, data):
            raw, xml = data

            _process(xml, "u", self.parser_node)
            return data

    class BlockquotePipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "disp-quote"

        def transform(self, data):
            raw, xml = data

            _process(xml, "blockquote", self.parser_node)
            return data

    class HrPipe(plumber.Pipe):
        def parser_node(self, node):
            node.attrib.clear()

        def transform(self, data):
            raw, xml = data

            _process(xml, "hr", self.parser_node)
            return data

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)
