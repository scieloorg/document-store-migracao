import logging
import plumber
import html
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


def wrap_node(node, elem_wrap="p"):
    tag = node.tag

    p = etree.Element(elem_wrap)
    _node = deepcopy(node)
    p.append(_node)
    etree.strip_tags(p, tag)

    return p


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
            self.GraphicChildrenPipe(),
            self.RemoveCommentPipe(),
            self.BodyAllowedTagPipe(),
            self.HTMLEscapingPipe(),
        )

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            xml = utils_xml.str2objXML(data)
            return data, xml

    class DeprecatedHTMLTagsPipe(plumber.Pipe):
        TAGS = ["font", "small", "big", "dir", "span", "s"]

        def transform(self, data):
            raw, xml = data
            for tag in self.TAGS:
                nodes = xml.findall(".//" + tag)
                if len(nodes) > 0:
                    etree.strip_tags(xml, tag)
                # nodes = xml.findall(".//" + tag)
                # if len(nodes) > 0:
                #     logger.info("DEVERIA TER REMOVIDO:%s ", tag)
                #     for item in nodes:
                #         logger.info(etree.tostring(item))
            return data

    class RemoveExcedingStyleTagsPipe(plumber.Pipe):
        TAGS = ("b", "i", "em", "strong", "u")

        def transform(self, data):
            raw, xml = data
            for tag in self.TAGS:
                for node in xml.findall(".//" + tag):
                    text = "".join(node.itertext()).strip()
                    if not text:
                        node.tag = "STRIPTAG"
            etree.strip_tags(xml, "STRIPTAG")
            return data

    class RemoveEmptyPipe(plumber.Pipe):
        EXCEPTIONS = ["a", "br", "img", "hr"]

        def _is_empty_element(self, node):
            return node.findall("*") == [] and \
                   not (node.text or '').strip()

        def _remove_empty_element(self, node):
            parent = node.getparent()
            if parent is not None:
                if node.tail:
                    previous = node.getprevious()
                    if previous is not None:
                        if not previous.tail:
                            previous.tail = ''
                        previous.tail += node.tail
                    else:
                        if not parent.text:
                            parent.text = ''
                        parent.text += node.tail
                parent.remove(node)
                removed = node.tag
                return removed

        def _remove_empty_tags(self, xml):
            removed_tags = []
            for node in xml.xpath("//*"):
                if node.tag not in self.EXCEPTIONS:
                    if self._is_empty_element(node):
                        removed = self._remove_empty_element(node)
                        if removed:
                            removed_tags.append(removed)
            return removed_tags

        def transform(self, data):
            raw, xml = data
            total_removed_tags = []
            remove = True
            while remove:
                removed_tags = self._remove_empty_tags(xml)
                total_removed_tags.extend(removed_tags)
                remove = len(removed_tags) > 0
            if len(total_removed_tags) > 0:
                logger.info(
                    "Total de %s tags vazias removidas",
                    len(total_removed_tags)
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
        TAGS = [
            "abstract",
            "ack",
            "annotation",
            "app",
            "app-group",
            "author-comment",
            "author-notes",
            "bio",
            "body",
            "boxed-text",
            "caption",
            "def",
            "disp-quote",
            "fig",
            "fn",
            "glossary",
            "list-item",
            "note",
            "notes",
            "open-access",
            "ref-list",
            "sec",
            "speech",
            "statement",
            "supplementary-material",
            "support-description",
            "table-wrap-foot",
            "td",
            "th",
            "trans-abstract",
        ]

        def parser_node(self, node):
            _id = node.attrib.pop("id", None)
            node.attrib.clear()
            if _id:
                node.set("id", _id)

            etree.strip_tags(node, "big")

            parent = node.getparent()
            if not parent.tag in self.TAGS:
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
        ALLOWED_CHILDREN = ("label", "title", "p", "def-list", "list")

        def parser_node(self, node):
            node.tag = "list-item"
            node.attrib.clear()

            c_not_allowed = [
                c_node
                for c_node in node.getchildren()
                if c_node.tag not in self.ALLOWED_CHILDREN
            ]
            for c_node in c_not_allowed:
                node.replace(c_node, wrap_node(c_node, "p"))

            if node.text:
                p = etree.Element("p")
                p.text = node.text

                node.insert(0, p)
                node.text = ""

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

            email = etree.Element("email")
            email.text = href.replace("mailto:", "")

            node.tag = "p"
            node.append(email)
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
            list_tags = ["div", "sec", "table"]
            for tag in list_tags:
                ref_node = root.findall("//%s[@id='%s']" % (tag, href.replace("#", "")))
                if ref_node:
                    _attrib.update(
                        {"rid": href.replace("#", ""), "ref-type": ref_node[0].tag}
                    )
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

    class GraphicChildrenPipe(plumber.Pipe):
        TAGS = (
            "addr-line",
            "alternatives",
            "alt-title",
            "article-title",
            "attrib",
            "award-id",
            "bold",
            "chapter-title",
            "code",
            "collab",
            "comment",
            "compound-kwd-part",
            "compound-subject-part",
            "conf-theme",
            "data-title",
            "def-head",
            "disp-formula",
            "element-citation",
            "fixed-case",
            "funding-source",
            "inline-formula",
            "italic",
            "label",
            "license-p",
            "meta-value",
            "mixed-citation",
            "monospace",
            "named-content",
            "overline",
            "p",
            "part-title",
            "private-char",
            "product",
            "roman",
            "sans-serif",
            "sc",
            "see",
            "see-also",
            "sig",
            "sig-block",
            "source",
            "std",
            "strike",
            "styled-content",
            "sub",
            "subject",
            "subtitle",
            "sup",
            "supplement",
            "support-source",
            "td",
            "term",
            "term-head",
            "textual-form",
            "th",
            "title",
            "trans-source",
            "trans-subtitle",
            "trans-title",
            "underline",
            "verse-line",
        )

        def parser_node(self, node):
            parent = node.getparent()
            if parent.tag in self.TAGS:
                node.tag = "inline-graphic"
            else:
                etree.strip_tags(parent.getparent(), parent.tag)

        def transform(self, data):
            raw, xml = data

            _process(xml, "graphic", self.parser_node)
            return data

    class RemoveCommentPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            comments = xml.xpath("//comment()")
            for comment in comments:
                parent = comment.getparent()
                parent.remove(comment)
            logger.info("Total de %s 'comentarios' processadas", len(comments))
            return data

    class HTMLEscapingPipe(plumber.Pipe):
        def parser_node(self, node):
            text = node.text
            if text:
                node.text = html.escape(text)

        def transform(self, data):
            raw, xml = data

            _process(xml, "*", self.parser_node)
            return data

    class BodyAllowedTagPipe(plumber.Pipe):
        TAGS = (
            "address",
            "alternatives",
            "array",
            "boxed-text",
            "chem-struct-wrap",
            "code",
            "fig",
            "fig-group",
            "graphic",
            "media",
            "preformat",
            "supplementary-material",
            "table-wrap",
            "table-wrap-group",
            "disp-formula",
            "disp-formula-group",
            "def-list",
            "list",
            "tex-math",
            "mml:math",
            "p",
            "related-article",
            "related-object",
            "disp-quote",
            "speech",
            "statement",
            "verse-group",
            "sec",
            "sig-block",
        )

        def transform(self, data):
            raw, xml = data

            for children in xml.getchildren():
                if not children.tag in self.TAGS:
                    xml.remove(children)

            return data

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)
