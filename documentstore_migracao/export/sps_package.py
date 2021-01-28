import os
import itertools
import logging
import json
from typing import Tuple

from copy import deepcopy
from lxml import etree

from documentstore_migracao.export import article
from documentstore_migracao.utils import files, string
from documentstore_migracao.utils import scielo_ids_generator, xml
from documentstore_migracao.utils.convert_html_body import HTML2SPSPipeline
from documentstore_migracao import exceptions


logger = logging.getLogger(__name__)


class NotAllowedtoChangeAttributeValueError(Exception):
    pass


class InvalidAttributeValueError(Exception):
    pass


class InvalidValueForOrderError(Exception):
    pass


def parse_date(_date):
    def format(value):
        if value and value.isdigit():
            return value.zfill(2)
        return value or ""

    if _date is not None:
        return tuple(
            [format(_date.findtext(item) or "") for item in ["year", "month", "day"]]
        )
    return "", "", ""


def parse_value(value):
    value = value.lower()
    if value.isdigit():
        return value.zfill(2)
    if "spe" in value:
        return "spe"
    if "sup" in value:
        return "s"
    return value


def parse_issue(issue):
    issue = " ".join([item for item in issue.split()])
    parts = issue.split()
    parts = [parse_value(item) for item in parts]
    s = "-".join(parts)
    s = s.replace("spe-", "spe")
    s = s.replace("s-", "s")
    if s.endswith("s"):
        s += "0"
    return s


def is_asset_href(href):
    return ("img/revistas" in href or href.count(".") == 1) and (
        ":" not in href
        and "@" not in href
        and not href.startswith("www")
        and not href.startswith("http")
    )


def is_valid_value_for_order(value):
    try:
        if not (0 < int(value) <= 99999):
            raise ValueError
    except (ValueError, TypeError):
        raise InvalidValueForOrderError(
            "Invalid value for 'order': %s" %
            value
        )
    else:
        return True


def is_valid_value_for_pid_v2(value):
    if len(value or "") != 23:
        raise ValueError
    return True


def is_valid_value_for_language(value):
    if len(value or "") != 2:
        raise ValueError
    return True


def is_valid_value_for_issns(issns_dict):
    """
    Expected issns_dict is a dict
    keys: 'epub' and/or 'ppub'
    values: issn (1234-5678)
    """
    try:
        if len(set(issns_dict.keys())) != len(set(issns_dict.values())):
            raise ValueError(f"{issns_dict} has duplicated keys or values")
        if not issns_dict:
            raise ValueError(f"Expected at least one item")
        if not set(issns_dict.keys()).issubset({'epub', 'ppub'}):
            raise ValueError(
                f"Expected keys: 'epub' or 'ppub'. Found: {issns_dict.keys()}")
        for v in issns_dict.values():
            if len(v) != 9 or v[4] != "-":
                raise ValueError(f"{v} is not an ISSN")
    except AttributeError:
        raise ValueError(f"Expected dict. {issns_dict} is not dict")


VALIDATE_FUNCTIONS = dict((
    ("article_id_which_id_type_is_other", is_valid_value_for_order),
    ("scielo_pid_v2", is_valid_value_for_pid_v2),
    ("aop_pid", is_valid_value_for_pid_v2),
    ("original_language", is_valid_value_for_language),
    ("issns", is_valid_value_for_issns),
))


class SPS_Package:
    def __init__(self, xmltree, _original_asset_name_prefix=None):
        self.xmltree = xmltree
        self._original_asset_name_prefix = _original_asset_name_prefix

    @property
    def article_meta(self):
        return self.xmltree.find(".//article-meta")

    @property
    def xmltree(self):
        return self._xmltree

    @xmltree.setter
    def xmltree(self, value):
        try:
            etree.tostring(value, encoding="utf-8")
        except (TypeError, etree.SerialisationError):
            raise
        else:
            self._xmltree = value

    @property
    def issn(self):
        return (
            self.xmltree.findtext('.//issn[@pub-type="epub"]')
            or self.xmltree.findtext('.//issn[@pub-type="ppub"]')
            or self.xmltree.findtext(".//issn")
        )

    @property
    def acron(self):
        return self.xmltree.findtext('.//journal-id[@journal-id-type="publisher-id"]') or ""

    @property
    def publisher_id(self):
        try:
            return self.xmltree.xpath(
                './/article-id[not(@specific-use="scielo") and @pub-id-type="publisher-id"]/text()'
            )[0]
        except IndexError:
            return None

    def _get_scielo_pid(self, specific_use):
        try:
            return self.xmltree.xpath(
                f'.//article-id[@specific-use="{specific_use}"]/text()'
            )[0]
        except IndexError:
            return None

    def _set_scielo_pid(self, attr_value, specific_use, value):
        if attr_value is None:
            pid_node = etree.Element("article-id")
            pid_node.set("pub-id-type", "publisher-id")
            pid_node.set("specific-use", specific_use)
            pid_node.text = value
            self.article_meta.insert(0, pid_node)
        else:
            pid_node = self.article_meta.xpath(
                f'.//article-id[@specific-use="{specific_use}"]'
            )[0]
            pid_node.text = value

    @property
    def scielo_pid_v1(self):
        return self._get_scielo_pid("scielo-v1")

    @scielo_pid_v1.setter
    def scielo_pid_v1(self, value):
        self._set_scielo_pid(self.scielo_pid_v1, "scielo-v1", value)

    @property
    def scielo_pid_v2(self):
        return self._get_scielo_pid("scielo-v2")

    @scielo_pid_v2.setter
    def scielo_pid_v2(self, value):
        if not self._is_allowed_to_update("scielo_pid_v2", value):
            return
        self._set_scielo_pid(self.scielo_pid_v2, "scielo-v2", value)

    @property
    def scielo_pid_v3(self):
        return self._get_scielo_pid("scielo-v3")

    @scielo_pid_v3.setter
    def scielo_pid_v3(self, value):
        self._set_scielo_pid(self.scielo_pid_v3, "scielo-v3", value)

    @property
    def aop_pid(self):
        try:
            return self.xmltree.xpath(
                './/article-id[@specific-use="previous-pid" and @pub-id-type="publisher-id"]/text()'
            )[0]
        except IndexError:
            return None

    @aop_pid.setter
    def aop_pid(self, value):
        if not self._is_allowed_to_update("aop_pid", value):
            return
        if self.aop_pid is None:
            pid_node = etree.Element("article-id")
            pid_node.set("pub-id-type", "publisher-id")
            pid_node.set("specific-use", "previous-pid")
            pid_node.text = value
            self.article_meta.insert(1, pid_node)
        else:
            pid_node = self.article_meta.xpath(
                './/article-id[@specific-use="previous-pid" and @pub-id-type="publisher-id"]'
            )[0]
            pid_node.text = value

    @property
    def issns(self):
        try:
            return {
                issn.get("pub-type"): issn.text
                for issn in self.xmltree.xpath('.//journal-meta//issn')
            } or None
        except (TypeError, AttributeError):
            return None

    @property
    def journal_meta(self):
        data = []
        issns = [
            self.xmltree.findtext('.//issn[@pub-type="epub"]'),
            self.xmltree.findtext('.//issn[@pub-type="ppub"]'),
            self.xmltree.findtext(".//issn"),
        ]
        for issn_type, issn in zip(["eissn", "pissn", "issn"], issns):
            if issn:
                data.append((issn_type, issn))
        if self.acron:
            data.append(("acron", self.acron))
        return data

    @property
    def document_bundle_pub_year(self):
        if self.article_meta is not None:
            xpaths = (
                'pub-date[@pub-type="collection"]',
                'pub-date[@date-type="collection"]',
                'pub-date[@pub-type="epub-pub"]',
                'pub-date[@pub-type="epub"]',
            )
            for xpath in xpaths:
                pubdate = self.article_meta.find(xpath)
                if pubdate is not None and pubdate.findtext("year"):
                    return pubdate.findtext("year")

    @property
    def parse_article_meta(self):
        elements = [
            "volume",
            "issue",
            "fpage",
            "lpage",
            "elocation-id",
            "pub-date",
            "article-id",
        ]
        items = []
        for elem_name in elements:
            xpath = ".//article-meta/{}".format(elem_name)
            for node in self.xmltree.findall(xpath):
                if node is not None:
                    content = node.text
                    if node.tag == "article-id":
                        elem_name = node.get("pub-id-type")
                        if elem_name == "doi":
                            if "/" in content:
                                content = content[content.find("/") + 1 :]
                    if node.tag == "issue":
                        content = parse_issue(content)
                    elif node.tag == "pub-date":
                        content = self.document_bundle_pub_year
                        elem_name = "year"
                    if content and content.isdigit() and int(content) == 0:
                        content = ""
                    if content:
                        items.append((elem_name, content))
        return items

    @property
    def package_name(self):
        if self._original_asset_name_prefix is None:
            raise ValueError(
                "SPS_Package._original_asset_name_prefix has an invalid value."
            )
        data = dict(self.parse_article_meta)
        data_labels = data.keys()
        labels = ["volume", "issue", "fpage", "lpage", "elocation-id"]
        if "volume" not in data_labels and "issue" not in data_labels:
            if "doi" in data_labels:
                data.update({"type": "ahead"})
                labels.append("type")
                labels.append("year")
                labels.append("doi")
            elif "other" in data_labels:
                data.update({"type": "ahead"})
                labels.append("type")
                labels.append("year")
                labels.append("other")
        elif (
            "fpage" not in data_labels
            and "lpage" not in data_labels
            and "elocation-id" not in data_labels
            and "doi" not in data_labels
        ):
            labels.append("other")
        items = [self.issn, self.acron]
        items += [data[k] for k in labels if k in data_labels]
        return (
            "-".join([item for item in items if item])
            or self._original_asset_name_prefix
        )

    def asset_name(self, img_filename):
        if self._original_asset_name_prefix is None:
            raise ValueError(
                "SPS_Package._original_asset_name_prefix has an invalid value."
            )
        filename, ext = os.path.splitext(self._original_asset_name_prefix)
        suffix = img_filename
        if img_filename.startswith(filename):
            suffix = img_filename[len(filename) :]
        return "-g".join([self.package_name, suffix])

    @property
    def assets(self):
        xpaths = (
            './/graphic[@xlink:href]',
            './/media[@xlink:href]',
            './/inline-graphic[@xlink:href]',
            './/supplementary-material[@xlink:href]',
            './/inline-supplementary-material[@xlink:href]',
        )
        iterators = [
            self.xmltree.iterfind(
                xpath, namespaces={'xlink': 'http://www.w3.org/1999/xlink'}
            )
            for xpath in xpaths
        ]
        items = []
        for node in itertools.chain(*iterators):
            href = node.get("{http://www.w3.org/1999/xlink}href")
            if ":" not in href and "/" not in href:
                name, ext = os.path.splitext(href)
                items.append(href)
        return items

    @property
    def elements_which_has_xlink_href(self):
        paths = [
            ".//ext-link[@xlink:href]",
            ".//graphic[@xlink:href]",
            ".//inline-graphic[@xlink:href]",
            ".//inline-supplementary-material[@xlink:href]",
            ".//media[@xlink:href]",
            ".//supplementary-material[@xlink:href]",
        ]
        iterators = [
            self.xmltree.iterfind(
                path, namespaces={"xlink": "http://www.w3.org/1999/xlink"}
            )
            for path in paths
        ]
        return itertools.chain(*iterators)

    def replace_assets_names(self):
        replacements = []
        attr_name = "{http://www.w3.org/1999/xlink}href"
        for node in self.elements_which_has_xlink_href:
            old_path = node.get(attr_name)
            if is_asset_href(old_path):
                f_name, ext = files.extract_filename_ext_by_path(old_path)
                new_fname = self.asset_name(f_name)
                node.set(attr_name, "%s%s" % (new_fname, ext))
                replacements.append((old_path, new_fname))
        return replacements

    def get_renditions_metadata(self):
        renditions = []
        metadata = {}
        if self.article_meta is not None:
            for node in self.article_meta.findall(".//self-uri"):
                url = node.get("{http://www.w3.org/1999/xlink}href")
                lang = node.get("{http://www.w3.org/XML/1998/namespace}lang")
                filename, ext = files.extract_filename_ext_by_path(url)
                renditions.append((url, filename))
                metadata[lang] = url
        return renditions, metadata

    @property
    def volume(self):
        return dict(self.parse_article_meta).get("volume")

    @property
    def number(self):
        if self.article_meta is not None:
            issue_tag = self.article_meta.find("./issue")
            if issue_tag is not None:
                issue_tag_text = issue_tag.text.strip()
                lower_value = issue_tag_text.lower()
                if "sup" in lower_value:
                    index = lower_value.find("sup")
                    if index == 0:  # starts with "s"
                        return None
                    issue_tag_text = issue_tag_text[:index].strip()
                return "".join(issue_tag_text.split())

    @property
    def supplement(self):
        if self.article_meta is not None:
            issue_tag = self.article_meta.find("./issue")
            if issue_tag is not None:
                issue_tag_text = issue_tag.text.strip()
                lower_value = issue_tag_text.lower()
                if "sup" in lower_value:
                    issue_words = lower_value.split()
                    if "sup" in issue_words[-1]:    # suppl "0"
                        return "0"
                    return issue_tag_text.split()[-1]

    @property
    def year(self):
        return self.documents_bundle_pubdate[0]

    @property
    def fpage(self):
        try:
            return self.article_meta.findtext("fpage")
        except AttributeError:
            return None

    @property
    def documents_bundle_id(self):
        items = []
        data = dict(self.journal_meta)
        for label in ["eissn", "pissn", "issn"]:
            if data.get(label):
                items = [data.get(label)]
                break

        items.append(data.get("acron"))

        data = dict(self.parse_article_meta)
        if not data.get("volume") and not data.get("issue"):
            items.append("aop")
        else:
            labels = ("year", "volume", "issue")
            items.extend([data[k] for k in labels if data.get(k)])
        return "-".join(items)

    @property
    def is_only_online_publication(self):
        fpage = self.article_meta.findtext("fpage")
        if fpage and fpage.isdigit():
            fpage = int(fpage)
        if fpage:
            return False

        lpage = self.article_meta.findtext("lpage")
        if lpage and lpage.isdigit():
            lpage = int(lpage)
        if lpage:
            return False

        volume = self.article_meta.findtext("volume")
        issue = self.article_meta.findtext("issue")
        if volume or issue:
            return bool(self.article_meta.findtext("elocation-id"))

        return True

    @property
    def order(self):
        for item in (
                len(self.scielo_pid_v2 or "") == 23 and self.scielo_pid_v2[-5:],
                self.article_id_which_id_type_is_other,
                self.fpage,
                ):
            try:
                if is_valid_value_for_order(item):
                    return item.zfill(5)
            except InvalidValueForOrderError:
                continue

    @property
    def article_id_which_id_type_is_other(self):
        try:
            return self.article_meta.xpath(
                "article-id[@pub-id-type='other']")[0].text
        except (AttributeError, IndexError):
            return None

    @article_id_which_id_type_is_other.setter
    def article_id_which_id_type_is_other(self, value):
        if not self._is_allowed_to_update(
                "article_id_which_id_type_is_other", value):
            return
        value = value.zfill(5)
        node = self.article_meta.find(
            './/article-id[@publisher-id="other"]'
        )
        if node is None:
            node = etree.Element("article-id")
            node.set("pub-id-type", "other")
            node.text = value
            self.article_meta.insert(0, node)
        else:
            node.text = value

    @property
    def is_ahead_of_print(self):
        if not bool(self.volume) and not bool(self.number):
            return True
        return False

    def _match_pubdate(self, pubdate_xpaths):
        """
        Retorna o primeiro match da lista de pubdate_xpaths
        """
        for xpath in pubdate_xpaths:
            pubdate = self.article_meta.find(xpath)
            if pubdate is not None:
                return pubdate

    def _set_pub_date(self, attrs_by_version: tuple, value: tuple) -> None:
        sps_version = self.xmltree.xpath('/article/@specific-use')
        if len(sps_version) > 0 and attrs_by_version.get(sps_version[0]) is not None:
            attrs = attrs_by_version[sps_version[0]]
        else:
            attrs = attrs_by_version["other"]
        pubdate_node = etree.Element("pub-date")
        for attr in attrs:
            pubdate_node.set(*attr)
        for tag, val in zip(["day", "month", "year"], value[::-1]):
            if len(val) > 0:
                new_node = etree.Element(tag)
                new_node.text = val
                pubdate_node.append(new_node)

        attr_query = " and ".join(
            [f"@{k}='{v}'" for k, v in attrs]
        )  # -> "@pub-type='epub' and @attr='value'"
        already_existing_nodes = self.article_meta.xpath(f"pub-date[{attr_query}]")

        if len(already_existing_nodes) == 0:
            self.article_meta.append(pubdate_node)
            return None

        for pubdate_element in already_existing_nodes:
            parent = pubdate_element.getparent()
            index = parent.index(pubdate_element)
            parent.insert(index, pubdate_node)
            parent.remove(pubdate_element)


    @property
    def document_pubdate(self) -> Tuple[str, str, str]:
        xpaths = (
            'pub-date[@pub-type="epub"]',
            'pub-date[@date-type="pub"]',
            'pub-date',
        )
        pub_date = self._match_pubdate(xpaths)
        pub_date_or_empty = ("", "", "")

        if pub_date is not None and not (
            pub_date.get("date-type", pub_date.get("pub-type")) == "collection"
        ):
            pub_date_or_empty = parse_date(pub_date)

        return pub_date_or_empty

    @document_pubdate.setter
    def document_pubdate(self, value):
        xpaths_attrs_to_set = {
            "sps-1.9": (("publication-format", "electronic"), ("date-type", "pub"),),
            "sps-1.8": (("pub-type", "epub"),),
            "other": (("pub-type", "epub"),),
        }
        self._set_pub_date(xpaths_attrs_to_set, value)

    @property
    def documents_bundle_pubdate(self):
        xpaths = (
            'pub-date[@pub-type="epub-ppub"]',
            'pub-date[@pub-type="collection"]',
            'pub-date[@date-type="collection"]',
        )
        return parse_date(self._match_pubdate(xpaths))

    @documents_bundle_pubdate.setter
    def documents_bundle_pubdate(self, value):
        if value is None:
            xpaths = (
                'pub-date[@pub-type="epub-ppub"]',
                'pub-date[@pub-type="collection"]',
                'pub-date[@date-type="collection"]',
            )
            pubdate_node = self._match_pubdate(xpaths)
            self.article_meta.remove(pubdate_node)
        else:
            xpaths_attrs_to_set = {
                "sps-1.9": (
                    ("publication-format", "electronic"), ("date-type", "collection"),),
                "sps-1.8": (("pub-type", "collection"),),
                "other": (("pub-type", "epub-ppub"),),
            }
            self._set_pub_date(xpaths_attrs_to_set, value)

    def complete_pub_date(self, document_pubdate, issue_pubdate):
        # Verificar data de publicação e da coleção
        if len("".join(self.document_pubdate)) == 0 and document_pubdate is not None:
            logger.debug(
                'Updating document with document pub date "%s"', document_pubdate,
            )
            self.document_pubdate = document_pubdate

        if self.is_ahead_of_print:
            if len("".join(self.documents_bundle_pubdate)) > 0:
                logger.debug("Removing collection date from ahead of print document")
                self.documents_bundle_pubdate = None
        else:
            if (
                len("".join(self.documents_bundle_pubdate)) == 0
                and issue_pubdate is not None
            ):
                logger.debug(
                    'Updating document with collection date "%s"', issue_pubdate
                )
                self.documents_bundle_pubdate = issue_pubdate

    @property
    def languages(self):
        """The language of the main document plus all translations.
        """
        return self.xmltree.xpath(
            '/article/@xml:lang | //sub-article[@article-type="translation"]/@xml:lang'
        )

    @property
    def original_language(self):
        """The language of the main document."""
        article_tag = self.xmltree.xpath('/article[@xml:lang]')
        if article_tag:
            return article_tag[0].attrib["{http://www.w3.org/XML/1998/namespace}lang"]

    @original_language.setter
    def original_language(self, value):
        """Set language of the main document."""
        if not self._is_allowed_to_update("original_language", value):
            return
        article_tag = self.xmltree.xpath('/article')
        if article_tag:
            article_tag[0].set("{http://www.w3.org/XML/1998/namespace}lang", value)

    @property
    def media_prefix(self):

        if not self.scielo_pid_v3:
            raise exceptions.XMLError("Não existe scielo-pid-v3")

        return f"{self.issn}/{self.scielo_pid_v3}"

    def _get_ref_items(self, body):
        ref_items = []
        back = body.getnext()
        if back is not None:
            ref_items = back.findall(".//ref")
        if not ref_items:
            ref_items = body.getroottree().findall(".//ref")
        return ref_items

    def transform_body(self, spy=False):

        for index, body in enumerate(self.xmltree.xpath("//body"), start=1):
            logger.debug("Processando body numero: %s" % index)

            txt_body = body.findtext("./p") or ""
            convert = HTML2SPSPipeline(
                pid=self.scielo_pid_v2,
                ref_items=self._get_ref_items(body),
                body_index=index,
                spy=spy,
            )
            _, obj_html_body = convert.deploy(txt_body)

            # sobrecreve o html escapado anterior pelo novo xml tratado
            if obj_html_body.tag != "body":
                obj_html_body = obj_html_body.find("body")
            if obj_html_body is None:
                raise TypeError("XML: %s esta sem Body" % (self.scielo_pid_v2))

            body.getparent().replace(body, obj_html_body)

        return self.xmltree

    def _move_appendix_from_body_to_back(self):
        for body in self.xmltree.iterfind(".//body"):
            app_group_tags = body.findall(".//app-group")
            if len(app_group_tags) > 0:
                back = body.getparent().find("./back")
                if back is None:
                    body.getparent().append(etree.Element("back"))
                    back = body.getparent().find("./back")
                for app_group_tag in app_group_tags:
                    back.append(app_group_tag)

    def transform_content(self):
        # CONVERTE PUB-DATE PARA SPS 1.9
        self.transform_pubdate()

        # OUTROS AJUSTES NO XML PARA SPS 1.9
        self._move_appendix_from_body_to_back()

    def transform_article_meta_count(self):
        count_tree = self.xmltree.find(".//counts")
        if count_tree is not None:
            count_tree.getparent().remove(count_tree)

        return self.xmltree

    def create_scielo_id(self):
        PATHS = [".//article-meta"]

        def _append_node(parent, new_node):
            node = parent.findall(".//article-id")
            if node:
                parent.insert(parent.index(node[0]), new_node)
            else:
                parent.append(new_node)

        iterators = [self.xmltree.iterfind(path) for path in PATHS]
        for article in itertools.chain(*iterators):

            node = article.findall(".//article-id[@specific-use='scielo-v3']")
            if not node:
                articleId = etree.Element("article-id")
                articleId.set("pub-id-type", "publisher-id")
                articleId.set("specific-use", "scielo-v3")
                articleId.text = scielo_ids_generator.generate_scielo_pid()
                _append_node(article, articleId)

        return self.xmltree

    def transform_pubdate(self):
        xpaths_to_change = (
            ("pub-date[@pub-type='epub']", ("date-type", "pub")),
            ("pub-date[@pub-type='collection']", ("date-type", "collection")),
            ("pub-date[@pub-type='epub-ppub']", ("date-type", "collection")),
        )
        for xpath, pubdate_element_attr in xpaths_to_change:
            pubdate = self.article_meta.find(xpath)
            if pubdate is not None:
                pubdate.set(*pubdate_element_attr)
                pubdate.attrib.pop("pub-type")
        xpaths_to_update = (
            ("pub-date[@date-type='pub']"),
            ("pub-date[@date-type='collection']"),
        )
        for xpath in xpaths_to_update:
            pubdate = self.article_meta.find(xpath)
            if pubdate is not None:
                pubdate.set("publication-format", "electronic")

    def update_mixed_citations(self, references: dict, override=False) -> list:
        """Atualiza a tag `mixed-citation` nas referências do artigo. Também cria
        a tag `label` com a ordem/índice da referência.

        Params:
            references (dict): Dicionário com as referências de um artigo. O
                formato esperado é: {"order": "reference-text"}.
            override (bool): Força a atualização do mixed-citation para
                referências que já possuam o elemento.

        Returns:
            None
        """

        updated = []

        for order, reference in enumerate(
            self.xmltree.findall(".//back/ref-list/ref"), start=1
        ):
            reference_text = references.get(str(order))

            if reference_text is None:
                continue
            elif not override and reference.find(".//mixed-citation") is not None:
                continue

            try:
                new_mixed_citation = xml.create_mixed_citation_element(reference_text)
            except AssertionError:
                continue

            xml.remove_element(reference, ".//mixed-citation")
            reference.insert(0, new_mixed_citation)

            extracted_order = xml.extract_reference_order(text=reference_text)

            if extracted_order == str(order):
                xml.remove_element(reference, ".//label")
                reference_label = etree.Element("label")
                reference_label.text = extracted_order
                reference.insert(0, reference_label)

            updated.append(references.get(str(order)))

        return updated

    def fix(self, attr_name, attr_new_value, silently=False):
        """
        Conserta valor de atributo e silencia as exceções
        """
        try:
            setattr(self, attr_name, attr_new_value)
        except (NotAllowedtoChangeAttributeValueError,
                InvalidAttributeValueError) as exc:
            if silently:
                logging.debug("%s", str(exc))
            else:
                raise

    def _is_allowed_to_update(self, attr_name, attr_new_value):
        """
        Se há uma função de validação associada com o atributo,
        verificar se é permitido atualizar o atributo, dados seus valores
        atual e/ou novo
        """
        validate_function = VALIDATE_FUNCTIONS.get(attr_name)
        if validate_function is None:
            # não há nenhuma validação, então é permitido fazer a atualização
            return True

        curr_value = getattr(self, attr_name)

        if attr_new_value == curr_value:
            # desnecessario atualizar
            return False

        try:
            # valida o valor atual do atributo
            validate_function(curr_value)
        except (ValueError, InvalidValueForOrderError):
            # o valor atual do atributo é inválido,
            # então continuar para verificar o valor "novo"
            pass
        else:
            # o valor atual do atributo é válido,
            # então não permitir atualização
            raise NotAllowedtoChangeAttributeValueError(
                "Not allowed to update %s (%s) with %s, "
                "because current is valid" %
                (attr_name, curr_value, attr_new_value))
        try:
            # valida o valor novo para o atributo
            validate_function(attr_new_value)
        except (ValueError, InvalidValueForOrderError):
            # o valor novo é inválido, então não permitir atualização
            raise InvalidAttributeValueError(
                "Not allowed to update %s (%s) with %s, "
                "because new value is invalid" %
                (attr_name, curr_value, attr_new_value))
        else:
            # o valor novo é válido, então não permitir atualização
            return True


class DocumentsSorter:
    def __init__(self):
        self._documents_bundles = {}
        self._reverse = {}

    @property
    def reverse(self):
        return self._reverse

    @property
    def documents_bundles(self):
        return self._documents_bundles

    def insert_document(self, document_id, document_xml):
        pkg = SPS_Package(document_xml, "none")

        data = dict(pkg.parse_article_meta)
        self._documents_bundles[document_id] = {
            "eissn": dict(pkg.journal_meta).get("eissn"),
            "pissn": dict(pkg.journal_meta).get("pissn"),
            "issn": dict(pkg.journal_meta).get("issn"),
            "acron": dict(pkg.journal_meta).get("acron"),
            "pid": pkg.publisher_id,
            "year": pkg.year,
            "volume": pkg.volume,
            "number": pkg.number,
            "supplement": pkg.supplement,
            "order": pkg.order,
        }

    def insert_documents(self, documents):
        """
        documents é uma lista de tuplas (document_id, document_xml)
        """
        for document_id, document_xml in documents:
            self.insert_document(document_id, document_xml)

    @property
    def documents_bundles_with_sorted_documents(self):
        _documents_bundles = deepcopy(self.documents_bundles)
        for dbid, docs_bundle in _documents_bundles.items():
            _documents_bundles[dbid]["items"] = [
                docs_bundle["items"][k]
                for k in sorted(docs_bundle["items"].keys(), reverse=self.reverse[dbid])
            ]
        return _documents_bundles


class SourceJson:

    def __init__(self, json_data):
        self.json_data = json.loads(json_data)

    @property
    def issue_folder(self):
        suffixes = [
            ("v", "v31"),
            ("s", "v131"),
            ("n", "v32"),
            ("s", "v132"),
        ]
        label_parts = []
        article = self.json_data["article"]
        for suffix, field in suffixes:
            value = article.get(field)
            if value:
                label_parts.append(suffix + value[0]["_"])
        return "".join(label_parts)

    @property
    def renditions_metadata(self):
        try:
            return self.json_data["fulltexts"]["pdf"]
        except KeyError:
            return {}

    @property
    def fixed_renditions_metadata(self):
        fixed = {}
        for lang, path in self.renditions_metadata.items():

            expected_issue_folder = "/{}/".format(self.issue_folder)
            if expected_issue_folder in path:
                return self.renditions_metadata

            wrong_folder = expected_issue_folder.lower()
            if wrong_folder in path:
                fixed[lang] = path.replace(wrong_folder, expected_issue_folder)
        return fixed

    def get_renditions_metadata(self):
        renditions = []
        for lang, url in self.fixed_renditions_metadata.items():
            filename, ext = files.extract_filename_ext_by_path(url)
            renditions.append((url, filename))
        return renditions, self.fixed_renditions_metadata
