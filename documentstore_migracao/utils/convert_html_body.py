import logging
import plumber
import html
import re
import os
from urllib import request, error
from copy import deepcopy
from lxml import etree
from documentstore_migracao.utils import files
from documentstore_migracao.utils import xml as utils_xml
from documentstore_migracao import config


logger = logging.getLogger(__name__)


TEMP_A_HREF_TEXTS = "/tmp/dsm_ahref_texts.txt"
TEMP_A_NAMES = "/tmp/dsm_a_names.txt"
TEMP_FILEPATHS = "/tmp/dsm_filepaths.txt"

STARTSWITH_RETURNS_TAG_AND_REFTYPE = tuple(
    [tuple(item.strip().split()) for item in open(config.CONVERSION_TAGS).readlines()]
)


def join_texts(texts):
    return " ".join([item for item in texts if item])


def _preserve_node_tail_before_remove_node(node, node_text):
    parent = node.getparent()
    if node.tail:
        text = join_texts([node_text.rstrip(), node.tail.lstrip()])
        previous = node.getprevious()
        if previous is not None:
            previous.tail = join_texts([(previous.tail or "").rstrip(), text])
        else:
            parent.text = join_texts([(parent.text or "").rstrip(), text])


def _remove_element_or_comment(node, remove_inner=False):
    parent = node.getparent()
    if parent is None:
        return

    removed = node.tag
    try:
        node.tag = "REMOVE_NODE"
    except AttributeError:
        is_comment = True
        node_text = ""
    else:
        is_comment = False
        node_text = node.text or ""
        text = get_node_text(node)

    if is_comment or remove_inner or not text.strip():
        _preserve_node_tail_before_remove_node(node, node_text)
        parent.remove(node)
        return removed
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


def gera_id(_string, index_body):
    rid = _string
    number_item = re.search(r"([a-zA-Z]{1,3})(\d+)([a-zA-Z0-9]+)?", _string)
    if number_item:
        name_item, number_item, sufix_item = number_item.groups("")
        rid = name_item + number_item + sufix_item

    if not rid[0].isalpha():
        rid = "replace_by_reftype" + rid

    if index_body == 1:
        return rid.lower()

    ref_id = "%s-body%s" % (rid, index_body)
    return ref_id.lower()


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


def find_or_create_asset_node(root, elem_name, elem_id, node=None):
    if elem_name is None or elem_id is None:
        return
    xpath = './/{}[@id="{}"]'.format(elem_name, elem_id)
    asset = root.find(xpath)
    if asset is None and node is not None:
        asset = search_asset_node_backwards(node)
    if asset is None:
        if node is not None:
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
    return join_texts([item for item in node.itertext() if item])


def get_other_node_which_same_text(root, a_href_text):
    for node in root.findall(".//xref"):
        text = get_node_text(node)
        if text == a_href_text:
            return node


def first_alpha_characteres(text):
    t = []
    for c in text:
        if c.isalpha():
            t.append(c)
        else:
            break
    return "".join(t)


class Inferer:

    REFTYPE = {"table-wrap": "table", "ref": "bibr"}

    def ref_type(self, elem_name):
        return self.REFTYPE.get(elem_name, elem_name)

    def tag_and_reftype_from_name(self, name):
        if not name:
            return
        for prefix in ["not", "_ftnref"]:
            if name.startswith(prefix) and name[len(prefix) :].isdigit():
                return
        for prefix in ["titulo", "title", "tx", "top", "home"]:
            if name.startswith(prefix):
                return
        for prefix, tag in STARTSWITH_RETURNS_TAG_AND_REFTYPE:
            if name.startswith(prefix):
                return tag, self.ref_type(tag)
        if not name[0].isalnum():
            if name[0] == "*":
                return
            return "symbol", "fn"
        return "fn", "fn"

    def tag_and_reftype_from_a_href_text(self, a_href_text):
        if not a_href_text.strip():
            return
        a_href_text = a_href_text.strip().lower()

        for i, c in enumerate(a_href_text):
            if not c.isalnum():
                continue
            else:
                break
        text = a_href_text[i:]
        if text[0].isdigit():
            return "fn", "fn"
        for prefix, tag in STARTSWITH_RETURNS_TAG_AND_REFTYPE:
            if text.startswith(prefix) and len(prefix) > 1:
                return tag, self.ref_type(tag)
        if "corresp" in a_href_text:
            return "corresp", "corresp"

    def tag_and_reftype_and_id_from_filepath(self, file_path):
        filename, __ = files.extract_filename_ext_by_path(file_path)
        for prefix, tag in STARTSWITH_RETURNS_TAG_AND_REFTYPE:
            if tag is None:
                continue
            if prefix == filename:
                return tag, self.ref_type(tag), filename
            if prefix in filename:
                parts = filename.split(prefix)
                if len(parts) < 2:
                    continue
                if parts[0] and parts[0][-1].isalpha():
                    continue
                if parts[1] and parts[1][0].isalpha():
                    continue
                if parts[1]:
                    return tag, self.ref_type(tag), prefix + "".join(parts[1:])


class Document:
    def __init__(self, xmltree):
        self.xmltree = xmltree
        self.inferer = Inferer()

    @property
    def a_href_items(self):
        texts = {}
        file_paths = {}
        for a_href in self.xmltree.findall(".//a[@href]"):
            href = a_href.attrib.get("href").strip()
            text = get_node_text(a_href).lower().strip()

            if text:
                if text not in texts.keys():
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


class CustomPipe(plumber.Pipe):
    def __init__(self, super_obj=None, *args, **kwargs):

        self.super_obj = super_obj
        super(CustomPipe, self).__init__(*args, **kwargs)


class HTML2SPSPipeline(object):
    def __init__(self, pid, index_body=1):
        self.pid = pid
        self.index_body = index_body
        self.document = Document(None)
        self._ppl = plumber.Pipeline(
            self.SetupPipe(super_obj=self),
            self.SaveRawBodyPipe(super_obj=self),
            self.DeprecatedHTMLTagsPipe(),
            self.RemoveImgSetaPipe(),
            self.RemoveDuplicatedIdPipe(),
            self.RemoveExcedingStyleTagsPipe(),
            self.RemoveEmptyPipe(),
            self.RemoveStyleAttributesPipe(),
            self.RemoveCommentPipe(),
            self.HTMLEscapingPipe(),
            self.BRPipe(),
            self.PPipe(),
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
            self.RemoveThumbImgPipe(),
            self.FixElementAPipe(super_obj=self),
            self.InternalLinkAsAsteriskPipe(super_obj=self),
            self.DocumentPipe(super_obj=self),
            self.AnchorAndInternalLinkPipe(super_obj=self),
            self.AssetsPipe(super_obj=self),
            self.APipe(super_obj=self),
            self.ImgPipe(super_obj=self),
            self.TdCleanPipe(),
            self.TableCleanPipe(),
            self.BlockquotePipe(),
            self.HrPipe(),
            self.TagsHPipe(),
            self.DispQuotePipe(),
            self.GraphicChildrenPipe(),
            self.RemovePWhichIsParentOfPPipe(),
            self.RemoveRefIdPipe(),
            self.SanitizationPipe(),
        )

    class SetupPipe(CustomPipe):
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

    class RemoveDuplicatedIdPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            nodes = xml.findall(".//*[@id]")
            root = xml.getroottree()
            for node in nodes:
                attr = node.attrib
                d_ids = root.findall(".//*[@id='%s']" % attr["id"])
                if len(d_ids) > 1:
                    for index, d_n in enumerate(d_ids[1:]):
                        d_n.set("id", "%s-duplicate-%s" % (attr["id"], index))

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

    class ImgPipe(CustomPipe):
        def parser_node(self, node):
            node.tag = "graphic"
            src = node.attrib.pop("src")
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

    class APipe(CustomPipe):
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

            if not href:
                # devido ao caso do href estar mal
                # formado devemos so trocar a tag
                # e retorna para continuar o Pipe
                return

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
            root = node.getroottree()

            href = node.attrib.pop("href")

            node.tag = "xref"
            node.attrib.clear()

            xref_name = href.replace("#", "")
            if xref_name == "ref":
                rid = node.text or ""
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
                rid = gera_id(xref_name, self.super_obj.index_body)
                ref_node = root.find("//*[@xref_id='%s']" % rid)

                node.set("rid", rid)
                if ref_node is not None:
                    ref_type = ref_node.tag
                    if ref_type == "table-wrap":
                        ref_type = "table"
                    node.set("ref-type", ref_type)
                    ref_node.attrib.pop("xref_id")
                else:
                    # nao existe a[@name=rid]
                    _remove_element_or_comment(node, xref_name == "top")

        def parser_node(self, node):
            try:
                href = node.attrib["href"].strip()
            except KeyError:
                if "id" not in node.attrib.keys():
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

                for child in node.iterchildren():
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
            node.attrib.pop("xref_id", None)

        def transform(self, data):
            raw, xml = data

            _process(xml, "*[@xref_id]", self.parser_node)
            return data

    class SanitizationPipe(plumber.Pipe):
        def transform(self, data):
            raw, xml = data

            convert = DataSanitizationPipeline()
            _, obj = convert.deploy(xml)
            return raw, obj

    class FixElementAPipe(CustomPipe):
        def parser_node(self, node):
            _id = node.attrib.get("id")
            _name = node.attrib.get("name")
            if _id is None or (_name and _id != _name):
                node.set("id", _name)
            if _name is None:
                node.set("name", _id)
            href = node.attrib.get("href")
            if href:
                if href[0] == "#":
                    a = etree.Element("a")
                    a.set("name", node.attrib.get("name"))
                    a.set("id", node.attrib.get("id"))
                    node.addprevious(a)
                    node.attrib.pop("id")
                    node.attrib.pop("name")

        def transform(self, data):
            raw, xml = data
            _process(xml, "a[@id]", self.parser_node)
            _process(xml, "a[@name]", self.parser_node)
            return data

    class InternalLinkAsAsteriskPipe(CustomPipe):
        def parser_node(self, node):
            href = node.attrib.get("href")
            if href.startswith("#"):
                texts = get_node_text(node)
                if texts and texts[0] == "*":
                    _remove_element_or_comment(node)

        def transform(self, data):
            raw, xml = data
            _process(xml, "a[@href]", self.parser_node)
            return data

    class AnchorAndInternalLinkPipe(CustomPipe):
        """
        Identifica pelo a/@name:
        - para qual elemento, a[@name] será convertido
            (table-wrap, fig, disp-formula, fn, app)
        - para que ref-type a[@href=#name] (xref[@ref-type])
        """

        def _remove_a(self, a_name, a_href_items):
            _remove_element_or_comment(a_name, True)
            for a_href in a_href_items:
                _remove_element_or_comment(a_href, True)

        def _create_fn(self, node):
            texts = (node.tail or "").strip()
            if texts and not texts[0].isalnum():
                node.tail = ""
                label = etree.Element("label")
                label.text = texts[0]
                texts = texts[1:].strip()
                node.append(label)
            p = etree.Element("p")
            p.text = texts
            node.tail = None
            node.text = None
            node.append(p)

        def _create_corresp(self, node):
            texts = join_texts((node.tail or "").strip().split())
            node.set("fn-type", "corresp")
            node.tag = "fn"
            label = etree.Element("label")
            p = etree.Element("p")
            if ":" in texts:
                texts = texts.split(":")
            else:
                texts = "", texts
            label.text = texts[0]
            p.text = texts[1]
            if label.text:
                node.append(label)
            node.append(p)
            node.tail = None

        def _update_a_name(self, node, new_id, new_tag):
            _name = node.attrib.get("name")
            node.attrib.clear()
            node.set("id", new_id)
            if new_tag == "symbol":
                node.set("symbol", _name)
                new_tag = "fn"
            if new_tag == "fn":
                self._create_fn(node)
            if new_tag == "corresp":
                self._create_corresp(node)
            else:
                node.tag = new_tag

        def _update_a_href_items(self, a_href_items, new_id, reftype):
            for ahref in a_href_items:
                ahref.attrib.clear()
                ahref.set("ref-type", reftype)
                ahref.set("rid", new_id)
                ahref.tag = "xref"

        def transform(self, data):
            raw, xml = data
            self.super_obj.document.xmltree = xml
            for name, a_name_and_hrefs in self.super_obj.document.a_names.items():
                a_name, a_hrefs = a_name_and_hrefs
                if a_name.attrib.get("xml_new_id"):
                    new_id = a_name.attrib.get("xml_new_id")
                    new_tag = a_name.attrib.get("xml_new_tag")
                    reftype = a_name.attrib.get("xml_reftype")
                    self._update_a_name(a_name, new_id, new_tag)
                    self._update_a_href_items(a_hrefs, new_id, reftype)
                else:
                    self._remove_a(a_name, a_hrefs)

            return data

    class DocumentPipe(CustomPipe):
        def _update(self, node, elem_name, ref_type, new_id, text=None):
            node.set("xml_new_tag", elem_name)
            node.set("xml_reftype", ref_type)
            node.set("xml_new_id", new_id)
            if text:
                node.set("xml_label", text)

        def _add_node_id(self, inferer, nodes_with_id, nodes_without_id):
            _id = None
            alt_id = None
            for node in a_href_text_nodes:
                href = node.attrib.get("href")
                if href:
                    if href[0] == "#":
                        _id = href[1:]
                    else:
                        tag_reftype_id = inferer.tag_and_reftype_and_id_from_filepath(
                            href
                        )
                        if tag_reftype_id is not None:
                            alt_elem_name, alt_ref_type, alt_id = tag_reftype_id
            return _id, alt_id

        def _add_id(self, inferer, nodes_without_id, _id, tag, reftype, text):
            for node in nodes_without_id:
                alt_id = None
                if not _id:
                    href = node.attrib.get("href")
                    tag_reftype_id = inferer.tag_and_reftype_and_id_from_filepath(
                        href
                    )
                    if tag_reftype_id:
                        alt_elem_name, alt_reftype, alt_id = tag_reftype_id
                if _id or alt_id:
                    new_id = gera_id(_id or alt_id, self.super_obj.index_body)
                    self._update(node, tag, reftype, new_id, text)

        def _complete_a_href_from_text(self, inferer, texts):
            for text, data in texts.items():
                nodes_with_id, nodes_without_id = data
                tag_reftype = inferer.tag_and_reftype_from_a_href_text(text)
                if tag_reftype:
                    tag, reftype = tag_reftype
                    _id = None
                    for node in nodes_with_id:
                        _id = node.attrib.get("href")[1:]
                        new_id = gera_id(_id, self.super_obj.index_body)
                        self._update(node, tag, reftype, new_id, text)
                    self._add_id(
                        inferer, nodes_without_id, _id, tag, reftype, text)
                else:
                    if not text.isalnum():
                        for node in nodes_with_id:
                            _remove_element_or_comment(node)

        def _complete_a_href_from_file_paths(self, inferer, file_paths):
            for path, nodes in file_paths.items():
                new_id = None
                missing = []
                for node in nodes:
                    if node.attrib.get("xml_new_id"):
                        if new_id is None:
                            elem_name = node.attrib.get("xml_new_tag")
                            ref_type = node.attrib.get("xml_reftype")
                            text = node.attrib.get("xml_label")
                            new_id = node.attrib.get("xml_new_id")
                    else:
                        missing.append(node)
                if len(missing) == 0:
                    continue
                if not new_id:
                    tag_reftype_id = inferer.tag_and_reftype_and_id_from_filepath(path)
                    if tag_reftype_id:
                        elem_name, ref_type, _id = tag_reftype_id
                        new_id = gera_id(_id, self.super_obj.index_body)
                        text = ""
                if new_id:
                    for node in missing:
                        self._update(node, elem_name, ref_type, new_id, text)

        def _complete_a_name(self, inferer, a_names):
            for name, a_name_and_hrefs in a_names.items():
                a_name, a_hrefs = a_name_and_hrefs
                new_id = None
                missing = []
                for node in a_hrefs:
                    if node.attrib.get("xml_new_id"):
                        if new_id is None:
                            elem_name = node.attrib.get("xml_new_tag")
                            ref_type = node.attrib.get("xml_reftype")
                            text = node.attrib.get("xml_label")
                            new_id = node.attrib.get("xml_new_id")
                    else:
                        missing.append(node)
                if not new_id:
                    tag_reftype = None
                    if a_name.tail:
                        tag_reftype = inferer.tag_and_reftype_from_a_href_text(
                            a_name.tail)
                    if not tag_reftype:
                        tag_reftype = inferer.tag_and_reftype_from_name(name)
                    if tag_reftype:
                        elem_name, ref_type = tag_reftype
                        new_id = gera_id(name, self.super_obj.index_body)
                        text = ""
                if new_id:
                    self._update(a_name, elem_name, ref_type, new_id, text)
                    for node in missing:
                        self._update(node, elem_name, ref_type, new_id, text)

        def _complete_img(self, inferer, images):
            for path, images in images.items():
                tag_reftype_id = inferer.tag_and_reftype_and_id_from_filepath(
                    path)
                if tag_reftype_id:
                    text = None
                    elem_name, ref_type, _id = tag_reftype_id
                    new_id = gera_id(_id, self.super_obj.index_body)
                    asset = (
                        images[0]
                        .getroottree()
                        .find(".//*[@xml_new_id='{}']".format(new_id))
                    )
                    if asset is not None:
                        text = asset.attrib.get("xml_label")
                    for node in images:
                        elem = asset
                        if elem is None:
                            elem = search_asset_node_backwards(node, "xml_new_tag")
                            if elem is not None:
                                # and elem.attrib.get("xml_new_tag") == elem_name
                                text = elem.attrib.get("xml_label")
                                new_id = elem.attrib.get("xml_new_id")
                                elem_name = elem.attrib.get("xml_new_tag")
                                ref_type = elem.attrib.get("xml_reftype")
                        if all([elem_name, ref_type, new_id]):
                            self._update(node, elem_name, ref_type, new_id, text)

        def transform(self, data):
            raw, xml = data

            self.super_obj.document.xmltree = xml
            texts, file_paths = self.super_obj.document.a_href_items
            names = self.super_obj.document.a_names
            images = self.super_obj.document.images

            with open(TEMP_FILEPATHS, "a+") as fp:
                fp.write("\n".join(file_paths.keys()))
                fp.write("\n".join(images.keys()))
            with open(TEMP_A_NAMES, "a+") as fp:
                fp.write("\n".join(names.keys()))
            with open(TEMP_A_HREF_TEXTS, "a+") as fp:
                fp.write("\n".join(texts.keys()))
            self._complete_a_name(self.super_obj.document.inferer, names)
            self._complete_a_href_from_text(
                self.super_obj.document.inferer, texts)

            self._complete_a_href_from_file_paths(
                self.super_obj.document.inferer, file_paths
            )
            self._complete_img(self.super_obj.document.inferer, images)
            return data

    class RemoveImgSetaPipe(plumber.Pipe):
        def parser_node(self, node):
            if "/seta." in node.find("img").attrib.get("src"):
                _remove_element_or_comment(node.find("img"))

        def transform(self, data):
            raw, xml = data
            _process(xml, "a[img]", self.parser_node)
            return data

    class AssetsPipe(CustomPipe):
        def transform(self, data):
            raw, xml = data

            convert = AssetsPipeline(
                self.super_obj.pid, self.super_obj.index_body, self.super_obj.document
            )
            _, obj = convert.deploy(xml)
            return raw, obj

    class RemoveThumbImgPipe(plumber.Pipe):
        def parser_node(self, node):
            path = node.attrib.get("src") or ""
            if "thumb" in path:
                parent = node.getparent()
                _remove_element_or_comment(node, True)
                if parent.tag == "a" and parent.attrib.get("href"):
                    for child in parent.getchildren():
                        _remove_element_or_comment(child, True)
                    parent.tag = "img"
                    parent.set("src", parent.attrib.pop("href"))
                    parent.text = ""

        def transform(self, data):
            raw, xml = data
            _process(xml, "img", self.parser_node)
            return data

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)


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


class AssetsPipeline(object):
    def __init__(self, pid, index_body=1, document=None):
        self.pid = pid
        self.index_body = index_body
        self.document = document or Document(None)
        self._ppl = plumber.Pipeline(
            self.SetupPipe(),
            self.AddAssetInfoToTablePipe(super_obj=self),
            self.CreateAssetElementsFromExternalLinkElementsPipe(super_obj=self),
            self.CreateAssetElementsFromImgOrTableElementsPipe(super_obj=self),
        )

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            new_obj = deepcopy(data)
            return data, new_obj

    class AddAssetInfoToTablePipe(CustomPipe):
        def parser_node(self, node):
            _id = node.attrib.get("id")
            if _id:
                new_id = gera_id(_id, self.super_obj.index_body)
                node.set("id", new_id)
                node.set("xml_new_id", new_id)
                node.set("xml_new_tag", "table-wrap")
                node.set("xml_label", "Tab")

        def transform(self, data):
            raw, xml = data
            _process(xml, "table[@id]", self.parser_node)
            return data

    class CreateAssetElementsFromExternalLinkElementsPipe(CustomPipe):

        def _create_asset_content(self, node_a):
            href = node_a.attrib.get("href")
            fname, ext = os.path.splitext(href.lower())

            if ext in [".htm", ".html"]:
                parts = href.split("/")
                local = "/".join(parts[-4:])
                remote = config.get("STATIC_URL_FILE") + href[1:]
                local = os.path.join(config.get("SITE_SPS_PKG_PATH"), local)
                asset_in_html_page = AssetInHTMLPage(local, remote)
                tree = asset_in_html_page.convert(self.super_obj)
                if tree:
                    tree.tag = "REMOVE_TAG"
                    return tree
                return

            new_graphic = etree.Element("graphic")
            new_graphic.set(
                "{http://www.w3.org/1999/xlink}href", href
            )
            return new_graphic

        def _create_asset_group(self, a_href):
            root = a_href.getroottree()
            asf_id = a_href.attrib.get("xml_new_id")
            elem_name = a_href.attrib.get("xml_new_tag")
            if not elem_name or not asf_id:
                return
            asset = find_or_create_asset_node(root, elem_name, asf_id)

            if asset is not None:
                content = self._create_asset_content(a_href)
                asset.append(content)
                if content.tag == "REMOVE_TAG":
                    _remove_element_or_comment(content, False)

                if asset.getparent() is None:
                    new_p = etree.Element("p")
                    new_p.append(asset)
                    parent = a_href.getparent()
                    parent.addnext(new_p)

                self._create_xref(a_href)

        def _create_xref(self, a_href):
            reftype = a_href.attrib.pop("xml_reftype")
            asf_id = a_href.attrib.pop("xml_new_id")

            if asf_id is None or reftype is None:
                return

            a_href.tag = "xref"
            a_href.attrib.clear()
            a_href.set("rid", asf_id)
            a_href.set("ref-type", reftype)

        def transform(self, data):
            raw, xml = data
            self.super_obj.document.xmltree = xml
            a_href_texts, file_paths = self.super_obj.document.a_href_items
            for path, nodes in file_paths.items():
                if nodes[0].attrib.get("xml_new_tag"):
                    self._create_asset_group(nodes[0])
                    for node in nodes[1:]:
                        self._create_xref(node)
            return data

    class CreateAssetElementsFromImgOrTableElementsPipe(CustomPipe):
        def _find_label_and_caption_in_node(self, node, previous_or_next):
            node_text = node.attrib.get("xml_label")
            if node_text is None:
                return

            text = get_node_text(previous_or_next)
            if text.lower().startswith(node_text.lower()):
                _node = previous_or_next
                parts = text.split()
                if len(parts) > 0:
                    if len(parts) == 1:
                        text = parts[0], ""
                    elif parts[1].isalnum():
                        text = parts[:2], parts[2:]
                    elif parts[1][:-1].isalnum():
                        text = (parts[0], parts[1][:-1]), parts[2:]
                    else:
                        text = parts[:1], parts[1:]
                    if len(text) == 2:
                        label = etree.Element("label")
                        label.text = join_texts(text[0])
                        title_text = join_texts(text[1])
                        caption = None

                        if title_text:
                            caption = etree.Element("caption")
                            title = etree.Element("title")
                            title.text = join_texts(text[1])
                            caption.append(title)
                        return _node, label, caption

        def _find_label_and_caption_around_node(self, node):
            parent = node.getparent()
            _node = None
            label = None
            caption = None
            node_label_caption = None

            previous = parent.getprevious()
            _next = parent.getnext()

            if previous is not None:
                node_label_caption = self._find_label_and_caption_in_node(
                    node, previous
                )

            if node_label_caption is None and _next is not None:
                node_label_caption = self._find_label_and_caption_in_node(node, _next)

            if node_label_caption is not None:
                _node, label, caption = node_label_caption
                if _node.getparent() is not None:
                    _node.getparent().remove(_node)
                return label, caption

        def _get_asset_node(self, img_or_table, xml_new_tag, xml_new_id):
            asset = find_or_create_asset_node(
                img_or_table.getroottree(), xml_new_tag, xml_new_id, img_or_table
            )
            if asset is not None:
                if asset.getparent() is None:
                    img_or_table.getparent().addprevious(asset)
            return asset

        def parser_node(self, img_or_table):
            xml_new_id = img_or_table.attrib.get("xml_new_id")
            xml_reftype = img_or_table.attrib.get("xml_reftype")
            xml_new_tag = img_or_table.attrib.get("xml_new_tag")
            xml_label = img_or_table.attrib.get("xml_label")
            if not xml_new_tag or not xml_new_id:
                return
            img_or_table_parent = img_or_table.getparent()
            label_and_caption = self._find_label_and_caption_around_node(img_or_table)
            asset = self._get_asset_node(img_or_table, xml_new_tag, xml_new_id)
            if label_and_caption:
                if label_and_caption[1] is not None:
                    asset.insert(0, label_and_caption[1])
                asset.insert(0, label_and_caption[0])
            new_img_or_table = deepcopy(img_or_table)
            img_or_table_parent.remove(img_or_table)
            for attr in ["xml_new_id", "xml_reftype", "xml_label",
                         "xml_new_tag"]:
                if attr in new_img_or_table.attrib.keys():
                    new_img_or_table.attrib.pop(attr)
            asset.append(new_img_or_table)

        def transform(self, data):
            raw, xml = data
            _process(xml, "img[@xml_new_id]", self.parser_node)
            _process(xml, "table[@xml_new_id]", self.parser_node)
            return data


class HTMLPage:

    def __init__(self, local=None, remote=None, content=None, ):
        self.local = local
        self.remote = remote
        self.htmltree = content

    @property
    def htmltree(self):
        return self._htmltree

    @htmltree.setter
    def htmltree(self, value):
        self._htmltree = None
        if not value:
            xmltree = self.get_content()
            if xmltree:
                self._htmltree = etree.fromstring(xmltree)
            else:
                print(self.local, self.remote)

    @property
    def content(self):
        return etree.tostring(self.tree)

    def get_content(self):
        if self.local and os.path.isfile(self.local):
            print(self.local)
            with open(self.local, "rb") as fp:
                return fp.read()
        try:
            print(self.remote)
            with request.urlopen(self.remote, timeout=30) as fp:
                content = fp.read()
        except (error.HTTPError, error.URLError) as e:
            logger.exception(e)
        else:
            dirname = os.path.dirname(self.local)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(self.local, "wb") as fp:
                fp.write(content)
            return content


class AssetInHTMLPage(HTMLPage):

    def _convert(self, _pipeline):
        body_tree = self.htmltree.find(".//body")
        if body_tree:
            __, body_tree = _pipeline.deploy(body_tree)
            return body_tree

    @property
    def xml_tree(self):
        xml_filepath = self.local + ".xml"
        if os.path.isfile(xml_filepath):
            with open(xml_filepath, "rb") as fp:
                content = fp.read()
                if content:
                    return etree.fromstring(content)

    def convert(self, _pipeline):
        xmltree = self.xml_tree
        if not xmltree:
            xmltree = self._convert(_pipeline)
            if xmltree:
                with open(self.local + ".xml", "wb") as fp:
                    fp.write(etree.tostring(xmltree))
        return xmltree
