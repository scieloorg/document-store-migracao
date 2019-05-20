import logging
import plumber
import html
import re
import os
from lxml import etree
from copy import deepcopy
from documentstore_migracao.utils import files
from documentstore_migracao.utils import xml as utils_xml
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def _remove_element_or_comment(node):
    parent = node.getparent()
    if parent is not None:
        if node.tail:
            text = (node.text or "").strip() + node.tail
            previous = node.getprevious()
            if previous is not None:
                if not previous.tail:
                    previous.tail = ""
                previous.tail += text
            else:
                if not parent.text:
                    parent.text = ""
                parent.text += text

        removed = node.tag
        try:
            node.tag = "REMOVE_NODE"

        except AttributeError:
            parent.remove(node)

        else:
            if node.getchildren():
                etree.strip_tags(parent, "REMOVE_NODE")
            else:
                parent.remove(node)

        return removed


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


def gera_id(_string):

    number_item = re.search(r"([a-zA-Z]{1,3})(\d)([a-zA-Z])", _string)
    if number_item:
        name_item, number_item, sufix_item = number_item.groups("")
        rid = name_item + str(int(number_item)) + sufix_item
        return rid


class CustomPipe(plumber.Pipe):
    def __init__(self, super_obj=None, *args, **kwargs):

        self.super_obj = super_obj
        super(CustomPipe, self).__init__(*args, **kwargs)


class HTML2SPSPipeline(object):
    def __init__(self, pid, index_body=1):
        self.pid = pid
        self.index_body = index_body
        self._ppl = plumber.Pipeline(
            self.SetupPipe(super_obj=self),
            self.SaveRawBodyPipe(super_obj=self),
            self.DeprecatedHTMLTagsPipe(),
            self.RemoveExcedingStyleTagsPipe(),
            self.RemoveEmptyPipe(),
            self.RemoveStyleAttributesPipe(),
            self.RemoveCommentPipe(),
            self.HTMLEscapingPipe(),
            self.BRPipe(),
            self.PPipe(),
            self.DivPipe(),
            self.ANamePipe(super_obj=self),
            self.TablePipe(),
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
            self.TableCleanPipe(),
            self.BlockquotePipe(),
            self.HrPipe(),
            self.GraphicChildrenPipe(),
            self.RemovePWhichIsParentOfPPipe(),
            self.RemoveRefIdPipe(),
            self.SanitizationPipe(),
        )

    class SetupPipe(CustomPipe):
        def transform(self, data):
            xml = utils_xml.str2objXML(data)
            return data, xml

    class SaveRawBodyPipe(CustomPipe):
        def transform(self, data):
            raw, xml = data
            root = xml.getroottree()
            root.write(
                os.path.join("/tmp/", "%s.xml" % self.super_obj.pid),
                encoding="utf-8",
                doctype=config.DOC_TYPE_XML,
                xml_declaration=True,
                pretty_print=True,
            )
            return data, xml

    class DeprecatedHTMLTagsPipe(CustomPipe):
        TAGS = ["font", "small", "big", "dir", "span", "s", "lixo", "center"]

        def transform(self, data):
            raw, xml = data
            for tag in self.TAGS:
                nodes = xml.findall(".//" + tag)
                if len(nodes) > 0:
                    etree.strip_tags(xml, tag)
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
            return node.findall("*") == [] and not (node.text or "").strip()

        def _remove_empty_tags(self, xml):
            removed_tags = []
            for node in xml.xpath("//*"):
                if node.tag not in self.EXCEPTIONS:
                    if self._is_empty_element(node):
                        removed = _remove_element_or_comment(node)
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
            node.tag = "p"
            _id = node.attrib.pop("id", None)
            node.attrib.clear()
            if _id:
                node.set("id", _id)

        def transform(self, data):
            raw, xml = data

            _process(xml, "div", self.parser_node)
            return data

    class ANamePipe(CustomPipe):

        def find_a_href(self, root, _id_name):
            return root.find('.//a[@href="#{}"]'.format(_id_name))

        def parser_node(self, node):
            attrib = node.attrib

            _id_name = attrib.get("name", attrib.get("id", "")).lower()
            if _id_name.startswith("top") or _id_name.startswith("back"):
                return

            root = node.getroottree()
            if _id_name.startswith("tx"):
                _remove_element_or_comment(node)
                _remove_element_or_comment(self.find_a_href(root, _id_name))
            elif _id_name.startswith("t"):
                a_href = self.find_a_href(root, _id_name)
                if a_href and a_href.text and 'tab' in a_href.text.lower():
                    node.tag = "table-wrap"
                else:
                    node.tag = "fn"
            elif _id_name[0] in "fcq":
                node.tag = "fig"
            elif _id_name.startswith("n"):
                node.tag = "fn"

            node.attrib.clear()
            ref_id = "%s-%s" % (
                gera_id(_id_name) or _id_name,
                self.super_obj.index_body,
            )
            if ref_id:
                node.set("ref-id", ref_id)
            node.set("id", ref_id)

        def transform(self, data):
            raw, xml = data

            _process(xml, "a[@name]", self.parser_node)
            return data

    class TablePipe(plumber.Pipe):
        def parser_node_table(self, node):

            _id = node.attrib.get("id")
            if _id:
                p = etree.Element("table-wrap")
                _node = deepcopy(node)
                p.append(_node)

                id_name = gera_id(new_element[0] + id_name[-1])
                if id_name:
                    p.set("id", id_name)

                parent = node.getparent()
                parent.append(p)
                parent.remove(node)

        def transform(self, data):
            raw, xml = data

            _process(xml, "table[@id]", self.parser_node_table)
            return data

    class ImgPipe(plumber.Pipe):
        def parser_node(self, node):
            node.tag = "graphic"
            _attrib = deepcopy(node.attrib)
            src = _attrib.pop("src")

            node.attrib.clear()
            node.set("{http://www.w3.org/1999/xlink}href", src)

            filename, __ = files.extract_filename_ext_by_path(src)
            if "t" in filename:
                new_element = "table-wrap"
                id_name = filename.split("t")
            else:
                id_name = filename.split("f")
                new_element = "fig"

            n_id = gera_id(new_element[0] + id_name[-1])
            if n_id:
                root = node.getroottree()
                ref_node = root.find("//%s[@ref-id='%s']" % (new_element, n_id))
                if ref_node is not None:
                    _node = deepcopy(node)
                    ref_node.append(_node)

                    parent = node.getparent()
                    parent.remove(node)

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
        def _parser_node_external_link(self, node, extlinktype="uri"):
            node.tag = "ext-link"

            href = node.attrib.get("href")
            node.attrib.clear()
            _attrib = {
                "ext-link-type": extlinktype,
                "{http://www.w3.org/1999/xlink}href": href,
            }
            node.attrib.update(_attrib)

        def _create_email(self, node):
            a_node_copy = deepcopy(node)
            href = a_node_copy.attrib.get("href")
            if "mailto:" in href:
                href = href.split("mailto:")[1]

            node.attrib.clear()
            node.tag = "email"

            img = node.find("img")
            if img is not None:
                graphic = etree.Element("graphic")
                graphic.attrib["{http://www.w3.org/1999/xlink}href"] = img.attrib["src"]
                _remove_element_or_comment(img)
                parent = node.getprevious() or node.getparent()
                graphic.append(node)
                parent.append(graphic)

            if not href:
                return

            if node.text and node.text.strip():
                if href == node.text:
                    pass
                elif href in node.text:
                    node.tag = "REMOVE_TAG"
                    texts = node.text.split(href)
                    node.text = texts[0]
                    email = etree.Element("email")
                    email.text = href
                    email.tail = texts[1]
                    node.append(email)
                    etree.strip_tags(node.getparent(), "REMOVE_TAG")
                else:
                    node.attrib["{http://www.w3.org/1999/xlink}href"] = href
            if not node.text:
                node.text = href

        def _parser_node_anchor(self, node):
            node.tag = "xref"
            href = node.attrib.get("href")
            if href.startswith("#top") or href.startswith("#back"):

                list_c_node = list(node.getchildren())
                c_text = "".join([t.strip() for t in node.itertext()])

                if (
                    len(list_c_node) == 1
                    and c_text == ""
                    and list_c_node[0].tag == "graphic"
                ):
                    node.remove(list_c_node[0])
                _remove_element_or_comment(node)


            node.attrib.clear()
            root = node.getroottree()

            xref_name = href.replace("#", "")
            if xref_name == "ref":

                rid = node.text
                if not rid.isdigit():
                    rid = (
                        rid.replace("(", "")
                        .replace(")", "")
                        .replace("-", ",")
                        .split(",")
                    )
                    rid = rid[0]
                node.set("rid", "B%s" % rid)
                node.set("ref-type", "bibr")

            else:
                rid = gera_id(xref_name)
                if rid:
                    ref_node = root.find("//*[@ref_id='%s']" % rid)
                    node.set("rid", xref_name)
                    if ref_node is not None:
                        ref_type = ref_node.tag
                        if ref_type == "table-wrap":
                            ref_type = "table"
                        node.set("ref-type", ref_type)

        def parser_node(self, node):
            try:
                href = node.attrib["href"].strip()
            except KeyError:
                logger.debug("\tTag 'a' sem href removendo node do xml")
                _remove_element_or_comment(node)
            else:
                if href.startswith("#"):
                    self._parser_node_anchor(node)
                elif "mailto" in href or "@" in href:
                    self._create_email(node)
                elif "/" in href or href.startswith("www") or "http" in href:
                    self._parser_node_external_link(node)

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
                    _remove_element_or_comment(c_node)

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

        def transform(self, data):
            raw, xml = data

            _process(xml, "graphic", self.parser_node)
            return data

    class RemoveCommentPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            comments = xml.xpath("//comment()")
            for comment in comments:
                _remove_element_or_comment(comment)
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

    class RemovePWhichIsParentOfPPipe(plumber.Pipe):
        def _tag_texts(self, xml):
            for node in xml.xpath(".//p[p]"):
                if node.text and node.text.strip():
                    new_p = etree.Element("p")
                    new_p.text = node.text
                    node.text = ""
                    node.insert(0, new_p)

                for child in node.iter():
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

        def transform(self, data):
            raw, xml = data
            self._tag_texts(xml)
            self._identify_extra_p_tags(xml)
            self._tag_text_in_body(xml)
            etree.strip_tags(xml, "REMOVE_P")
            return data

    class RemoveRefIdPipe(plumber.Pipe):
        def parser_node(self, node):
            node.attrib.pop("ref-id", None)

        def transform(self, data):
            raw, xml = data

            _process(xml, "*[@ref-id]", self.parser_node)
            return data

    class SanitizationPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            convert = DataSanitizationPipeline()
            _, obj = convert.deploy(xml)
            return raw, obj

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)


class DataSanitizationPipeline(object):
    def __init__(self):
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.GraphicInExtLink(),
            self.HRTagPape(),
            self.TableinBody(),
            self.TableinP(),
        )

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)

    class SetupPipe(plumber.Pipe):
        def transform(self, data):

            new_obj = deepcopy(data)
            return data, new_obj

    class GraphicInExtLink(plumber.Pipe):
        NEW_TAG = "p"

        def parser_node(self, node):

            graphic = node.find("graphic")
            _graphic = deepcopy(graphic)
            _graphic.tag = "inline-graphic"
            p = etree.Element(self.NEW_TAG)
            p.append(_graphic)
            node.append(p)
            node.remove(graphic)

        def transform(self, data):
            raw, xml = data

            _process(xml, "ext-link[graphic]", self.parser_node)
            return data

    class HRTagPape(plumber.Pipe):
        def parser_node(self, node):

            element = etree.fromstring(
                "<table-wrap><table><tr><td><hr/></td></tr></table></table-wrap>"
            )
            node.getparent().replace(node, element)

        def transform(self, data):
            raw, xml = data

            _process(xml, "hr", self.parser_node)
            return data

    class TableinBody(plumber.Pipe):
        def parser_node(self, node):

            table = node.find("table")
            _table = deepcopy(table)
            w_wrap = etree.Element("table-wrap")
            w_wrap.append(_table)
            node.append(w_wrap)
            node.remove(table)

        def transform(self, data):
            raw, xml = data

            _process(xml, "body[table]", self.parser_node)
            return data

    class TableinP(TableinBody):
        def transform(self, data):
            raw, xml = data

            _process(xml, "p[table]", self.parser_node)
            return data
