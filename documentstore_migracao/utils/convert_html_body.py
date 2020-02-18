import logging
import plumber
import html
import os
from copy import deepcopy

import requests
from lxml import etree
from documentstore_migracao.utils import files
from documentstore_migracao.utils import xml as utils_xml
from documentstore_migracao import config
from documentstore_migracao.utils.convert_html_body_inferer import Inferer

import faulthandler

faulthandler.enable()

logger = logging.getLogger(__name__)
TIMEOUT = config.get("TIMEOUT") or 5

ASSET_TAGS = ("disp-formula", "fig", "table-wrap", "app")


def is_footnote_label(text):
    """
    Retorna True quando text representa "label" de nota de rodapé. Padrões:
    Primeiro caracter é dígito
    Primeiro caracter não é alfanumérico
    Uma letra, minúscula
    """
    if text:
        return any(
            [
                text[0].isdigit(),
                not text[0].isalnum(),
                text[0].isalpha() and len(text) == 1 and text[0].lower() == text[0]
            ]
        )

def get_anchor(xml, anchor_parent, label_and_caption_element):
    a = anchor_parent.find(".//a[@name]")
    if a is None:
        new_a = etree.Element("a")
        text = get_node_text(label_and_caption_element)
        texts = text.split(" ")
        if len(texts) >= 2 and texts[1].isdigit():
            name = texts[0][:3]+texts[1]
            if xml.find(".//a[@href='#{}']".format(name)) is None:
                name = name.lower()

            if xml.find(".//a[@href='#{}']".format(name)) is None:
                name = " ".join(texts[:2])
            new_a.set("name", name)
            new_a.set("id", name)
    else:
        new_a = deepcopy(a)
        new_a.tail = ""
    return new_a


def move_tail_into_node(node):
    """
    Move o conteúdo de node.tail para dentro de node
    Usa IGN para evitar segment fault
    Remove IGN no final
    """
    if (node.tail or "").strip():
        children = node.getchildren()
        if children:
            e = etree.Element("IGN")
            e.text = node.tail
            children[-1].append(e)
        else:
            node.text = node.tail
        node.tail = ""
        etree.strip_tags(node, "IGN")


def _remove_tag(node, remove_content=False):
    parent = node.getparent()
    if parent is None:
        return
    removed = node.tag
    node.tag = "REMOVE_NODE"
    if remove_content:
        # isso evita remover node.tail
        node.addnext(etree.Element("REMOVE_NODE"))
        parent.remove(node)
    etree.strip_tags(parent, "REMOVE_NODE")
    return removed


def _process(xml, tag, func):
    logger.debug("\tbuscando tag '%s'", tag)
    nodes = xml.findall(".//%s" % tag)
    for node in nodes:
        func(node)
    logger.info("Total de %s tags '%s' processadas", len(nodes), tag)


def wrap_node(node, elem_wrap="p"):

    _node = deepcopy(node)
    p = etree.Element(elem_wrap)
    p.append(_node)
    node.getparent().replace(node, p)

    return p


def wrap_content_node(_node, elem_wrap="p"):

    p = etree.Element(elem_wrap)
    if _node.text:
        p.text = _node.text
    if _node.tail:
        p.tail = _node.tail

    _node.text = None
    _node.tail = None
    _node.insert(0, p)


def find_or_create_asset_node(root, elem_name, elem_id, node=None):
    if elem_name is None or elem_id is None:
        return
    xpath = './/{}[@id="{}"]'.format(elem_name, elem_id)
    asset = root.find(xpath)
    if asset is None and node is not None:
        asset = search_asset_node_backwards(node)
    if asset is None and node is not None:
        parent = node.getparent()
        if parent is not None:
            previous = parent.getprevious()
            if previous is not None:
                asset = previous.find(".//*[@id]")
                if asset is not None and len(asset.getchildren()) > 0:
                    asset = None

    if asset is None:
        asset = etree.Element(elem_name)
        asset.set("id", elem_id)
    return asset


def get_node_text(node):
    if node is None:
        return ""
    for comment in node.xpath("//comment()"):
        parent = comment.getparent()
        if parent is not None:
            # isso evita remover comment.tail
            comment.addnext(etree.Element("REMOVE_COMMENT"))
            parent.remove(comment)
    try:
        etree.strip_tags(node, "REMOVE_COMMENT")
    except ValueError:
        # node is _Comment
        words = []
    else:
        words = " ".join(node.itertext()).split()
    return " ".join((word for word in words if word))


def alnum(sentence):
    words = sentence.split()
    new_words = []
    for w in words:
        alnumchars = [c for c in w if c.isalnum()]
        new_words.append("".join(alnumchars))
    return new_words


def minor(words1, words2):
    return sorted([len(words1), len(words2)])[0]


def matched_first_two_words(text_words, search_expr):
    if text_words and search_expr:
        text_words = alnum(text_words.lower())
        search_expr = alnum(search_expr.lower())
        if len(text_words) >= 2 and len(search_expr) >= 2:
            min_0 = minor(text_words[0], search_expr[0])
            min_1 = minor(text_words[1], search_expr[1])
            if (
                text_words[0][:min_0] == search_expr[0][:min_0]
                and text_words[1][:min_1] == search_expr[1][:min_1]
            ):
                return True


class CustomPipe(plumber.Pipe):
    def __init__(self, super_obj=None, *args, **kwargs):
        self.super_obj = super_obj
        super(CustomPipe, self).__init__(*args, **kwargs)


class HTML2SPSPipeline(object):
    def __init__(self, pid="", ref_items=[], index_body=1):
        self.pid = pid
        self.index_body = index_body
        self.ref_items = ref_items
        self.document = Document(None)
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.SaveRawBodyPipe(super_obj=self),
            self.ConvertRemote2LocalPipe(),
            self.RemoveReferencesFromBodyPipe(super_obj=self),
            self.RemoveCommentPipe(),
            self.DeprecatedHTMLTagsPipe(),
            self.RemoveImgSetaPipe(),
            self.RemoveOrMoveStyleTagsPipe(),
            self.RemoveEmptyPipe(),
            self.RemoveStyleAttributesPipe(),
            self.AHrefPipe(),
            self.DivPipe(),
            self.LiPipe(),
            self.OlPipe(),
            self.UlPipe(),
            self.DefListPipe(),
            self.DefItemPipe(),
            self.IPipe(),
            self.EmPipe(),
            self.UPipe(),
            self.BPipe(),
            self.StrongPipe(),
            self.RemoveInvalidBRPipe(),
            self.ConvertElementsWhichHaveIdPipe(),
            self.RemoveInvalidBRPipe(),
            self.BRPipe(),
            self.BR2PPipe(),
            self.TdCleanPipe(),
            self.TableCleanPipe(),
            self.BlockquotePipe(),
            self.HrPipe(),
            self.TagsHPipe(),
            self.DispQuotePipe(),
            self.GraphicChildrenPipe(),
            self.FixBodyChildrenPipe(),
            self.RemovePWhichIsParentOfPPipe(),
            self.PPipe(),
            self.RemoveRefIdPipe(),
            self.FixIdAndRidPipe(super_obj=self),
        )

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            try:
                text = etree.tostring(data)
            except TypeError:
                xml = utils_xml.str2objXML(data)
                text = data
            else:
                xml = data
            return text, xml

    class SaveRawBodyPipe(CustomPipe):
        def transform(self, data):
            raw, xml = data
            root = xml.getroottree()
            root.write(
                os.path.join(
                    "/tmp/",
                    "%s.%s.xml" % (self.super_obj.pid, self.super_obj.index_body),
                ),
                encoding="utf-8",
                doctype=config.DOC_TYPE_XML,
                xml_declaration=True,
                pretty_print=True,
            )
            return data, xml

    class ConvertRemote2LocalPipe(plumber.Pipe):
        def transform(self, data):
            logger.info("ConvertRemote2LocalPipe")
            raw, xml = data
            html_page = Remote2LocalConversion(xml)
            html_page.remote_to_local()
            logger.info("ConvertRemote2LocalPipe - fim")
            return data

    class DeprecatedHTMLTagsPipe(plumber.Pipe):
        TAGS = ["font", "small", "big", "dir", "span", "s", "lixo", "center"]

        def transform(self, data):
            raw, xml = data
            for tag in self.TAGS:
                nodes = xml.findall(".//" + tag)
                if len(nodes) > 0:
                    etree.strip_tags(xml, tag)
            return data

    class RemoveOrMoveStyleTagsPipe(plumber.Pipe):
        STYLE_TAGS = ("i", "b", "em", "strong", "u", "sup", "sub")

        def _move_style_tag_into_children(self, node):
            for child in node.findall(".//*"):
                if child.text and not child.getchildren():
                    e = etree.Element(node.tag)
                    e.text = child.text
                    child.text = ""
                    child.append(e)
            node.tag = "STRIPTAG"

        def _mark_style_tags_to_move_or_remove(self, xml):
            for style_tag in self.STYLE_TAGS:
                for node in xml.findall(".//" + style_tag):
                    text = get_node_text(node)
                    children = node.getchildren()
                    if not text:
                        node.tag = "STRIPTAG"
                    elif node.find(".//{}".format(style_tag)) is not None:
                        node.tag = "STRIPTAG"
                    else:
                        move = any(
                            (
                                child.tag
                                for child in children
                                if child.tag not in self.STYLE_TAGS
                            )
                        )
                        if move:
                            node.set("move", "true")
            etree.strip_tags(xml, "STRIPTAG")

        def _remove_or_move_style_tags(self, xml):
            while True:
                self._mark_style_tags_to_move_or_remove(xml)
                if xml.find(".//*[@move]") is None:
                    break
                for node in xml.findall(".//*[@move]"):
                    node.attrib.pop("move")
                    self._move_style_tag_into_children(node)
                etree.strip_tags(xml, "STRIPTAG")

        def transform(self, data):
            raw, xml = data
            self._remove_or_move_style_tags(xml)
            return data

    class RemoveEmptyPipe(plumber.Pipe):
        EXCEPTIONS = ["a", "br", "img", "hr", "td"]

        def _is_empty_element(self, node):
            return node.findall("*") == [] and not get_node_text(node)

        def _remove_empty_tags(self, xml):
            removed_tags = []
            for node in xml.xpath("//*"):
                if node.tag not in self.EXCEPTIONS:
                    if self._is_empty_element(node):
                        removed = _remove_tag(node)
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

        def transform(self, data):
            logger.info("BRPipe.transform - inicio")
            raw, xml = data
            for node in xml.findall(".//*[br]"):
                if node.tag in self.ALLOWED_IN:
                    for br in node.findall("br"):
                        br.tag = "break"
            logger.info("BRPipe.transform - inicio")
            return data

    class RemoveInvalidBRPipe(plumber.Pipe):
        def _remove_first_or_last_br(self, xml):
            """
            b'<bold><br/>Luis Huicho</bold>
            b'<bold>Luis Huicho</bold>
            """
            logger.info("RemoveInvalidBRPipe._remove_br - inicio")
            while True:
                change = False
                for node in xml.findall(".//*[br]"):
                    first = node.getchildren()[0]
                    last = node.getchildren()[-1]
                    if (node.text or "").strip() == "" and first.tag == "br":
                        first.tag = "REMOVEINVALIDBRPIPEREMOVETAG"
                        change = True
                    if (last.tail or "").strip() == "" and last.tag == "br":
                        last.tag = "REMOVEINVALIDBRPIPEREMOVETAG"
                        change = True
                if not change:
                    break
            etree.strip_tags(xml, "REMOVEINVALIDBRPIPEREMOVETAG")
            logger.info("RemoveInvalidBRPipe._remove_br - fim")

        def transform(self, data):
            logger.info("RemoveInvalidBRPipe - inicio")
            text, xml = data
            self._remove_first_or_last_br(xml)
            logger.info("RemoveInvalidBRPipe - fim")
            return data

    class BR2PPipe(plumber.Pipe):
        def _create_p(self, node, nodes, text):
            logger.info("BR2PPipe._create_p - inicio")
            if nodes or (text or "").strip():
                logger.info("BR2PPipe._create_p - element p")
                p = etree.Element("p")
                if node.tag not in ["REMOVE_P", "p"]:
                    p.set("content-type", "break")
                p.text = text
                logger.info("BR2PPipe._create_p - append nodes")
                for n in nodes:
                    p.append(deepcopy(n))
                logger.info("BR2PPipe._create_p - node.append(p)")
                node.append(p)
            logger.info("BR2PPipe._create_p - fim")

        def _create_new_node(self, node):
            """
            <root><p>texto <br/> texto 1</p></root>
            <root><p><p content-type= "break">texto </p><p content-type= "break"> texto 1</p></p></root>
            """
            logger.info("BR2PPipe._create_new_node - inicio")
            new = etree.Element(node.tag)
            for attr, value in node.attrib.items():
                new.set(attr, value)
            text = node.text
            nodes = []
            for i, child in enumerate(node.getchildren()):
                if child.tag == "br":
                    self._create_p(new, nodes, text)
                    nodes = []
                    text = child.tail
                else:
                    nodes.append(child)
            self._create_p(new, nodes, text)
            logger.info("BR2PPipe._create_new_node - fim")
            return new

        def _executa(self, xml):
            logger.info("BR2PPipe._executa - inicio")
            while True:
                node = xml.find(".//*[br]")
                if node is None:
                    break
                new = self._create_new_node(node)

                node.addprevious(new)
                if node.tag == "p":
                    new.tag = "BRTOPPIPEREMOVETAG"
                p = node.getparent()
                if p is not None:
                    p.remove(node)
            etree.strip_tags(xml, "BRTOPPIPEREMOVETAG")
            logger.info("BR2PPipe._executa - fim")

        def transform(self, data):
            logger.info("BR2PPipe - inicio")
            text, xml = data
            self._executa(xml)
            logger.info("BR2PPipe - fim")
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
        ATTRIBUTES = ("content-type", "id", "specific-use", "xml:base", "xml:lang")

        def parser_node(self, node):
            if "class" in node.attrib.keys() and not node.get("content-type"):
                node.set("content-type", node.get("class"))
            for attr in node.attrib.keys():
                if attr not in self.ATTRIBUTES:
                    node.attrib.pop(attr)
            parent = node.getparent()
            if parent.tag not in self.TAGS:
                logger.warning("Tag `p` in `%s`", parent.tag)

        def transform(self, data):
            raw, xml = data
            _process(xml, "p", self.parser_node)
            return data

    class DivPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "p"
            _id = node.attrib.pop("id", None)
            node.attrib.clear()
            if _id:
                node.set("id", _id)

        def transform(self, data):
            raw, xml = data

            _process(xml, "div", self.parser_node)
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
                wrap_node(c_node, "p")

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

    class DefListPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "def-list"
            node.attrib.clear()

        def transform(self, data):
            raw, xml = data

            _process(xml, "dl", self.parser_node)
            return data

    class DefItemPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "def-item"
            node.attrib.clear()

        def transform(self, data):
            raw, xml = data

            _process(xml, "dd", self.parser_node)
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
        EXPECTED_INNER_TAGS = [
            "email",
            "ext-link",
            "uri",
            "hr",
            "inline-supplementary-material",
            "related-article",
            "related-object",
            "disp-formula",
            "disp-formula-group",
            "break",
            "citation-alternatives",
            "element-citation",
            "mixed-citation",
            "nlm-citation",
            "bold",
            "fixed-case",
            "italic",
            "monospace",
            "overline",
            "roman",
            "sans-serif",
            "sc",
            "strike",
            "underline",
            "ruby",
            "chem-struct",
            "inline-formula",
            "def-list",
            "list",
            "tex-math",
            "mml:math",
            "p",
            "abbrev",
            "index-term",
            "index-term-range-end",
            "milestone-end",
            "milestone-start",
            "named-content",
            "styled-content",
            "alternatives",
            "array",
            "code",
            "graphic",
            "media",
            "preformat",
            "inline-graphic",
            "inline-media",
            "private-char",
            "fn",
            "target",
            "xref",
            "sub",
            "sup",
        ]
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
            for c_node in node.getchildren():
                if c_node.tag not in self.EXPECTED_INNER_TAGS:
                    _remove_tag(c_node)

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

    class TableCleanPipe(TdCleanPipe):
        EXPECTED_INNER_TAGS = ["col", "colgroup", "thead", "tfoot", "tbody", "tr"]

        EXPECTED_ATTRIBUTES = [
            "border",
            "cellpadding",
            "cellspacing",
            "content-type",
            "frame",
            "id",
            "rules",
            "specific-use",
            "style",
            "summary",
            "width",
            "xml:base",
        ]

        def transform(self, data):
            raw, xml = data

            _process(xml, "table", self.parser_node)
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
            node.tag = "p"
            node.set("content-type", "hr")

        def transform(self, data):
            raw, xml = data

            _process(xml, "hr", self.parser_node)
            return data

    class TagsHPipe(plumber.Pipe):
        def parser_node(self, node):
            node.attrib.clear()
            org_tag = node.tag
            node.tag = "p"
            node.set("content-type", org_tag)

        def transform(self, data):
            raw, xml = data

            tags = ["h1", "h2", "h3", "h4", "h5", "h6"]
            for tag in tags:
                _process(xml, tag, self.parser_node)
            return data

    class DispQuotePipe(plumber.Pipe):
        TAGS = [
            "label",
            "title",
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
            "attrib",
            "permissions",
        ]

        def parser_node(self, node):
            node.attrib.clear()
            if node.text and node.text.strip():
                new_p = etree.Element("p")
                new_p.text = node.text
                node.text = None
                node.insert(0, new_p)

            for c_node in node.getchildren():
                if c_node.tail and c_node.tail.strip():
                    new_p = etree.Element("p")
                    new_p.text = c_node.tail
                    c_node.tail = None
                    c_node.addnext(new_p)

                if c_node.tag not in self.TAGS:
                    wrap_node(c_node, "p")

        def transform(self, data):
            raw, xml = data

            _process(xml, "disp-quote", self.parser_node)
            return data

    class GraphicChildrenPipe(plumber.Pipe):
        TAGS = (
            "alternatives",
            "app",
            "app-group",
            "array",
            "bio",
            "body",
            "boxed-text",
            "chem-struct",
            "chem-struct-wrap",
            "disp-formula",
            "disp-quote",
            "fig",
            "fig-group",
            "floats-group",
            "glossary",
            "license-p",
            "named-content",
            "notes",
            "p",
            "ref-list",
            "sec",
            "sig",
            "sig-block",
            "styled-content",
            "supplementary-material",
            "table-wrap",
            "td",
            "term",
            "th",
        )

        def parser_node(self, node):
            parent = node.getparent()
            if parent.tag not in self.TAGS:
                node.tag = "inline-graphic"

        def transform(self, data):
            raw, xml = data

            _process(xml, "graphic", self.parser_node)
            return data

    class RemoveReferencesFromBodyPipe(CustomPipe):
        def transform(self, data):
            raw, xml = data
            if len(self.super_obj.ref_items) > 0:
                references_header, p_to_delete = self._mark_references(xml)
                if len(self.super_obj.ref_items) == len(p_to_delete):
                    self._delete_references_header(references_header)
                    for p in p_to_delete:
                        _remove_tag(p, True)
                else:
                    logger.info("RemoveReferencesFromBodyPipe: FALHOU")
            return data

        def _mark_references(self, xml):
            """
            Cria o atributo "content-type" com valor "ref-to-delete" para
            os parágrafos de referências que contém o comentário
            `<!-- end-ref -->`
            """
            header = None
            comments = xml.xpath("//comment()")
            for comment in comments:
                name = comment.text.strip()
                if name == "end-ref":
                    parents = [comment.getparent(), comment.getparent().getparent()]
                    for parent in parents:
                        if parent.tag == "p":
                            parent.set("content-type", "ref-to-delete")
                            break
                elif header is None and name == "ref":
                    header = comment.getprevious()
            return header, xml.findall(".//p[@content-type='ref-to-delete']")

        def _delete_references_header(self, references_header):
            if references_header is not None:
                text = get_node_text(references_header)
                if text:
                    text = text.upper()
                    if text.startswith("REF") or ">REF" in text:
                        logger.info(
                            "RemoveReferencesFromBodyPipe: Primeiro: %s"
                            % etree.tostring(references_header)
                        )
                        _remove_tag(references_header, True)

    class RemoveCommentPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            comments = xml.xpath("//comment()")
            for comment in comments:
                parent = comment.getparent()
                if parent is not None:
                    # isso evita remover comment.tail
                    comment.addnext(etree.Element("REMOVE_COMMENT"))
                    parent.remove(comment)
            etree.strip_tags(xml, "REMOVE_COMMENT")
            logger.info("Total de %s 'comentarios' removidos", len(comments))
            return data

    class AHrefPipe(plumber.Pipe):
        def _create_ext_link(self, node, extlinktype="uri"):
            node.tag = "ext-link"
            href = node.attrib.get("href")
            node.attrib.clear()
            node.set("ext-link-type", extlinktype)
            node.set("{http://www.w3.org/1999/xlink}href", href)

        def _create_email(self, node):
            href = node.get("href").strip()
            if "mailto:" in href:
                href = href.split("mailto:")[1]

            node_text = (node.text or "").strip()
            node.tag = "email"
            node.attrib.clear()
            if not href and node_text and "@" in node_text:
                texts = node_text.split()
                for text in texts:
                    if "@" in text:
                        href = text
                        break
            if not href:
                # devido ao caso do href estar mal
                # formado devemos so trocar a tag
                # e retorna para continuar o Pipe
                return

            node.set("{http://www.w3.org/1999/xlink}href", href)

            if href == node_text:
                return
            if href in node_text:
                root = node.getroottree()
                temp = etree.Element("AHREFPIPEREMOVETAG")
                texts = node_text.split(href)
                temp.text = texts[0]
                email = etree.Element("email")
                email.text = href
                temp.append(email)
                temp.tail = texts[1]
                node.addprevious(temp)
                etree.strip_tags(root, "AHREFPIPEREMOVETAG")
            else:
                # https://jats.nlm.nih.gov/publishing/tag-library/1.2/element/email.html
                node.tag = "ext-link"
                node.set("ext-link-type", "email")
                node.set("{http://www.w3.org/1999/xlink}href", "mailto:" + href)

        def parser_node(self, node):

            href = node.get("href")
            if href.count('"') == 2:
                node.set("href", href.replace('"', ""))
                href = node.get("href")

            if href[0] in ["#", "."] or href.startswith("/img/revistas/"):
                return
            if "mailto" in href or "@" in href:
                return self._create_email(node)
            if href.startswith("//") or ":" in href:
                return self._create_ext_link(node)
            if href.startswith("www"):
                return self._create_ext_link(node)
            if href.startswith("http//"):
                return self._create_ext_link(node)
            href = href.split("/")[0]
            if href and href.count(".") and href.replace(".", ""):
                return self._create_ext_link(node)

        def transform(self, data):
            raw, xml = data
            _process(xml, "a[@href]", self.parser_node)
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

    class RemovePWhichIsParentOfPPipe(plumber.Pipe):
        def _tag_texts(self, xml):
            for node in xml.xpath(".//p[p]"):
                if node.text and node.text.strip():
                    new_p = etree.Element("p")
                    new_p.text = node.text
                    node.text = ""
                    node.insert(0, new_p)

                for child in node.getchildren():
                    if child.tail and child.tail.strip():
                        new_p = etree.Element("p")
                        new_p.text = child.tail
                        child.tail = ""
                        child.addnext(new_p)

        def _identify_extra_p_tags(self, xml):
            for node in xml.xpath(".//p[p]"):
                node.tag = "REMOVE_P"

        def _tag_text_in_body(self, xml):
            for body in xml.xpath(".//body"):
                for node in body.findall("*"):
                    if node.tail and node.tail.strip():
                        new_p = etree.Element("p")
                        new_p.text = node.tail
                        node.tail = ""
                        node.addnext(new_p)

        def _solve_open_p(self, xml):
            node = xml.find(".//p[p]")
            if node is not None:
                new_p = etree.Element("p")
                if node.text and node.text.strip():
                    new_p.text = node.text
                    node.text = ""
                for child in node.getchildren():
                    if child.tag != "p":
                        new_p.append(deepcopy(child))
                        node.remove(child)
                    else:
                        break
                if new_p.text or new_p.getchildren():
                    node.addprevious(new_p)
                node.tag = "REMOVE_P"
                etree.strip_tags(xml, "REMOVE_P")

        def _solve_open_p_items(self, xml):
            node = xml.find(".//p[p]")
            while node is not None:
                self._solve_open_p(xml)
                node = xml.find(".//p[p]")

        def transform(self, data):
            raw, xml = data
            self._solve_open_p_items(xml)
            # self._tag_texts(xml)
            # self._identify_extra_p_tags(xml)
            # self._tag_text_in_body(xml)
            etree.strip_tags(xml, "REMOVE_P")
            return data

    class RemoveRefIdPipe(plumber.Pipe):
        def parser_node(self, node):
            node.attrib.pop("xref_id", None)

        def transform(self, data):
            raw, xml = data

            _process(xml, "*[@xref_id]", self.parser_node)
            return data

    class FixIdAndRidPipe(CustomPipe):
        def transform(self, data):
            raw, xml = data
            for node in xml.findall(".//*[@rid]"):
                self._update(node, "rid")
            for node in xml.findall(".//*[@id]"):
                self._update(node, "id")
            return data, xml

        def _update(self, node, attr_name):
            value = node.get(attr_name)
            value = self._fix(node.get("ref-type") or node.tag, value)
            node.attrib[attr_name] = value

        def _fix(self, tag, value):
            if not value:
                value = tag
            if not value.isalnum():
                value = "".join([c if c.isalnum() else "_" for c in value])
            if not value[0].isalpha():
                if tag[0] in value:
                    value = value[value.find(tag[0]) :]
                else:
                    value = tag[:3] + value
            if self.super_obj.index_body > 1:
                value = value + "-body{}".format(self.super_obj.index_body)
            return value.lower()

    class SanitizationPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            convert = DataSanitizationPipeline()
            _, obj = convert.deploy(xml)
            return raw, obj

    class RemoveImgSetaPipe(plumber.Pipe):
        def parser_node(self, node):
            if "/seta." in node.find("img").attrib.get("src"):
                _remove_tag(node.find("img"))

        def transform(self, data):
            raw, xml = data
            _process(xml, "a[img]", self.parser_node)
            return data

    class ConvertElementsWhichHaveIdPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            convert = ConvertElementsWhichHaveIdPipeline()
            _, obj = convert.deploy(xml)
            return raw, obj

    class FixBodyChildrenPipe(plumber.Pipe):
        ALLOWED_CHILDREN = [
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
        ]

        def transform(self, data):
            raw, xml = data
            body = xml.find(".//body")
            if body is not None and body.tag == "body":
                for child in body.getchildren():
                    if child.tag not in self.ALLOWED_CHILDREN:
                        new_child = etree.Element("p")
                        new_child.append(deepcopy(child))
                        child.addprevious(new_child)
                        body.remove(child)
                    elif child.tail:
                        new_child = etree.Element("p")
                        new_child.text = child.tail.strip()
                        child.tail = child.tail.replace(new_child.text, "")
                        child.addnext(new_child)
            return data


class DataSanitizationPipeline(object):
    def __init__(self):
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.GraphicInExtLink(),
            self.TableinBody(),
            self.TableinP(),
            self.AddPinFN(),
            self.WrapNodeInDefItem(),
        )

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)

    class SetupPipe(plumber.Pipe):
        def transform(self, data):

            new_obj = deepcopy(data)
            return data, new_obj

    class GraphicInExtLink(plumber.Pipe):
        def parser_node(self, node):

            graphic = node.find("graphic")
            graphic.tag = "inline-graphic"
            wrap_node(graphic, "p")

        def transform(self, data):
            raw, xml = data

            _process(xml, "ext-link[graphic]", self.parser_node)
            return data

    class TableinBody(plumber.Pipe):
        def parser_node(self, node):

            table = node.find("table")
            wrap_node(table, "table-wrap")

        def transform(self, data):
            raw, xml = data

            _process(xml, "body[table]", self.parser_node)
            return data

    class TableinP(TableinBody):
        def transform(self, data):
            raw, xml = data

            _process(xml, "p[table]", self.parser_node)
            return data

    class AddPinFN(plumber.Pipe):
        def parser_node(self, node):
            if node.text:
                wrap_content_node(node, "p")

        def transform(self, data):
            raw, xml = data

            _process(xml, "fn", self.parser_node)
            return data

    class WrapNodeInDefItem(plumber.Pipe):
        def parser_node(self, node):
            text = node.text or ""
            tail = node.tail or ""
            if text.strip() or tail.strip():
                wrap_content_node(node, "term")

            for c_node in node.getchildren():
                if c_node.tag not in ["term", "def"]:
                    wrap_node(c_node, "def")

        def transform(self, data):
            raw, xml = data

            _process(xml, "def-item", self.parser_node)
            return data


class ConvertElementsWhichHaveIdPipeline(object):
    def __init__(self):
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.AssetThumbnailInLayoutTableAndLinkInMessage(),
            self.AssetThumbnailInLayoutTableAndLinkInThumbnail(),
            self.RemoveTableUsedToDisplayFigureAndLabelAndCaptionInTwoLines(),
            self.RemoveTableUsedToDisplayFigureAndLabelAndCaptionSideBySide(),
            self.AssetThumbnailInLinkAndAnchorAndCaption(),
            self.AssetThumbnailInLayoutImgAndCaptionAndMessage(),
            self.RemoveThumbImgPipe(),
            self.CompleteElementAWithNameAndIdPipe(),
            self.CompleteElementAWithXMLTextPipe(),
            self.SwitchElementsAPipe(),
            self.EvaluateElementAToDeleteOrMarkAsFnLabelPipe(),
            self.DeduceAndSuggestConversionPipe(),
            self.ApplySuggestedConversionPipe(),
            self.AssetElementFixPositionPipe(),
            self.CreateDispFormulaPipe(),
            self.AssetElementAddContentPipe(),
            self.FixOutSideTablePipe(),
            self.AssetElementIdentifyLabelAndCaptionPipe(),
            self.AssetElementFixPipe(),
            self.CreateInlineFormulaPipe(),
            self.AppendixPipe(),
            self.TablePipe(),
            self.SupplementaryMaterialPipe(),
            self.RemoveXMLAttributesPipe(),
            self.ImgPipe(),
            self.FnMovePipe(),
            self.FnLabelOfPipe(),
            self.FnAddContentPipe(),
            self.FnIdentifyLabelAndPPipe(),
            self.FnFixContentPipe(),
        )

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            new_obj = deepcopy(data)
            return data, new_obj

    class AssetThumbnailInLayoutImgAndCaptionAndMessage(plumber.Pipe):
        """
        Converte o modelo de miniatura que fica dentro de uma tabela com duas
        colunas e uma linha.
        Sendo na primeira coluna a imagem em miniatura e na segunda a legenda.
        Além disso na linha seguinte à tabela há a mensagem "View larger ..."
        No parágrafo seguinte está o conteúdo que seria mostrado ao clicar em
        "View larger..."
        """
        def transform(self, data):
            raw, xml = data
            done = False
            for p in xml.findall(".//p[@content-type='html']"):
                done = self._convert(p)
                if not done:
                    pass
            if done:
                for p in xml.findall(".//p"):
                    if p.text and "View larger" in p.text:
                        parent = p.getparent()
                        parent.remove(p)
            return data

        def _convert(self, p):
            previous = p.getprevious()
            if "View larger" not in get_node_text(previous):
                return

            p_caption = previous.getprevious()
            if p_caption is None:
                return

            img = p.find(".//img")
            if img is None:
                return

            p_anchor = p_caption.getprevious()
            src = img.get("src")
            for wrong in ["http:/img/fbpe", "http://www.scielo.br/img/fbpe"]:
                src = src.replace(wrong, "/img/revistas")
            img.set("src", src)

            new_elem = etree.Element("p")
            xml = p.getroottree().find(".")
            new_a = get_anchor(xml, p_anchor, p_caption)
            new_a.append(deepcopy(img))
            new_a.append(deepcopy(p_caption))
            new_elem.append(new_a)
            new_elem.set("content-type", "created-from-layout-img-and-caption-msg")
            p.addnext(new_elem)

            for item in [p, previous, p_anchor, p_caption]:
                parent = item.getparent()
                parent.remove(item)
            return True

    class RemoveTableUsedToDisplayFigureAndLabelAndCaptionSideBySide(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for table in xml.findall(".//table"):
                tr = table.findall("tr")
                if len(tr) != 1:
                    continue

                td = tr[0].findall("td")
                if len(td) != 2:
                    continue

                img = td[0].find(".//img")
                if img is None:
                    continue
                new_a = get_anchor(xml, td[0], td[1])
                new_a.append(deepcopy(img))
                new_p = deepcopy(td[1])
                new_p.tag = "p"
                new_a.append(new_p)
                new_e = etree.Element("p")
                new_e.set("content-type", "created-from-layout-side-by-side")
                new_e.append(new_a)
                table.addprevious(new_e)
                parent = table.getparent()
                parent.remove(table)
            return data

    class RemoveTableUsedToDisplayFigureAndLabelAndCaptionInTwoLines(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for table in xml.findall(".//table"):
                tr = table.findall("tr")
                if len(tr) != 1:
                    continue

                td = tr[0].findall("td")
                if len(td) != 1:
                    continue

                p_items = td[0].findall("p")
                if len(p_items) != 2:
                    continue

                img = p_items[0].find(".//img")
                if img is None:
                    continue
                new_a = get_anchor(xml, p_items[0], p_items[1])
                new_a.append(deepcopy(img))
                new_p = deepcopy(p_items[1])
                new_p.tag = "p"
                new_a.append(new_p)
                new_e = etree.Element("p")
                new_e.set(
                    "content-type",
                    "created-from-layout-img-and-caption-in-two-lines")
                new_e.append(new_a)
                table.addprevious(new_e)
                parent = table.getparent()
                parent.remove(table)
            return data

    class AssetThumbnailInLayoutTableAndLinkInMessage(plumber.Pipe):
        """
        Converte o modelo de miniatura que fica dentro de uma tabela com duas
        colunas e uma linha.
        Sendo na primeira coluna a imagem em miniatura e na segunda a legenda.
        Além disso na linha seguinte à tabela há a mensagem "View larger ..."
        No parágrafo seguinte está o conteúdo que seria mostrado ao clicar em
        "View larger..."
        """
        def transform(self, data):
            raw, xml = data
            done = False
            for p in xml.findall(".//p[@content-type='html']"):
                done = self._replace_table_and_view_larger_message(p)
                if not done:
                    pass
            if done:
                for p in xml.findall(".//p"):
                    if p.text and "View larger" in p.text:
                        parent = p.getparent()
                        parent.remove(p)
            return data

        def _replace_table_and_view_larger_message(self, p):
            previous = p.getprevious()
            if "View larger" not in get_node_text(previous):
                return

            table = previous.getprevious()
            if table.tag != "table":
                return

            img = p.find(".//img")
            if img is None:
                return

            p_label = p.findall(".//p")
            if not p_label:
                return

            src = img.get("src")
            for wrong in ["http:/img/fbpe", "http://www.scielo.br/img/fbpe"]:
                src = src.replace(wrong, "/img/revistas")
            img.set("src", src)

            new_elem = etree.Element("p")
            xml = table.getroottree().find(".")
            new_a = get_anchor(xml, table, p_label[-1])
            new_a.append(deepcopy(img))
            new_a.append(deepcopy(p_label[-1]))
            new_elem.append(new_a)
            new_elem.set("content-type", "created-from-layout-table-and-link-in-message")
            p.addnext(new_elem)

            for item in [p, previous, table]:
                parent = item.getparent()
                parent.remove(item)
            return True

    class AssetThumbnailInLayoutTableAndLinkInThumbnail(plumber.Pipe):
        """
        Converte o modelo de miniatura que fica dentro de uma tabela com duas
        colunas e uma linha.
        Sendo na primeira coluna a imagem em miniatura com link para a imagem
        ampliada e na segunda a legenda.
        Além disso na linha seguinte à tabela há a mensagem "View larger ..."
        sem link.
        """
        def transform(self, data):
            raw, xml = data
            thumbnail = False
            for p in xml.findall(".//p[@content-type='html']"):
                previous = p.getprevious()
                if previous.tag != "table":
                    continue
                a = previous.find(".//a[@link-type='internal']")
                if a is None:
                    continue
                href = a.get("href")
                if not href or not href.startswith("#"):
                    continue
                href = href[1:]
                thumbnail_img = a.find("img")
                if thumbnail_img is None:
                    continue
                p_html_img = p.find(".//img")
                if p_html_img is None:
                    continue

                thumbnail_img_src = thumbnail_img.get("src")
                p_html_img_src = p_html_img.get("src")

                thumbnail_name, ext = os.path.splitext(thumbnail_img_src)
                name, ext = os.path.splitext(p_html_img_src)

                if (thumbnail_img_src.startswith(name) or
                    thumbnail_name.endswith("table")):
                    a_name = previous.find(".//a[@name]")
                    if a_name is not None:
                        self._create_simpler_element(p, a_name, p_html_img)
                        thumbnail = True
            if thumbnail:
                for p in xml.findall(".//p"):
                    if p.text and "View larger" in p.text:
                        parent = p.getparent()
                        parent.remove(p)
            return data

        def _create_simpler_element(self, p, a_name, p_html_img):
            table = p.getprevious()
            new_a = deepcopy(a_name)
            new_a.tail = ""
            new_p = etree.Element("p")
            if a_name.tail:
                new_p.text = a_name.tail
                a_name.tail = ""
            _next = a_name
            while True:
                _next = _next.getnext()
                if _next is None:
                    break
                new_p.append(deepcopy(_next))
            new_a.append(deepcopy(p_html_img))
            new_a.append(deepcopy(new_p))
            new_e = etree.Element("p")
            new_e.set("content-type", "created-from-layout-table-link-in-thumbnail")
            new_e.append(new_a)
            table.addprevious(new_e)
            table_parent = table.getparent()
            p_next = p.getnext()
            if p_next is not None and p_next.text:
                if "View larger" in p_next.text:
                    table_parent.remove(p_next)
            table_parent.remove(table)
            table_parent.remove(p)

    class AssetThumbnailInLinkAndAnchorAndCaption(plumber.Pipe):
        """
        Converte o modelo de miniatura que fica dentro de um link.
        No parágrafo seguinte, está a imagem ampliada + legenda.
        No parágrafo seguinte, está a âncora e a legenda.
        """
        def transform(self, data):
            raw, xml = data
            thumbnail = False
            for p in xml.findall(".//p[@content-type='html']"):
                previous = p.getprevious()
                if previous.tag != "a" or previous.get("link-type") != "internal":
                    continue
                p_next = p.getnext()
                if p_next.tag != "a":
                    p_next = p_next.findall(".//a[@name]")
                    if p_next is not None:
                        p_next = p_next[-1]
                if p_next.tag != "a":
                    continue

                a_name = p_next

                thumbnail_img = previous.find(".//img")
                if thumbnail_img is None:
                    continue
                p_html_img = p.find(".//img")
                if p_html_img is None:
                    continue

                thumbnail_img_src = thumbnail_img.get("src")
                p_html_img_src = p_html_img.get("src")

                name, ext = os.path.splitext(p_html_img_src)
                if thumbnail_img_src.startswith(name):
                    self._create_new_a(p, previous, a_name, p_html_img)
                    thumbnail = True
            if thumbnail:
                for p in xml.findall(".//p"):
                    if p.text and "View larger" in p.text:
                        parent = p.getparent()
                        parent.remove(p)
            return data

        def _create_new_a(self, p, link, a_name, p_html_img):
            new_p = etree.Element("p")
            new_p.text = a_name.tail or ""
            if a_name.tail:
                a_name.tail = ""
            _next = a_name
            remove_items = []
            while True:
                remove_items.append(_next)
                _next = _next.getnext()
                if _next is None:
                    break
                if _next.tag == "p":
                    if "View larger" in _next.text:
                        parent = _next.getparent()
                        parent.remove(_next)
                    break
                new_p.append(deepcopy(_next))

            new_a = deepcopy(a_name)
            new_a.tail = ""

            new_a.append(new_p)
            new_a.append(deepcopy(p_html_img))

            new_e = etree.Element("p")
            new_e.set("content-type", "created-from-layout-link-anchor-caption")
            new_e.append(new_a)

            p.addnext(new_e)

            # remove os elementos excedentes
            remove_items.append(p)
            remove_items.append(link)

            for item in remove_items:
                parent = item.getparent()
                parent.remove(item)

    class RemoveThumbImgPipe(plumber.Pipe):
        def parser_node(self, node):
            path = node.attrib.get("src") or ""
            if "thumb" in path:
                parent = node.getparent()
                _remove_tag(node, True)
                self._fix_a_hef_text(parent)

        def _fix_a_hef_text(self, parent):
            if parent is not None and parent.tag == "a" and parent.get("href"):
                label_text = get_node_text(parent)
                if label_text:
                    words = label_text.split()
                    if len(words) >= 2:
                        if words[1][0].isdigit():
                            label_text = " ".join(words[:2])
                        elif not words[1][0].isalnum():
                            label_text = words[0]
                if label_text:
                    for child in parent.getchildren():
                        if child.text and child.text.strip().startswith(label_text):
                            child.text = ""
                        elif child.tail and child.tail.strip().startswith(label_text):
                            child.tail = ""
                    parent.text = label_text

        def transform(self, data):
            raw, xml = data
            _process(xml, "img", self.parser_node)
            return data

    class CompleteElementAWithNameAndIdPipe(plumber.Pipe):
        """Garante que todos os elemento a[@name] e a[@id] tenham @name e @id.
        Corrige id e name caso contenha caracteres nao alphanum.
        """

        def _fix_a_href(self, xml):
            for a in xml.findall(".//a[@name]"):
                name = a.attrib.get("name")
                for a_href in xml.findall(".//a[@href='{}']".format(name)):
                    a_href.set("href", "#" + name)

        def parser_node(self, node):
            _id = node.attrib.get("id")
            _name = node.attrib.get("name")
            node.set("id", _name or _id)
            node.set("name", _name or _id)
            href = node.attrib.get("href")
            if href and href[0] == "#":
                a = etree.Element("a")
                a.set("name", node.attrib.get("name"))
                a.set("id", node.attrib.get("id"))
                node.addprevious(a)
                node.set("href", "#" + href[1:])
                node.attrib.pop("id")
                node.attrib.pop("name")

        def transform(self, data):
            raw, xml = data
            self._fix_a_href(xml)
            _process(xml, "a[@id]", self.parser_node)
            _process(xml, "a[@name]", self.parser_node)
            return data

    class CompleteElementAWithXMLTextPipe(plumber.Pipe):
        """
        Adiciona o atributo @xml_text ao elemento a, com o valor completo
        de seu rótulo. Por exemplo, explicitar se <a href="#2">2</a> é
        nota de rodapé <a href="#2" xml_text="2">2</a> ou
        Fig 2 <a href="#2" xml_text="figure 2">2</a>.
        """

        inferer = Inferer()

        def add_xml_text_to_a_href(self, xml):
            for node in xml.find(".").getchildren():
                self.add_xml_text_to_a_href_in_p(node)

        def add_xml_text_to_a_href_in_p(self, body_child):
            previous = etree.Element("none")
            nodes = body_child.findall(".//a[@href]")
            if body_child.tag == "a" and body_child.get("href"):
                nodes.insert(0, body_child)
            for node in nodes:
                text = get_node_text(node)
                if text:
                    if len(text) == 1 and text.isalpha() and text == text.upper():
                        pass
                    else:
                        text = text.lower()
                    node.set("xml_text", text)
                if text and text[0].isdigit():
                    # it is a note or other element
                    xml_text = previous.get("xml_text") or ""
                    splitted = xml_text.split()
                    if len(splitted) >= 2:
                        label, number = splitted[:2]
                        if self._is_a_sequence(number, text):
                            if previous is node.getprevious() and previous.tail:
                                words = previous.tail.split()
                                if len(words) < 2:
                                    node.set("xml_text", label + " " + text)
                previous = node

        def _get_number(self, _string):
            number = "0"
            for c in _string:
                if not c.isdigit():
                    break
                number += c
            return int(number)

        def _is_a_sequence(self, previous, next):
            previous = self._get_number(previous)
            next = self._get_number(next)
            return previous + 1 == next or previous == next

        def add_xml_text_to_other_a(self, xml):
            for node in xml.xpath(".//a[@xml_text and @href]"):
                href = node.get("href")
                xml_text = node.get("xml_text")
                if xml_text:
                    for n in xml.findall(".//a[@href='{}']".format(href)):
                        if not n.get("xml_text"):
                            n.set("xml_text", xml_text)
                    for n in xml.findall(".//a[@name='{}']".format(href[1:])):
                        if not n.get("xml_text"):
                            n.set("xml_text", xml_text)

        def transform(self, data):
            raw, xml = data
            logger.info("CompleteElementAWithXMLTextPipe")
            self.add_xml_text_to_a_href(xml)
            self.add_xml_text_to_other_a(xml)
            return data

    class DeduceAndSuggestConversionPipe(plumber.Pipe):
        """Este pipe analisa os dados dos elementos a[@href] e a[@name],
        deduz e sugere tag, id, ref-type para a conversão de elementos,
        adicionando aos elementos a, os atributos: @xml_tag, @xml_id,
        @xml_reftype, @xml_label.
        Por exemplo:
        - a[@href] pode ser convertido para link para um
        ativo digital, pode ser link para uma nota de rodapé, ...
        - a[@name] pode ser convertido para a fig, table-wrap,
        disp-formula, fn, app etc
        Nota: este pipe não executa a conversão.
        """

        inferer = Inferer()

        def _update(self, node, elem_name, ref_type, new_id, text=None):
            node.set("xml_tag", elem_name)
            node.set("xml_reftype", ref_type)
            node.set("xml_id", new_id)
            if text:
                node.set("xml_label", text)

        def _add_xml_attribs_to_a_href_from_text(self, texts):
            for text, data in texts.items():
                nodes_with_id, nodes_without_id = data
                tag_reftype = self.inferer.tag_and_reftype_from_a_href_text(text)
                if not tag_reftype:
                    continue

                tag, reftype = tag_reftype
                node_id = None
                for node in nodes_with_id:
                    node_id = node.attrib.get("href")[1:]
                    new_id = node_id
                    self._update(node, tag, reftype, new_id, text)

                for node in nodes_without_id:
                    alt_id = None
                    if not node_id:
                        href = node.attrib.get("href")
                        tag_reftype_id = self.inferer.tag_and_reftype_and_id_from_filepath(
                            href, tag
                        )
                        if tag_reftype_id:
                            alt_tag, alt_reftype, alt_id = tag_reftype_id
                    if node_id or alt_id:
                        new_id = node_id or alt_id
                        self._update(node, tag, reftype, new_id, text)

        def _classify_nodes(self, nodes):
            incomplete = []
            complete = None
            for node in nodes:
                data = (
                    node.attrib.get("xml_label"),
                    node.attrib.get("xml_tag"),
                    node.attrib.get("xml_reftype"),
                    node.attrib.get("xml_id"),
                )
                if all(data) and not complete:
                    complete = data
                else:
                    incomplete.append(node)
            return complete, incomplete

        def _add_xml_attribs_to_a_href_from_file_paths(self, file_paths):
            for path, nodes in file_paths.items():
                new_id = None
                complete, incomplete = self._classify_nodes(nodes)
                if complete:
                    text, tag, reftype, new_id = complete
                else:
                    tag_reftype_id = self.inferer.tag_and_reftype_and_id_from_filepath(
                        path
                    )
                    if tag_reftype_id:
                        tag, reftype, _id = tag_reftype_id
                        new_id = _id
                        text = ""
                if new_id:
                    for node in incomplete:
                        self._update(node, tag, reftype, new_id, text)

        def _add_xml_attribs_to_a_name(self, a_names):
            for name, a_name_and_hrefs in a_names.items():
                new_id = None
                a_name, a_hrefs = a_name_and_hrefs

                complete, incomplete = self._classify_nodes(a_hrefs)
                if complete:
                    text, tag, reftype, new_id = complete
                else:
                    tag_reftype = self.inferer.tag_and_reftype_from_a_href_text(
                        a_name.tail
                    )
                    if not tag_reftype:
                        tag_reftype = self.inferer.tag_and_reftype_from_name(name)
                    if tag_reftype:
                        tag, reftype = tag_reftype
                        new_id = name
                        text = ""
                if new_id:
                    self._update(a_name, tag, reftype, new_id, text)
                    for node in incomplete:
                        self._update(node, tag, reftype, new_id, text)

        def _search_asset_node_related_to_img(self, new_id, img):
            if new_id:
                asset_node = img.getroottree().find(".//*[@xml_id='{}']".format(new_id))
                if asset_node is not None:
                    return asset_node
            found = search_asset_node_backwards(img, "xml_tag")
            if found is not None and found.attrib.get("name"):
                if found.attrib.get("xml_tag") in ASSET_TAGS:
                    return found

        def _add_xml_attribs_to_img(self, images):
            for path, images in images.items():
                text, new_id, tag, reftype = None, None, None, None
                tag_reftype_id = self.inferer.tag_and_reftype_and_id_from_filepath(path)
                if tag_reftype_id:
                    tag, reftype, _id = tag_reftype_id
                    new_id = _id
                for img in images:
                    found = self._search_asset_node_related_to_img(new_id, img)
                    if found is not None:
                        text = found.attrib.get("xml_label")
                        new_id = found.attrib.get("xml_id")
                        tag = found.attrib.get("xml_tag")
                        reftype = found.attrib.get("xml_reftype")
                    if all([tag, reftype, new_id]):
                        self._update(img, tag, reftype, new_id, text)

        def transform(self, data):
            raw, xml = data
            document = Document(xml)
            texts, file_paths = document.a_href_items
            names = document.a_names
            images = document.images
            self._add_xml_attribs_to_a_href_from_text(texts)
            self._add_xml_attribs_to_a_name(names)
            self._add_xml_attribs_to_a_href_from_file_paths(file_paths)
            self._add_xml_attribs_to_img(images)
            return data

    class EvaluateElementAToDeleteOrMarkAsFnLabelPipe(plumber.Pipe):
        """
        No texto há âncoras (a[@name]) e referencias cruzada (a[@href]):
        TEXTO->NOTAS e NOTAS->TEXTO.
        Remove as âncoras e referências cruzadas relacionadas com NOTAS->TEXTO.
        Também remover duplicidade de a[@name]
        Algumas NOTAS->TEXTO podem ser convertidas a "fn/label"
        """

        def _grouped_by_same_name_and_href(self, xml):
            groups = {}
            for a in xml.findall(".//a"):
                _id = a.attrib.get("name")
                if not _id:
                    href = a.attrib.get("href")
                    if href and href.startswith("#"):
                        _id = href[1:]
                if _id:
                    groups[_id] = groups.get(_id, [])
                    groups[_id].append(a)
            return groups

        def _grouped_by_same_xml_text(self, xml):
            groups = {}
            for a in xml.findall(".//a[@xml_text]"):
                xml_text = a.get("xml_text")
                if xml_text:
                    groups[xml_text] = groups.get(xml_text, [])
                    groups[xml_text].append(a)
            return groups

        def _keep_only_one_a_name(self, items):
            # remove os a[@name] repetidos, se aplicável
            a_names = [n for n in items if n.attrib.get("name")]
            for n in a_names[1:]:
                items.remove(n)
                _remove_tag(n)

        def _find_label_of(self, a_href, a_items):
            """
            Em um documento html, pode haver:

            No início do documento, o título com:
            - uma âncora do topo (tx*)
            - um link para nota de rodapé (#nt*)
            <p>
            <b>
            O regime de competência no setor público brasileiro:
            uma pesquisa empírica sobre a utilidade da informação
            contábil
            </b>
            <a id="tx*" name="tx*" xml_text="*"></a>
            <a href="#nt*" xml_text="*"><sup>*</sup></a></b>
            </p>

            No fim do documento:
            - âncora da nota do rodapé (nt*)
            - link para o topo (#tx*)
            <p><a id="nt*" name="nt*" xml_text="*"></a>
            <a href="#tx*" xml_text="*">*</a>
            Artigo apresentado no 12º Congresso USP de
            Controladoria e Contabilidade, São Paulo, julho de 2012</p>

            Esta função para a[@href='#tx*'], deve retornar a[@name='nt*']
            """
            for a in [item for item in a_items if item.get("name")]:
                if "#" + a.get("name") != a_href.get("href"):
                    if a.getnext() is a_href:
                        return a

        def _convert_to_fn_label(self, a_href_items, grouped_by_xml_text):
            a_href_items = a_href_items or []
            for a_href in a_href_items:
                xml_text = a_href.get("xml_text")
                if get_node_text(a_href) and is_footnote_label(xml_text):
                    logger.info(
                        "Identifica como fn/label: %s" %
                        etree.tostring(a_href))
                    a_href.tag = "label"
                    #a_href.attrib.pop("href")
                    group = grouped_by_xml_text.get(xml_text)

                    a = self._find_label_of(a_href, group)
                    if a is not None:
                        a_href.set("label-of", a.get("name"))
                    logger.info(etree.tostring(a_href))

        def _is_convertible_to_fn_label(self, a_items):
            if a_items[0].get("name") is None:
                return
            a_name = a_items[0]
            a_name_xml_text = a_name.get("xml_text", "")
            if " " in a_name_xml_text or not is_footnote_label(a_name_xml_text):
                return
            a_href_items = [a for a in a_items[1:] if a.get("href")]
            if len(a_href_items) > 0:
                a_name.tag = "_EXCLUDE_REMOVETAG"
                return a_href_items

        def _exclude_invalid_unique_a_href(self, nodes):
            if len(nodes) == 1 and nodes[0].attrib.get("href"):
                _remove_tag(nodes[0])

        def transform(self, data):
            raw, xml = data
            logger.info("EvaluateElementAToDeleteOrCreateFnLabelPipe")
            grouped_by_id = self._grouped_by_same_name_and_href(xml)
            grouped_by_xml_text = self._grouped_by_same_xml_text(xml)
            for _id, a_items in grouped_by_id.items():
                self._keep_only_one_a_name(a_items)
                a_href_items = self._is_convertible_to_fn_label(a_items)
                self._convert_to_fn_label(a_href_items, grouped_by_xml_text)
                self._exclude_invalid_unique_a_href(a_items)
            etree.strip_tags(xml, "_EXCLUDE_REMOVETAG")
            logger.info("EvaluateElementAToDeleteOrCreateFnLabelPipe - fim")
            return data

    class SwitchElementsAPipe(plumber.Pipe):
        def parser_node(self, node):
            if (node.tail or "").strip():
                return
            xml_text = node.get("xml_text")
            if is_footnote_label(xml_text):
                _next = node.getnext()
                if _next is not None and _next.tag == "a" and _next.get("name"):
                    _next.addnext(deepcopy(node))
                    parent = node.getparent()
                    parent.remove(node)

        def transform(self, data):
            raw, xml = data
            _process(xml, "a[@href]", self.parser_node)
            return data

    class ApplySuggestedConversionPipe(plumber.Pipe):
        """
        Converte os elementos a, para as tags correspondentes, considerando
        os valores dos atributos: @xml_tag, @xml_id, @xml_reftype, @xml_label,
        inseridos por DeduceAndSuggestConversionPipe()
        """

        def _remove_a(self, a_name, a_href_items):
            _remove_tag(a_name, True)
            for a_href in a_href_items:
                _remove_tag(a_href, True)

        def _update_a_name(self, node, new_id, new_tag):
            _name = node.attrib.get("name")
            node.set("id", new_id)
            if new_tag == "symbol":
                node.set("symbol", _name)
                new_tag = "fn"
            elif new_tag == "corresp":
                node.set("fn-type", "corresp")
                new_tag = "fn"
            node.tag = new_tag

        def _update_a_href_items(self, a_href_items, new_id, reftype):
            for ahref in a_href_items:
                ahref.attrib.clear()
                ahref.set("ref-type", reftype)
                ahref.set("rid", new_id)
                ahref.tag = "xref"

        def transform(self, data):
            raw, xml = data
            document = Document(xml)
            for name, a_name_and_hrefs in document.a_names.items():
                a_name, a_hrefs = a_name_and_hrefs
                if a_name.attrib.get("xml_id"):
                    new_id = a_name.attrib.get("xml_id")
                    new_tag = a_name.attrib.get("xml_tag")
                    reftype = a_name.attrib.get("xml_reftype")
                    self._update_a_name(a_name, new_id, new_tag)
                    self._update_a_href_items(a_hrefs, new_id, reftype)
                else:
                    self._remove_a(a_name, a_hrefs)
            return data

    class AssetElementFixPositionPipe(plumber.Pipe):
        """
        Move os elementos de ativos digitais, por exemplo:
        <p><fig/></p>
        para fora de modo que fique ao lado dos irmãos que serão conteúdo do
        ativo digital
        """

        def _set_move(self, node):
            node.set("move", "false")
            parent = node.getparent()
            if parent is not None:
                grand_parent = parent.getparent()
                if grand_parent is not None:
                    if (
                        not node.getchildren()
                        and node.getnext() is None
                        and not get_node_text(node)
                    ):
                        node.set("move", "true")

        def _set_move_for_nodes(self, xml):
            if xml.find(".//*[@move]") is None:
                for tag in ASSET_TAGS:
                    for node in xml.xpath(".//{}".format(tag)):
                        self._set_move(node)
                return
            for node in xml.xpath(".//*[@move='?']"):
                self._set_move(node)

        def _move_node(self, node):
            node.set("move", "?")
            parent = node.getparent()
            parent.addnext(deepcopy(node))
            parent.remove(node)

        def transform(self, data):
            raw, xml = data
            self._set_move_for_nodes(xml)
            while True:
                if not xml.xpath(".//*[@move='true']"):
                    break
                for node in xml.xpath(".//*[@move='true']"):
                    self._move_node(node)
                self._set_move_for_nodes(xml)
            for node in xml.xpath(".//*[@move]"):
                node.attrib.pop("move")
            return data

    class AssetElementAddContentPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for tag in ASSET_TAGS:
                logger.info("AssetElementAddContentPipe - {}".format(tag))
                for asset_node in xml.findall(".//{}".format(tag)):
                    logger.info(etree.tostring(asset_node))
                    asset_node.set("status", "identify-content")
                    if not self._is_complete(asset_node):
                        components = self._find_components(asset_node)
                        for component in components:
                            p = component.getparent()
                            asset_node.append(deepcopy(component))
                            p.remove(component)
            return data

        def _is_complete(self, asset_node):
            img = asset_node.xpath(".//img")
            table = asset_node.xpath(".//table")
            label = asset_node.xpath(".//*[@content-type='label']")
            return label and (img or table)

        def _find_components(self, asset_node):
            """
            Procura os componentes do elemento ativo digital
            que estão como nós irmãos à direita
            """
            ASSET_TAGS_XPATH = ".//fig | .//table-wrap | .//app | .//disp-formula"
            img = asset_node.find(".//img")
            table = asset_node.find(".//table")
            label = asset_node.find(".//*[@content-type='label']")
            if label is None:
                self._find_label(
                    asset_node, asset_node.get("id"), asset_node.get("xml_text")
                )
                label = asset_node.find(".//*[@content-type='label']")
            found = (label, img, table)
            components = []
            max_times = 3 - len([item for item in found if item is not None])

            i = 0

            _next = asset_node
            while True:
                if i == max_times:
                    break
                if label is not None and (img is not None or table is not None):
                    break
                _next = _next.getnext()
                if _next is None:
                    break
                if _next.tag in ASSET_TAGS:
                    break
                if _next.xpath(ASSET_TAGS_XPATH):
                    break
                if label is None:
                    label = self._find_label(
                        _next, asset_node.get("id"), asset_node.get("xml_text")
                    )
                if img is None:
                    img = self._find_img_or_table(_next, "img")
                if table is None:
                    table = self._find_img_or_table(_next, "table")

                i += 1
                if _next.get("content-type"):
                    components.append(_next)
            return components

        def _find_label(self, node, asset_id, search_by):
            if node.tag == "bold" and node.get("label-of"):
                label = node
                node.set("content-type", "label")
                return node
            label = node.find(".//bold[@label-of]")
            if label is not None:
                parent = label.getparent()
                if not parent.getchildren()[0] is label:
                    return
            if label is None and search_by:
                text = get_node_text(node)
                if matched_first_two_words(text, search_by):
                    self._create_label_in_node_text(node, asset_id, text)
                else:
                    self._create_label_in_node_tail(node, asset_id, search_by)
                label = node.find(".//bold[@label-of]")
            if label is not None:
                node.set("content-type", "label")
                return node

        def _create_label_in_node_text(self, node, asset_id, text):
            startswith = " ".join(text.split()[:2])
            found = None
            if node.text and node.text.startswith(text):
                found = node
            else:
                for n in node.findall(".//*"):
                    if n.text and n.text.startswith(startswith):
                        found = n
                        break
            if found is not None:
                if found.tag == "bold":
                    label = found
                    label.set("label-of", asset_id)

                else:
                    label = etree.Element("bold")
                    label.text = startswith
                    label.tail = found.text[len(label.text) :]
                    label.set("label-of", asset_id)
                    copy = deepcopy(found)
                    found.clear()
                    found.append(label)
                    for child in copy.getchildren():
                        found.append(child)

        def _create_label_in_node_tail(self, node, asset_id, search_by):
            tail = (node.tail or "").strip()
            if matched_first_two_words(tail, search_by):
                label = etree.Element("bold")
                label.text = " ".join(tail.split()[:2])
                label.set("label-of", asset_id)
                node.tail = node.tail[len(label.text) :]
                node.addnext(label)

        def _find_img_or_table(self, node, tag):
            found = None
            if node.tag == tag:
                found = node
            if found is None:
                found = node.find(".//{}".format(tag))
            if found is not None:
                node.set("content-type", tag)
                return node

    class FixOutSideTablePipe(plumber.Pipe):

        def transform(self, data):
            raw, xml = data

            for node in xml.xpath(".//table-wrap"):

                parent = node.getparent()

                if parent.getnext() is not None:

                    p = parent.getnext()

                    for p_neighbor in p.getchildren():
                        if p_neighbor.tag == 'table':
                            node.append(deepcopy(p))
                            parent.getparent().remove(p)
            return data

    class AssetElementIdentifyLabelAndCaptionPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            logger.info("AssetElementIdentifyLabelAndCaptionPipe")
            for asset_node in xml.findall(".//*[@status='identify-content']"):
                self._mark_label_and_caption(asset_node)
            return data

        def _add_nodes_to_element_title(self, nodes_for_title, n):
            if n is None:
                return
            if n is None or n.tag in ["table", "img"]:
                return
            if n.find(".//table") is not None:
                return
            if n.find(".//img") is not None:
                return
            nodes_for_title.append(n)

        def _infer_label_and_caption(self, label_parent, clue):
            label_text = None
            caption_title_text = None
            nodes_for_title = []
            start = label_parent
            label_parent_text = label_parent.text
            if label_parent_text:
                label_parent.text = ""
                if label_parent_text.lower().startswith(clue):
                    label_text = label_parent_text[: len(clue)]
                    caption_title_text = label_parent_text[len(clue) :]
                else:
                    words = matched_first_two_words(label_parent_text, clue)
                    if words:
                        parts = label_parent_text.split()
                        label_text = " ".join(parts[:2])
                        caption_title_text = " ".join(parts[2:])
                nodes_for_title = []
                for n in start.getchildren():
                    self._add_nodes_to_element_title(nodes_for_title, n)
            return label_text, caption_title_text, nodes_for_title

        def _mark_label_and_caption(self, asset_node):
            label_text = None
            caption_title_text = None
            nodes_for_title = []
            bold = asset_node.find(".//bold[@label-of]")
            if bold is None:
                data = self._find_label_and_caption(asset_node)
            else:
                data = self._find_caption(bold)
            if data:
                label_text, caption_title_text, nodes_for_title = data
                self._create_label_and_caption(
                    asset_node, label_text, caption_title_text, nodes_for_title
                )
                if bold is not None:
                    parent = bold.getparent()
                    if parent is not None:
                        parent.remove(bold)

        def _find_label_and_caption(self, asset_node):
            label_pattern = asset_node.get("xml_text")
            if label_pattern is None or not label_pattern[0].isalpha():
                return
            label_parent = asset_node.find(".//*[@content-type='label']")
            if label_parent is None:
                label_parent = asset_node

            return self._infer_label_and_caption(label_parent, label_pattern)

        def _find_caption(self, bold):
            # label já está identificado
            label_text = bold.text
            caption_title_text = bold.tail
            nodes_for_title = []
            n = bold
            while True:
                t = len(nodes_for_title)
                n = n.getnext()
                self._add_nodes_to_element_title(nodes_for_title, n)
                if t == len(nodes_for_title):
                    break
            return label_text, caption_title_text, nodes_for_title

        def _create_label_and_caption(
            self, asset_node, label_text, caption_title_text, nodes_for_title
        ):
            if label_text:
                label = etree.Element("label")
                label.text = label_text
                asset_node.append(label)
            if caption_title_text or nodes_for_title:
                caption = etree.Element("caption")
                title = etree.Element("title")
                title.text = caption_title_text
                caption.append(title)
                asset_node.append(caption)
                for n in nodes_for_title:
                    title.append(deepcopy(n))
                    p = n.getparent()
                    p.remove(n)

    class AssetElementFixPipe(plumber.Pipe):
        COMPONENT_TAGS = ("label", "caption", "img")

        def transform(self, data):
            raw, xml = data
            logger.info("AssetElementFixPipe")
            for asset_tag in ASSET_TAGS:
                for asset in xml.findall(".//{}".format(asset_tag)):
                    logger.info(etree.tostring(asset))
                    new_asset = etree.Element(asset_tag)
                    new_asset.set("id", asset.get("id"))
                    new_asset.tail = asset.tail

                    for tag in self.COMPONENT_TAGS:
                        for component in asset.findall(".//{}".format(tag)):
                            if component is not None:
                                new_asset.append(deepcopy(component))

                    new_asset_text = get_node_text(new_asset)
                    extra_component = False
                    for child in asset.getchildren():
                        for node in child.findall(".//*"):
                            if not node.getchildren():
                                text = get_node_text(node)
                                if text not in new_asset_text:
                                    new_asset.append(child)
                                    extra_component = True
                    if extra_component:
                        logger.info("AssetElementFixPipe: unexpected content?")
                    asset.addprevious(new_asset)
                    p = asset.getparent()
                    p.remove(asset)
                    logger.info(etree.tostring(new_asset))
            return data

    class CreateDispFormulaPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for node in xml.findall(".//img[@xml_tag='disp-formula']"):
                previous = node.getprevious()
                id = node.get("xml_id")
                if previous is None or previous.tag != "disp-formula":
                    disp_formula = etree.Element("disp-formula")
                    disp_formula.set("id", id)
                    disp_formula.set("name", id)
                    for attr, value in node.attrib.items():
                        if attr.startswith("xml_"):
                            disp_formula.set(attr, value)
                    node.addprevious(disp_formula)
            return data

    class CreateInlineFormulaPipe(plumber.Pipe):
        DISP_FORMULA_PARENTS = (
            "app",
            "app-group",
            "bio",
            "body",
            "boxed-text",
            "disp-formula-group",
            "disp-quote",
            "fig",
            "glossary",
            "license-p",
            "named-content",
            "notes",
            "p",
            "ref-list",
            "sec",
            "styled-content",
            "supplementary-material",
            "td",
            "term",
            "th",
        )
        INLINE_FORMULA_PARENTS = (
            "addr-line",
            "alt-title",
            "article-title",
            "attrib",
            "award-id",
            "bold",
            "collab",
            "comment",
            "compound-kwd-part",
            "compound-subject-part",
            "conf-theme",
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
            "product",
            "roman",
            "sans-serif",
            "sc",
            "strike",
            "styled-content",
            "sub",
            "subject",
            "subtitle",
            "sup",
            "supplement",
            "td",
            "term",
            "term-head",
            "th",
            "title",
            "trans-subtitle",
            "trans-title",
            "underline",
            "verse-line",
        )

        def transform(self, data):
            raw, xml = data
            for node in xml.findall(".//disp-formula"):
                parent = node.getparent()
                inline = False
                if parent.tag not in self.DISP_FORMULA_PARENTS:
                    if parent.tag in self.INLINE_FORMULA_PARENTS:
                        inline = True
                if not inline:
                    inline = (
                        node.getprevious() is not None
                        or node.getnext() is not None
                        or node.tail
                    )
                if inline:
                    node.tag = "inline-formula"
            return data

    class AppendixPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            remove_items = []
            for node in xml.xpath(".//app"):
                previous = node.getprevious()
                if previous is None or previous.tag != "app":
                    app_group = etree.Element("app-group")
                    node.addprevious(app_group)
                if node.find("label") is None:
                    text = None
                    for xref in xml.findall(
                        ".//xref[@rid='{}']".format(node.get("id"))
                    ):
                        text = get_node_text(xref)
                        if text:
                            break
                    if text:
                        label = etree.Element("label")
                        label.text = text
                        node.insert(0, label)
                caption = node.find("caption")
                if caption is not None:
                    caption.tag = "REMOVETAG"
                app_group.append(deepcopy(node))
                remove_items.append(node)
            etree.strip_tags(xml, "REMOVETAG")
            for item in remove_items:
                parent = item.getparent()
                parent.remove(item)
            return data

    class TablePipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for node in xml.findall(".//fig"):
                table = node.find(".//table")
                if table is not None and node.find(".//table-wrap") is None:
                    table.tag = "array"
                    table.attrib.clear()
                    if table.find("tbody") is None:
                        table.set("fix", "true")
                    if table is not None and table.getparent().tag != "fig":
                        for child in node.getchildren():
                            if table in child.getchildren():
                                child.addnext(deepcopy(table))
                                parent = table.getparent()
                                parent.remove(table)

            for node in xml.findall(".//table-wrap"):
                table = node.find(".//table")
                if table is not None and table.getparent().tag != "table-wrap":
                    for child in node.getchildren():
                        if table in child.getchildren():
                            child.addnext(deepcopy(table))
                            parent = table.getparent()
                            parent.remove(table)

            for node in xml.findall(".//table"):
                if node.getparent().tag != "table-wrap":
                    node.tag = "array"
                    node.attrib.clear()
                    if node.find("tbody") is None:
                        node.set("fix", "true")

            while True:
                if xml.find(".//array[@fix]") is None:
                    break
                for node in xml.findall(".//array[@fix]"):
                    node.attrib.clear()
                    if node.find("tbody") is None:
                        tbody = deepcopy(node)
                        tbody.tag = "tbody"
                        array = etree.Element("array")
                        array.append(tbody)
                        node.addnext(array)
                        parent = node.getparent()
                        parent.remove(node)
            return data

    class SupplementaryMaterialPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for node in xml.findall(".//a[@link-type='pdf']"):
                href = node.get("href")
                node.tag = "inline-supplementary-material"
                node.attrib.clear()
                node.set("{http://www.w3.org/1999/xlink}href", href)

            return data

    class RemoveXMLAttributesPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            for node in xml.findall(".//*[@xml_tag]"):
                for k in node.attrib.keys():
                    if k.startswith("xml_") or k == "name":
                        node.attrib.pop(k)
            return data

    class ImgPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "graphic"
            src = node.attrib.pop("src")
            node.attrib.clear()
            node.set("{http://www.w3.org/1999/xlink}href", src)

        def transform(self, data):
            raw, xml = data
            _process(xml, "img", self.parser_node)
            return data

    class FnMovePipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            self._move_fn_out_of_style_tags(xml)
            self._remove_p_if_fn_is_only_child(xml)
            return data

        def _move_fn_out_of_style_tags(self, xml):
            changed = True
            while changed:
                changed = False
                for tag in ("sup", "bold", "italic"):
                    self._identify_fn_to_move_out(xml, tag)
                    ret = self._move_fn_out(xml)
                    if ret:
                        changed = True

        def _remove_p_if_fn_is_only_child(self, xml):
            for p in xml.findall(".//p[fn]"):
                if len(p.findall(".//*")) == 1 and not get_node_text(p):
                    p.tag = "REMOVEPIFFNISONLYCHLDREMOVETAG"
            etree.strip_tags(xml, "REMOVEPIFFNISONLYCHLDREMOVETAG")

        def _identify_fn_to_move_out(self, xml, style_tag):
            for node in xml.findall(".//{}[fn]".format(style_tag)):
                text = (node.text or "").strip()
                children = node.getchildren()
                if children[0].tag == "fn" and not text:
                    node.set("move", "backward")
                elif children[-1].tag == "fn" and not (children[-1].tail or "").strip():
                    node.set("move", "forward")

        def _move_fn_out(self, xml):
            changed = False
            for node in xml.findall(".//*[@move]"):
                move = node.attrib.pop("move")
                if move == "backward":
                    self._move_fn_out_and_backward(node)
                elif move == "forward":
                    self._move_fn_out_and_forward(node)
                changed = True
            return changed

        def _move_fn_out_and_backward(self, node):
            fn = node.find("fn")
            fn_copy = deepcopy(fn)
            fn_copy.tail = ""
            node.addprevious(fn_copy)
            node.text = fn.tail
            node.remove(fn)

        def _move_fn_out_and_forward(self, node):
            fn = node.getchildren()[-1]
            fn_copy = deepcopy(fn)
            node.addnext(fn_copy)
            node.remove(fn)

    class FnLabelOfPipe(plumber.Pipe):
        """Cria fn a partir de label[@label-of]
        ou adiciona label em fn
        """

        def transform(self, data):
            raw, xml = data
            logger.info("FnLabelOfPipe")
            labels = [
                label.get("label-of") for label in xml.findall(".//label[@label-of]")
            ]
            repeated = [label for label in labels if labels.count(label) > 1]
            for label in set(repeated):
                labels = xml.findall(".//label[@label-of='{}']".format(label))
                for item in labels[1:]:
                    fn = etree.Element("fn")
                    fn.set("id", label + item.get("xml_text"))
                    item.addprevious(fn)
            for label in xml.findall(".//label[@label-of]"):
                label_of = label.get("label-of")
                if label_of not in repeated:
                    fn = xml.find(".//fn[@id='{}']".format(label_of))
                    if fn is None:
                        fn = etree.Element("fn")
                        fn.set("id", label_of)
                        label.addprevious(fn)
                    fn.append(deepcopy(label))
                    parent = label.getparent()
                    parent.remove(label)
            return data

    class FnAddContentPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            logger.info("FnAddContentPipe")
            for fn in xml.findall(".//fn"):
                fn.set("status", "add-content")
            while True:
                fn = xml.find(".//fn[@status='add-content']")
                if fn is None:
                    break
                fn.set("status", "identify-content")
                self._add_fn_tail_into_fn(fn)
            self._move_fn_out_of_fn_tags(xml)
            return data

        def _add_fn_tail_into_fn(self, node):
            logger.info("FnAddContentPipe._add_fn_tail_into_fn")
            move_tail_into_node(node)
            while True:
                _next = node.getnext()
                if _next is None:
                    break
                if node.find("label") is not None and node.find("p") is not None:
                    break
                if _next.tag in ["fn"]:
                    break
                if _next.tag in ["p"]:
                    if node.find("p") is not None:
                        break
                node.append(deepcopy(_next))
                parent = _next.getparent()
                parent.remove(_next)

        def _move_fn_out_of_fn_tags(self, xml):
            while True:
                for node in xml.findall(".//fn"):
                    if "fn-children" in node.attrib.keys():
                        node.attrib.pop("fn-children")
                    found = node.findall(".//fn")
                    if len(found) > 0:
                        node.set("fn-children", str(len(found)))
                fn = xml.find(".//fn[@fn-children]")
                if fn is None:
                    break
                items = []
                for inner_fn in fn.findall(".//fn"):
                    items.insert(0, inner_fn)
                for item in items:
                    parent = item.getparent()
                    fn.addnext(deepcopy(item))
                    parent.remove(item)

    class FnIdentifyLabelAndPPipe(plumber.Pipe):
        def _create_label(self, new_fn, node):
            label = node.find(".//label")
            if label is not None:
                return

            children = node.getchildren()
            node_text = (node.text or "").strip()
            if node_text:
                # print("FnIdentifyLabelAndPPipe - _create_label_from_node_text")
                logger.info("FnIdentifyLabelAndPPipe - _create_label_from_node_text")
                label = self._create_label_from_node_text(new_fn, node)
            elif children:
                # print("FnIdentifyLabelAndPPipe - _create_label_from_style_tags")
                logger.info("FnIdentifyLabelAndPPipe - _create_label_from_style_tags")
                self._create_label_from_style_tags(new_fn, node)
                if new_fn.find(".//label") is None:
                    # print("FnIdentifyLabelAndPPipe - _create_label_from_children")
                    logger.info("FnIdentifyLabelAndPPipe - _create_label_from_children")
                    self._create_label_from_children(new_fn, node)
            logger.info(etree.tostring(new_fn))

        def _create_label_from_node_text(self, new_fn, node):
            # print(etree.tostring(node))
            label_text = self._get_label_text(node)
            if label_text:
                label = etree.Element("label")
                label.text = label_text
                new_fn.insert(0, label)
                node.text = node.text.replace(label_text, "").lstrip()
            # print(etree.tostring(node))

        def _get_label_text(self, node):
            node_text = get_node_text(node)
            if not node_text:
                return
            splitted = [item.strip() for item in node_text.split()]
            logger.info("_get_label_text")
            logger.info(splitted)
            label_text = None
            if splitted[0][0].isalpha():
                if len(splitted[0]) == 1 and node_text[0].lower() == node_text[0]:
                    label_text = splitted[0]
            else:
                label_text = self._get_not_alpha_characteres(splitted[0])
            return label_text

        def _get_not_alpha_characteres(self, text):
            label_text = []
            for c in text:
                if not c.isalpha():
                    label_text.append(c)
                else:
                    break
            return "".join(label_text)

        def _create_label_from_children(self, new_fn, node):
            """
            Melhorar
            b'<fn id="back2"><italic>** Address: Rua Itapeva 366 conj 132 - 01332-000 S&#227;o Paulo SP - Brasil.</italic></fn>'
            """
            # print(etree.tostring(node))
            label_text = self._get_label_text(node)
            if label_text:
                label = etree.Element("label")
                label.text = label_text
                new_fn.insert(0, label)
                for n in node.findall(".//*"):
                    if n.text and n.text.startswith(label_text):
                        n.text = n.text.replace(label_text, "")
                        break

        def _create_label_from_style_tags(self, new_fn, node):
            STYLE_TAGS = ("sup", "bold", "italic")
            children = node.getchildren()
            node_style = None
            if children[0].tag in STYLE_TAGS:
                node_style = children[0]
            else:
                for tag in ["sup", "bold", "italic"]:
                    n = children[0].find(".//{}".format(tag))
                    if n is None:
                        continue
                    if not n.getchildren():
                        node_style = n
                        break
            if node_style is not None:
                node_text = get_node_text(node)
                node_style_text = get_node_text(node_style)
                if node_style_text == node_text:
                    node_style = None
            if node_style is not None:
                label = etree.Element("label")
                cp = deepcopy(node_style)
                cp.tail = ""
                label.append(cp)
                new_fn.insert(0, label)
                node.text = node_style.tail
                parent = node_style.getparent()
                parent.remove(node_style)

        def _create_p(self, new_fn, node):
            new_p = None
            if (node.text or "").strip():
                new_p = etree.Element("p")
                new_p.text = node.text
            for child in node.getchildren():
                if child.tag in ["label", "p"]:
                    new_p = self._create_new_p(new_fn, new_p, child)
                else:
                    if new_p is None:
                        new_p = etree.Element("p")
                    new_p.append(deepcopy(child))
            if new_p is not None:
                new_fn.append(new_p)
            node.tag = "DELETE"
            node.addprevious(new_fn)

        def _create_new_p(self, new_fn, new_p, child):
            if new_p is not None:
                new_fn.append(new_p)

            p = deepcopy(child)
            p.tail = ""
            new_fn.append(p)

            new_p = None
            if child.tail:
                new_p = etree.Element("p")
                new_p.text = child.tail
            return new_p

        def _identify_label_and_p(self, fn):
            new_fn = etree.Element("fn")
            for k, v in fn.attrib.items():
                if k in ["id", "label", "fn-type"]:
                    new_fn.set(k, v)
            self._create_label(new_fn, fn)
            self._create_p(new_fn, fn)
            fn.addprevious(new_fn)
            for delete in fn.getroottree().findall(".//DELETE"):
                parent = delete.getparent()
                parent.remove(delete)

        def transform(self, data):
            raw, xml = data
            for fn in xml.findall(".//fn"):
                logger.info("FnIdentifyLabelAndPPipe")
                self._identify_label_and_p(fn)
            return data

    class FnFixContentPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data
            logger.info("FnFixContentPipe")
            for fn in xml.findall(".//fn"):
                children = fn.getchildren()
                label = fn.find(".//label")
                if label is not None:
                    label.attrib.clear()
                    bold = label.find("*[@label-of]")
                    if bold is not None:
                        bold.attrib.clear()
                    if children[0].tag == "p" and children[0].text in ["(", "["]:
                        label.text = (
                            children[0].text + label.text + children[2].text[:1]
                        )
                        children[2].text = children[2].text[1:]
                        fn.remove(children[0])
                    elif children[0] is not label:
                        logger.info(
                            "FnFixContentPipe: %s" % etree.tostring(children[0])
                        )
            return data


def join_texts(texts):
    return " ".join([item.strip() for item in texts if item and item.strip()])


def search_asset_node_backwards(node, attr="id"):

    previous = node.getprevious()
    if previous is not None:
        if previous.attrib.get(attr):
            if len(previous.getchildren()) == 0:
                return previous

    parent = node.getparent()
    if parent is not None:
        previous = parent.getprevious()
        if previous is not None:
            asset = previous.find(".//*[@{}]".format(attr))
            if asset is not None:
                if len(asset.getchildren()) == 0:
                    return asset


def search_backwards_for_elem_p_or_body(node):
    up = node.getparent()
    while up is not None and up.tag not in ["p", "body"]:
        last = up
        up = up.getparent()
    if up.tag == "p":
        return up
    if up.tag == "body":
        return last


def create_p_for_asset(a_href, asset):

    new_p = etree.Element("p")
    new_p.set("content-type", "asset")
    new_p.append(asset)

    up = search_backwards_for_elem_p_or_body(a_href)

    _next = up
    while _next is not None and _next.attrib.get("content-type") == "asset":
        up = _next
        _next = up.getnext()

    up.addnext(new_p)


class Document:
    def __init__(self, xmltree):
        self.xmltree = xmltree

    @property
    def a_href_items(self):
        texts = {}
        file_paths = {}
        for a_href in self.xmltree.findall(".//a[@href]"):
            href = a_href.attrib.get("href").strip()
            text = a_href.get("xml_text")

            if text:
                if text not in texts.keys():
                    # tem id, nao tem id
                    texts[text] = ([], [])
                i = 0 if href and href[0] == "#" else 1
                texts[text][i].append(a_href)

            if href:
                if href[0] != "#" and ":" not in href and "@" not in href:
                    filename, __ = files.extract_filename_ext_by_path(href)
                    if filename not in file_paths.keys():
                        file_paths[filename] = []
                    file_paths[filename].append(a_href)
        return texts, file_paths

    @property
    def a_names(self):
        names = {}
        for a in self.xmltree.findall(".//a[@name]"):
            name = a.attrib.get("name").strip()
            if name:
                if name not in names.keys():
                    names[name] = (
                        a,
                        self.xmltree.findall('.//a[@href="#{}"]'.format(name)),
                    )
        return names

    @property
    def images(self):
        items = {}
        for img in self.xmltree.findall(".//img[@src]"):
            value = img.attrib.get("src").lower().strip()
            if value:
                filename, __ = files.extract_filename_ext_by_path(value)
                if filename not in items.keys():
                    items[filename] = []
                items[filename].append(img)
        return items


class FileLocation:
    def __init__(self, href):
        self.href = href
        self.basename = os.path.basename(href)
        self.new_href, self.ext = os.path.splitext(self.basename)

    @property
    def remote(self):
        file_path = self.href
        if file_path.startswith("/"):
            file_path = file_path[1:]
        return os.path.join(config.get("STATIC_URL_FILE"), file_path)

    @property
    def local(self):
        parts = self.remote.split("/")
        _local = "/".join(parts[-4:])
        _local = os.path.join(config.get("SITE_SPS_PKG_PATH"), _local)
        return _local.replace("//", "/")

    @property
    def content(self):
        _content = self.local_content
        if not _content:
            _content = self.download()
            if _content:
                self.save(_content)
        logger.info("%s %s" % (len(_content or ""), self.local))
        return _content

    @property
    def local_content(self):
        logger.info("Get local content from: %s" % self.local)
        if self.local and os.path.isfile(self.local):
            logger.info("Found")
            with open(self.local, "rb") as fp:
                return fp.read()

    def download(self):
        logger.info("Download %s" % self.remote)
        r = requests.get(self.remote, timeout=TIMEOUT)
        if r.status_code == 404:
            logger.error(
                "FAILURE. REQUIRES MANUAL INTERVENTION. Not found %s. " % self.remote
            )
            return
        if not r.status_code == 200:
            logger.error("%s: %s" % (self.remote, r.status_code))
            return
        return r.content

    def save(self, content):
        dirname = os.path.dirname(self.local)
        if not dirname.startswith(config.get("SITE_SPS_PKG_PATH")):
            logger.info(
                "%s: valor inválido de caminho local para ativo digital" % self.local
            )
            return
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(self.local, "wb") as fp:
            fp.write(content)


def fix_img_revistas_path(node):
    attr = "src" if node.get("src") else "href"
    location = node.get(attr)
    if "fbpe" in location or "revistas" in location or "img" in location:
        if ":" in location or location[0] == "#":
            return
        old_location = location
        if location.startswith("img"):
            location = "/" + location
        if " " in location:
            location = "".join(location.split())
        location = location.replace("/img/fbpe", "/img/revistas")
        location = location[location.find("/img/revistas") :]
        if old_location != location:
            logger.info(
                "fix_img_revistas_path: de {} para {}".format(old_location, location)
            )
            node.set(attr, location)


class Remote2LocalConversion:
    """
    - Identifica os a[@href] e os classifica
    - Se o arquivo é um HTML, baixa-o do site config.get("STATIC_URL_FILE")
    - Armazena-o em config.get("SITE_SPS_PKG_PATH"),
      mantendo a estrutura de acron/volnum
    - Insere seu conteúdo dentro de self.body
    - Se o arquivo é um link para uma imagem externa, transforma em img
    """

    IMG_EXTENSIONS = (".gif", ".jpg", ".jpeg", ".svg", ".png", ".tif", ".bmp")

    def __init__(self, xml):
        self.xml = xml
        self.body = self.xml.find(".//body")
        self._digital_assets_path = None
        self.imported_files = []

    @property
    def img_src_in_original_body(self):
        return [
            item.attrib["src"]
            for item in self.body.findall(".//img[@src]")
            if not item.get("imported")
        ]

    def find_digital_assets_path(self):
        for node in self.xml.xpath(".//*[@src]|.//*[@href]"):
            fix_img_revistas_path(node)
        for node in self.xml.xpath(".//*[@src]|.//*[@href]"):
            location = node.get("src", node.get("href"))
            if location.startswith("/img/"):
                dirnames = os.path.dirname(location).split("/")
                return "/".join(dirnames[:5])

    @property
    def digital_assets_path(self):
        if self._digital_assets_path is None:
            self._digital_assets_path = self.find_digital_assets_path()
        return self._digital_assets_path

    @property
    def body_children(self):
        if self.body is not None:
            return self.body.findall("*")
        return []

    def remote_to_local(self):
        self._import_html_files()
        self._import_img_files()
        self._remove_repeated_imported_images()

    def _classify_element_a_which_has_href_attribute(self):
        """
        Classifica o elemento a, de acordo com o conteúdo de seu atributo href.
        - external: link para site
        - internal: link para algum elemento interno (href="#?")
        - html: link para html que contém ativos digitais
        - pdf: link para pdf que está em /pdf/acron/volnum
        - asset: link para uma imagem que está em /img/revistas/acron/volnum
        - unknown: quando não foi identificado
        """
        if self.digital_assets_path is None:
            return
        for node in self.xml.findall(".//*[@src]"):
            fix_img_revistas_path(node)
            src = node.get("src")
            if ":" in src:
                node.set("link-type", "external")
                logger.info("Added @link-type: %s" % etree.tostring(node))
                continue

            value = src.split("/")[0]
            if "." in value:
                if src.startswith("./") or src.startswith("../"):
                    node.set(
                        "src",
                        os.path.join(
                            self.digital_assets_path, src[src.find("/") + 1 :]
                        ),
                    )
                else:
                    # pode ser URL
                    node.set("link-type", "external")
                    logger.info("Added @link-type: %s" % etree.tostring(node))
                    continue
                fix_img_revistas_path(node)

        for a_href in self.xml.findall(".//*[@href]"):
            if not a_href.get("link-type"):
                fix_img_revistas_path(a_href)
                href = a_href.get("href")

                if href.count('"') == 2:
                    node.set("href", href.replace('"', ""))
                    href = node.get("href")

                if ":" in href:
                    a_href.set("link-type", "external")
                    logger.info("Added @link-type: %s" % etree.tostring(a_href))
                    continue

                if href and href[0] == "#":
                    a_href.set("link-type", "internal")
                    logger.info("Added @link-type: %s" % etree.tostring(a_href))
                    continue

                value = href.split("/")[0]
                if "." in value:
                    if href.startswith("./") or href.startswith("../"):
                        a_href.set(
                            "href",
                            os.path.join(
                                self.digital_assets_path, href[href.find("/") + 1 :]
                            ),
                        )
                    else:
                        # pode ser URL
                        a_href.set("link-type", "external")
                        logger.info("Added @link-type: %s" % etree.tostring(a_href))
                        continue

                fix_img_revistas_path(a_href)
                href = a_href.get("href")
                basename = os.path.basename(href)
                f, ext = os.path.splitext(basename)
                if ".htm" in ext:
                    a_href.set("link-type", "html")
                elif href.startswith("/pdf/"):
                    a_href.set("link-type", "pdf")
                elif href.startswith("/img/revistas"):
                    a_href.set("link-type", "asset")
                else:
                    a_href.set("link-type", "unknown")
                logger.info("Added @link-type: %s" % etree.tostring(a_href))

    def _import_html_files(self):
        """
        Obtém o conteúdo de HTML mencionados no body e os insere no body.
        Após inserir o conteúdo do HTML, repete a operação, pois dentro do
        conteúdo importado, pode haver menção a outros HTML. Então,
        repete isso até que não exista menções a HTML
        """
        self._classify_element_a_which_has_href_attribute()
        while True:
            if self.body.find(".//a[@link-type='html']") is None:
                break

            self._import_html_files_content()
            self._classify_element_a_which_has_href_attribute()

    def _import_html_files_content(self):
        """
        Obtém o conteúdo de HTML mencionados no body e os insere no body.
        """
        new_p_items = []
        for bodychild in self.body_children:
            a_items = bodychild.findall(".//a[@link-type='html']")
            if bodychild.tag == "a" and bodychild.get("link-type") == "html":
                a_items.insert(0, bodychild)
            for a_link_type in a_items:
                new_p = self._imported_html_file(a_link_type)
                if new_p is not None:
                    new_p_items.append((bodychild, new_p))
        for bodychild, new_p in new_p_items[::-1]:
            logger.info(
                "Insere novo p com conteudo do HTML: %s" % etree.tostring(new_p)
            )
            bodychild.addnext(new_p)
        return len(new_p_items)

    def _imported_html_file(self, a_link_type):
        """
        Retorna novo elemento que representa o conteúdo do html importado,
        se aplicável
        """
        logger.info("Importar HTML de %s" % etree.tostring(a_link_type))
        href = a_link_type.get("href")
        if "#" in href:
            href, anchor = href.split("#")

        f, ext = os.path.splitext(href)
        new_href = os.path.basename(f)

        if href in self.imported_files:
            self._update_a_href(a_link_type, new_href)
        else:
            self.imported_files.append(href)
            html_body = self._get_html_body(href)
            if html_body is None:
                logger.info("Alterando para link para externo")
                a_link_type.set("link-type", "asset-not-found")
            else:
                self._update_a_href(a_link_type, new_href)
                content_type = "html"
                delete_tag = "REMOVE_" + content_type
                node_content = self._create_new_element_for_imported_html_file(
                    new_href, html_body, delete_tag
                )
                new_p = self._create_new_p(new_href, node_content, content_type)
                etree.strip_tags(new_p, delete_tag)
                return new_p

    def _get_html_body(self, href):
        """
        Obtém o conteúdo do HTML mencionado em node_a/@href e o retorna
        como um novo elemento
        """
        file_location = FileLocation(href)
        if file_location.content:
            html_tree = etree.fromstring(
                file_location.content, parser=etree.HTMLParser()
            )
            if html_tree is not None:
                return html_tree.find(".//body")

    def _import_img_files(self):
        """
        Localiza as menções a imagens (a/@href="/img/revistas/..."),
        as converte para um link interno que aponta para o novo elemento (img ou media)
        e cria este novo elemento (img ou media) para ser inserido no parágrafo
        seguinte.
        """
        new_p_items = []
        for child in self.body_children:
            for node_a in child.findall(".//a[@link-type='asset']"):
                new_p = self._imported_img_file(node_a)
                if new_p is not None:
                    new_p_items.append((child, new_p))
        for bodychild, new_p in new_p_items[::-1]:
            logger.info("Insere novo p: %s" % etree.tostring(new_p))
            bodychild.addnext(new_p)
        return len(new_p_items)

    def _imported_img_file(self, node_a):
        """
        Retorna novo elemento que representa a imagem importada,
        se aplicável
        """
        logger.info("Converte %s" % etree.tostring(node_a))
        href = node_a.get("href")
        f, ext = os.path.splitext(href)
        new_href = os.path.basename(f)

        self._update_a_href(node_a, new_href)

        if href in self.img_src_in_original_body:
            # já existe no body
            return

        if href in self.imported_files:
            # já está importado
            return

        self.imported_files.append(href)
        content_type = "asset"
        node_content = self._create_new_element_for_imported_img_file(node_a, href)
        if node_content is not None:
            new_p = self._create_new_p(new_href, node_content, content_type)
            return new_p

    def _update_a_href(self, a_href, new_href):
        a_href.set("href", "#" + new_href)
        a_href.set("link-type", "internal")
        logger.info("Atualiza a[@href]: %s" % etree.tostring(a_href))

    def _create_new_p(self, new_href, node_content, content_type):
        """
        Cria o elemento p para inserir o(s) ativo(s) digital(is) proveniente(s)
        de arquivo de imagem ou arquivo HTML mencionado.
        """
        a_name = etree.Element("a")
        a_name.set("id", new_href)
        a_name.set("name", new_href)

        new_p = etree.Element("p")
        new_p.set("content-type", content_type)
        new_p.append(a_name)

        if content_type == "asset":
            a_name.append(node_content)
        else:
            a_name.addnext(node_content)

        logger.info("Cria novo p: %s" % etree.tostring(new_p))

        return new_p

    def _create_new_element_for_imported_html_file(
        self, new_href, html_body, delete_tag="REMOVETAG"
    ):
        """
        Cria novo elemento para representar os ativos digitais que estão contidos em um arquivo HTML
        """
        # Criar o a[@name] com o conteúdo do body
        body = deepcopy(html_body)
        body.tag = delete_tag
        for a in body.findall(".//a"):
            logger.info("Encontrado elem a no body importado: %s" % etree.tostring(a))
            href = a.get("href")
            if href and href[0] == "#":
                a.set("href", "#" + new_href + href[1:].replace("#", "X"))
            elif a.get("name"):
                a.set("name", new_href + "X" + a.get("name"))
            logger.info("Atualiza elem a importado: %s" % etree.tostring(a))

        for img in body.findall(".//img"):
            src = img.get("src")
            name, ext = os.path.splitext(os.path.basename(src))

            if body.find(".//a[@name='{}']".format(name)) is None:
                a_name = etree.Element("a")
                a_name.set("name", name)
                a_name.set("id", name)
                img.addprevious(a_name)
            img.set("imported", "true")

        a_name = body.find(".//a[@name='{}']".format(new_href))
        if a_name is not None:
            a_name.tag = delete_tag
        return body

    def _create_new_element_for_imported_img_file(self, node_a, location):
        """
        Cria novo elemento para representar o ativo digital do arquivo de imagem
        """
        tag = "img"
        ign, ext = os.path.splitext(location)
        if ext.lower() not in self.IMG_EXTENSIONS:
            tag = "media"
        asset = etree.Element(tag)
        asset.set("src", location)
        asset.set("imported", "true")
        return asset

    def _remove_repeated_imported_images(self):
        """
        Pode acontecer casos de importar mais de uma vez uma imagem, pois
        ela pode ter sido mencionada com a[@href] e também dentro de um HTML.
        Manter a primeira ocorrência.
        """
        checked = []
        for asset in self.body.findall(".//*[@imported]"):
            if asset.attrib["src"] in checked:
                parent = asset.getparent()
                if parent is not None:
                    parent.remove(asset)
            else:
                checked.append(asset.attrib["src"])

        for content_type in ["html", "asset"]:
            for p in self.body.findall(".//p[@content-type='{}']".format(content_type)):
                if p.find(".//*[@src]") is None:
                    parent = p.getparent()
                    if parent is not None:
                        parent.remove(p)
