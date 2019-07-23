# code=utf-8

import os
import unittest
from lxml import etree
from documentstore_migracao.utils.xml import objXML2file

from documentstore_migracao.utils.convert_html_body_inferer import Inferer
from documentstore_migracao.utils.convert_html_body import (
    HTML2SPSPipeline,
    ConvertElementsWhichHaveIdPipeline,
    Document,
    _process,
    _remove_element_or_comment,
    search_asset_node_backwards,
)
from . import SAMPLES_PATH


class TestConvertHMTLBodySearchAssetNodeBackwards(unittest.TestCase):
    def test_search_asset_node_backwards_returns_a_node(self):
        text = """<root>
            <p><table-wrap id="t01"></table-wrap></p>
            <p><current/></p></root>"""
        xmltree = etree.fromstring(text)
        result = search_asset_node_backwards(xmltree.find(".//current"))
        self.assertEqual(result.tag, "table-wrap")

    def test_search_asset_node_backwards_returns_None(self):
        text = """<root>
            <p><table-wrap id="t01"><current/></table-wrap></p>
            <p><current/></p></root>"""
        xmltree = etree.fromstring(text)
        result = search_asset_node_backwards(xmltree.find(".//current"))
        self.assertIsNone(result)


class TestDocumentPipe(unittest.TestCase):
    def setUp(self):
        pipeline = HTML2SPSPipeline("PID")
        self.pipe = pipeline.DocumentPipe(pipeline)
        self.inferer = Inferer()
        self.text = """
        <root>
            <a href="#tab01">Tabela 1</a>
            <a href="#tab01">Tabela 1</a>
            <a name="tab01"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg">Figure 1</a>

            <a href="f02.jpg">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg">Figure 3</a>
            <a href="f03.jpg">3</a>
        </root>
        """
        self.xml = etree.fromstring(self.text)
        self.document = Document(self.xml)
        self.texts, self.files = self.document.a_href_items

    def test_identify_data(self):

        nodes = self.xml.findall("./a")
        img = self.xml.findall(".//img")
        self.assertEqual(
            self.document.a_names, {"tab01": (nodes[2], [nodes[0], nodes[1]])}
        )
        self.assertEqual(
            self.texts,
            {
                "tabela 1": ([nodes[0], nodes[1]], []),
                "figure 1": ([], [nodes[3]]),
                "2": ([], [nodes[4]]),
                "figure 3": ([], [nodes[5]]),
                "3": ([], [nodes[6]]),
            },
        )
        self.assertEqual(
            self.files,
            {"f01": [nodes[3]], "f02": [nodes[4]], "f03": [nodes[5], nodes[6]]},
        )
        self.assertEqual(self.document.images, {"app": [img[1]], "tabela": [img[0]]})

    def _assert(self, expected, step, xpath=".//a"):
        expected_node = etree.fromstring(expected).findall(xpath)
        for i, node in enumerate(self.xml.findall(xpath)):
            with self.subTest(step + " " + str(i)):
                self.assertEqual(etree.tostring(node), etree.tostring(expected_node[i]))

    def test_add_xml_attribs(self):
        expected = """
        <root>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a name="tab01"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f01" xml_label="figure 1">Figure 1</a>

            <a href="f02.jpg">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">Figure 3</a>
            <a href="f03.jpg">3</a>
        </root>
        """
        self.pipe._add_xml_attribs_to_a_href_from_text(self.texts)
        self._assert(expected, "a_href_from_text")

        expected = """
        <root>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a name="tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f01" xml_label="figure 1">Figure 1</a>

            <a href="f02.jpg">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">Figure 3</a>
            <a href="f03.jpg">3</a>
        </root>
        """
        self.pipe._add_xml_attribs_to_a_name(self.document.a_names)
        self._assert(expected, "a_names")

        expected = """
        <root>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a name="tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f01" xml_label="figure 1">Figure 1</a>

            <a href="f02.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f02">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">Figure 3</a>
            <a href="f03.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">3</a>
        </root>
        """
        self.pipe._add_xml_attribs_to_a_href_from_file_paths(self.files)
        self._assert(expected, "file_paths")

        expected = """
        <root>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a href="#tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a name="tab01" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1"/>
            <img src="tabela.jpg" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1"/>

            <a href="f01.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f01" xml_label="figure 1">Figure 1</a>

            <a href="f02.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f02">2</a>

            <img src="app.jpg" xml_tag="app" xml_reftype="app" xml_id="app"/>

            <a href="f03.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">Figure 3</a>
            <a href="f03.jpg" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">3</a>
        </root>
        """
        self.pipe._add_xml_attribs_to_img(self.document.images)
        self._assert(expected, "images", ".//img")


class TestHTML2SPSPipeline(unittest.TestCase):
    def _transform(self, text, pipe):
        tree = etree.fromstring(text)
        data = text, tree
        raw, transformed = pipe.transform(data)
        self.assertEqual(raw, text)
        return raw, transformed

    def setUp(self):
        filename = os.path.join(SAMPLES_PATH, "example_convert_html.xml")
        with open(filename, "r") as f:
            self.xml_txt = f.read()
        self.etreeXML = etree.fromstring(self.xml_txt)
        self.pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")

    def test_create_instance(self):
        expected_text = "<p>La nueva epoca de la revista<italic>Salud Publica de Mexico </italic></p>"
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        raw, xml = pipeline.SetupPipe().transform(expected_text)
        self.assertIn(expected_text, str(etree.tostring(xml)))

    def test_pipe_remove_empty_do_not_remove_img(self):
        text = '<root><p> <img align="x" src="a04qdr04.gif"/> </p> </root>'
        expected = '<root><p> <img align="x" src="a04qdr04.gif"/> </p> </root>'
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_do_not_remove_a(self):
        text = '<root><p> <a align="x" src="a04qdr04.gif"/> </p> </root>'
        expected = '<root><p> <a align="x" src="a04qdr04.gif"/> </p> </root>'
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_do_not_remove_hr(self):
        text = '<root><p> <hr align="x" src="a04qdr04.gif"/> </p> </root>'
        expected = '<root><p> <hr align="x" src="a04qdr04.gif"/> </p> </root>'
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_do_not_remove_br(self):
        text = '<root><p> <br align="x" src="a04qdr04.gif"/> </p> </root>'
        expected = '<root><p> <br align="x" src="a04qdr04.gif"/> </p> </root>'
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_p(self):
        text = "<root><p>Colonização micorrízica e concentração de nutrientes em três cultivares de bananeiras em um latossolo amarelo da Amazônia central</p> <p/> </root>"
        expected = "<root><p>Colonização micorrízica e concentração de nutrientes em três cultivares de bananeiras em um latossolo amarelo da Amazônia central</p></root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_bold(self):
        text = "<root><p>Colonização micorrízica e concentração de nutrientes <bold> </bold> em três cultivares de bananeiras em um latossolo amarelo</p> </root>"
        expected = "<root><p>Colonização micorrízica e concentração de nutrientes em três cultivares de bananeiras em um latossolo amarelo</p> </root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())

        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_attribute_style(self):
        text = '<root><p style="x">texto <b style="x"></b></p> <td style="bla"><caption style="x"/></td></root>'
        raw, transformed = self._transform(
            text, self.pipeline.RemoveStyleAttributesPipe()
        )
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><p>texto <b/></p> <td style="bla"><caption style="x"/></td></root>',
        )

    def test_pipe_hr(self):
        text = '<root><hr style="x" /></root>'
        raw, transformed = self._transform(text, self.pipeline.HrPipe())
        self.assertEqual(
            etree.tostring(transformed), b'<root><p content-type="hr"/></root>'
        )

    def test_pipe__tagsh__h1(self):
        text = "<root><h1>Titulo 1</h1></root>"
        raw, transformed = self._transform(text, self.pipeline.TagsHPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><p content-type="h1">Titulo 1</p></root>',
        )

    def test_pipe__tagsh__h3(self):
        text = "<root><h3>Titulo 3</h3></root>"
        raw, transformed = self._transform(text, self.pipeline.TagsHPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><p content-type="h3">Titulo 3</p></root>',
        )

    def test_pipe_br(self):
        text = '<root><p align="x">bla<br/> continua outra linha</p><p baljlba="1"/><td><br/></td><sec><br/></sec></root>'
        raw, transformed = self._transform(text, self.pipeline.BRPipe())
        print("?", etree.tostring(transformed))
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><p align="x">bla</p><p> continua outra linha</p><p baljlba="1"/><td><break/></td><sec/></root>',
        )

    def test_pipe_p(self):
        text = '<root><p align="x" id="y">bla</p><p baljlba="1"/></root>'
        raw, transformed = self._transform(text, self.pipeline.PPipe())

        self.assertEqual(
            etree.tostring(transformed), b'<root><p id="y">bla</p><p/></root>'
        )

    def test_pipe_div(self):
        text = '<root><div align="x" id="intro">bla</div><div baljlba="1"/></root>'
        raw, transformed = self._transform(text, self.pipeline.DivPipe())

        self.assertEqual(
            etree.tostring(transformed), b'<root><p id="intro">bla</p><p/></root>'
        )

    def test_pipe_img(self):
        text = '<root><img align="x" src="a04qdr04.gif"/><img align="x" src="a04qdr08.gif"/></root>'
        raw, transformed = self._transform(
            text, self.pipeline.ImgPipe(super_obj=self.pipeline)
        )

        nodes = transformed.findall(".//graphic")

        self.assertEqual(len(nodes), 2)
        for node, href in zip(nodes, ["a04qdr04.gif", "a04qdr08.gif"]):
            with self.subTest(node=node):
                self.assertEqual(
                    href, node.attrib["{http://www.w3.org/1999/xlink}href"]
                )
                self.assertEqual(len(node.attrib), 1)

    def test_pipe_li(self):
        text = """<root>
        <li><p>Texto dentro de <b>li</b> 1</p></li>
        <li align="x" src="a04qdr08.gif"><p>Texto dentro de <b>li</b> 2</p></li>
        <li><b>Texto dentro de 3</b></li>
        <li>Texto dentro de 4</li>
        </root>"""
        expected = [
            b"<list-item><p>Texto dentro de <b>li</b> 1</p></list-item>",
            b"<list-item><p>Texto dentro de <b>li</b> 2</p></list-item>",
            b"<list-item><p><b>Texto dentro de 3</b></p></list-item>",
            b"<list-item><p>Texto dentro de 4</p></list-item>",
        ]
        raw, transformed = self._transform(text, self.pipeline.LiPipe())

        nodes = transformed.findall(".//list-item")
        self.assertEqual(len(nodes), 4)
        for node, text in zip(nodes, expected):
            with self.subTest(node=node):
                self.assertEqual(text, etree.tostring(node).strip())
                self.assertEqual(len(node.attrib), 0)

    def test_pipe_ol(self):
        text = """
            <root>
            <ol>
            <li align="x" src="a04qdr04.gif">Texto dentro de <b>li</b> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <b>li</b> 2</li>
            </ol>
            <ol>
            <li align="x" src="a04qdr04.gif">Texto dentro de <b>li</b> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <b>li</b> 2</li>
            </ol>
            </root>
        """
        raw, transformed = self._transform(text, self.pipeline.OlPipe())

        nodes = transformed.findall(".//list")
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 1)
                self.assertEqual(node.attrib["list-type"], "order")

    def test_pipe_ul(self):
        text = """
            <root>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <b>li</b> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <b>li</b> 2</li>
            </ul>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <b>li</b> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <b>li</b> 2</li>
            </ul>
            </root>
        """
        raw, transformed = self._transform(text, self.pipeline.UlPipe())

        nodes = transformed.findall(".//list")
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 1)
                self.assertEqual(node.attrib["list-type"], "bullet")

    def test_pipe_dl(self):
        text = """
            <root>
            <dl><dd>Black hot drink</dd></dl>
            <dl><dd>Milk</dd></dl>
            </root>
        """
        raw, transformed = self._transform(text, self.pipeline.DefListPipe())

        nodes = transformed.findall(".//def-list")
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)

    def test_pipe_dd(self):
        text = """
            <root>
            <dl><dd>Black hot drink</dd></dl>
            <dl><dd>Milk</dd></dl>
            </root>
        """
        raw, transformed = self._transform(text, self.pipeline.DefItemPipe())

        nodes = transformed.findall(".//def-item")
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)

    def test_pipe_i(self):
        text = """
            <root>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <i>texto 1</i> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <i>texto <b>2</b></i> 2</li>
            </ul>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <i><b>texto S</b></i> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <i><b>texto</b> G</i> 2</li>
            </ul>
            </root>
        """
        raw, transformed = self._transform(text, self.pipeline.IPipe())

        nodes = transformed.findall(".//italic")
        self.assertEqual(len(nodes), 4)
        texts = [
            b"<italic>texto 1</italic> 1",
            b"<italic>texto <b>2</b></italic> 2",
            b"<italic><b>texto S</b></italic> 1",
            b"<italic><b>texto</b> G</italic> 2",
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)
                self.assertEqual(text, etree.tostring(node))

    def test_pipe_b(self):
        text = """
            <root>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <b>texto 1</b> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <b>texto <sup>2</sup></b> 2</li>
            </ul>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <b><sup>texto S</sup></b> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <b><sup>texto</sup> G</b> 2</li>
            </ul>
            </root>
            """
        raw, transformed = self._transform(text, self.pipeline.BPipe())

        nodes = transformed.findall(".//bold")
        self.assertEqual(len(nodes), 4)
        texts = [
            b"<bold>texto 1</bold> 1",
            b"<bold>texto <sup>2</sup></bold> 2",
            b"<bold><sup>texto S</sup></bold> 1",
            b"<bold><sup>texto</sup> G</bold> 2",
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)
                self.assertEqual(text, etree.tostring(node))

    def test_pipe_u(self):
        text = """
            <root>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <u>texto 1</u> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <u>texto <sup>2</sup></u> 2</li>
            </ul>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <u><sup>texto S</sup></u> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <u><sup>texto</sup> G</u> 2</li>
            </ul>
            </root>
            """
        raw, transformed = self._transform(text, self.pipeline.UPipe())

        nodes = transformed.findall(".//underline")
        self.assertEqual(len(nodes), 4)
        texts = [
            b"<underline>texto 1</underline> 1",
            b"<underline>texto <sup>2</sup></underline> 2",
            b"<underline><sup>texto S</sup></underline> 1",
            b"<underline><sup>texto</sup> G</underline> 2",
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)
                self.assertEqual(text, etree.tostring(node))

    def test_pipe_em(self):
        text = """
            <root>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <em>texto 1</em> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <em>texto <sup>2</sup></em> 2</li>
            </ul>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <em><sup>texto S</sup></em> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <em><sup>texto</sup> G</em> 2</li>
            </ul>
            </root>
            """
        raw, transformed = self._transform(text, self.pipeline.EmPipe())

        nodes = transformed.findall(".//italic")
        self.assertEqual(len(nodes), 4)
        texts = [
            b"<italic>texto 1</italic> 1",
            b"<italic>texto <sup>2</sup></italic> 2",
            b"<italic><sup>texto S</sup></italic> 1",
            b"<italic><sup>texto</sup> G</italic> 2",
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)
                self.assertEqual(text, etree.tostring(node))

    def test_pipe_strong(self):
        text = """
            <root>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <strong>texto 1</strong> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <strong>texto <sup>2</sup></strong> 2</li>
            </ul>
            <ul>
            <li align="x" src="a04qdr04.gif">Texto dentro de <strong><sup>texto S</sup></strong> 1</li>
            <li align="x" src="a04qdr08.gif">Texto dentro de <strong><sup>texto</sup> G</strong> 2</li>
            </ul>
            </root>
            """
        raw, transformed = self._transform(text, self.pipeline.StrongPipe())

        nodes = transformed.findall(".//bold")
        self.assertEqual(len(nodes), 4)
        texts = [
            b"<bold>texto 1</bold> 1",
            b"<bold>texto <sup>2</sup></bold> 2",
            b"<bold><sup>texto S</sup></bold> 1",
            b"<bold><sup>texto</sup> G</bold> 2",
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)
                self.assertEqual(text, etree.tostring(node))

    def test_pipe_a__parser_node_external_link_for_uri(self):
        expected = {
            "{http://www.w3.org/1999/xlink}href": "http://bla.org",
            "ext-link-type": "uri",
        }
        xml = etree.fromstring('<root><a href="http://bla.org">texto</a></root>')
        node = xml.find(".//a")

        self.pipeline.APipe(super_obj=self.pipeline)._parser_node_external_link(node)

        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))
        self.assertEqual(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "http://bla.org"
        )
        self.assertEqual(node.attrib.get("ext-link-type"), "uri")
        self.assertEqual(node.tag, "ext-link")
        self.assertEqual(node.text, "texto")
        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))

    def test_pipe_a__creates_email_element_with_href_attribute(self):
        expected = """<root>
        <p><email xlink:href="mailto:a@scielo.org">Enviar e-mail para A</email></p>
        </root>"""
        text = """<root>
        <p><a href="mailto:a@scielo.org">Enviar e-mail para A</a></p>
        </root>"""
        xml = etree.fromstring(text)

        node = xml.find(".//a")
        self.pipeline.APipe(super_obj=self.pipeline)._create_email(node)

        self.assertIn(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "mailto:a@scielo.org"
        )
        self.assertEqual(node.tag, "email")
        self.assertEqual(node.text, "Enviar e-mail para A")

    def test_pipe_a__creates_email_(self):
        expected = """<root>
        <p>Enviar e-mail para <email>a@scielo.org</email>.</p>
        </root>"""
        text = """<root>
        <p><a href="mailto:a@scielo.org">Enviar e-mail para a@scielo.org.</a></p>
        </root>"""
        xml = etree.fromstring(text)

        node = xml.find(".//a")
        self.pipeline.APipe(super_obj=self.pipeline)._create_email(node)
        p = xml.find(".//p")
        self.assertEqual(p.text, "Enviar e-mail para ")
        email = p.find("email")
        self.assertEqual(email.text, "a@scielo.org")
        self.assertEqual(email.tail, ".")

    def test_pipe_a__creates_graphic_email(self):
        expected = b"""<root><p><graphic xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="email.gif"><email>mailto:x@scielo.org</email></graphic></p></root>"""
        text = """<root>
        <p><a href="mailto:x@scielo.org"><img src="mail.gif" /></a></p>
        </root>"""
        xml = etree.fromstring(text)

        node = xml.find(".//a")
        self.pipeline.APipe(super_obj=self.pipeline)._create_email(node)

        self.assertEqual(
            xml.find(".//graphic").attrib.get("{http://www.w3.org/1999/xlink}href"),
            "mail.gif",
        )
        self.assertEqual(xml.findtext(".//graphic/email"), "x@scielo.org")

    def test_pipe_a__creates_email(self):
        text = """<root>
        <p><a href="mailto:a@scielo.org">a@scielo.org</a></p>
        </root>"""
        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        node = transformed.find(".//email")
        self.assertEqual(node.text, "a@scielo.org")
        self.assertEqual(node.tag, "email")

    def test_pipe_a__create_email_mailto_empty(self):
        text = """<root><a href="mailto:">sfpyip@hku.hk</a>). Correspondence should be addressed to Dr Yip at this address.</root>"""
        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        node = transformed.find(".//email")
        self.assertEqual(node.text, "a@scielo.org")
        self.assertEqual(node.tag, "email")

    def test_pipe_a__create_email_mailto_empty(self):
        text = """<root><a href="mailto:">sfpyip@hku.hk</a>). Correspondence should be addressed to Dr Yip at this address.</root>"""
        raw, transformed = self._transform(text, self.pipeline.APipe())

        node = transformed.find(".//email")
        self.assertEqual(node.text, "sfpyip@hku.hk")
        self.assertEqual(
            node.tail,
            "). Correspondence should be addressed to Dr Yip at this address.",
        )

    def test_fix_element_a(self):
        text = """<root><a name="_ftnref19" href="#_ftn2" id="_ftnref19"><sup>1</sup></a></root>"""
        expected = b"""<root><a name="_ftnref19" id="_ftnref19"/><a href="#_ftn2"><sup>1</sup></a></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipeline.FixElementAPipe(self.pipeline).transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_asterisk_in_a_name(self):
        text = '<root><a name="*" id="*"/></root>'
        expected = b"<root/>"
        xml = etree.fromstring(text)

        text, xml = self.pipeline.AnchorAndInternalLinkPipe(
            super_obj=self.pipeline
        ).transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_asterisk_in_a_href(self):
        text = '<root><a name="1a" id="1a"/><a href="#1b"><sup>*</sup></a></root>'
        expected = b'<root><a name="1a" id="1a"/><sup>*</sup></root>'
        xml = etree.fromstring(text)

        text, xml = self.pipeline.InternalLinkAsAsteriskPipe(
            super_obj=self.pipeline
        ).transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_asterisk_in_fn(self):
        text = '<root><a name="fn1" id="fn1"/>* texto</root>'
        expected = b'<root><fn id="fn1"><label>*</label><p>texto</p></fn></root>'
        xml = etree.fromstring(text)

        text, xml = self.pipeline.DocumentPipe(super_obj=self.pipeline).transform(
            (text, xml)
        )
        text, xml = self.pipeline.AnchorAndInternalLinkPipe(
            super_obj=self.pipeline
        ).transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_aname__removes__ftn(self):
        text = """<root><a name="_ftnref19" title="" href="#_ftn2" id="_ftnref19"><sup>1</sup></a></root>"""
        raw, transformed = text, etree.fromstring(text)
        raw, transformed = self.pipeline.AnchorAndInternalLinkPipe(
            self.pipeline
        ).transform((raw, transformed))
        node = transformed.find(".//xref")
        self.assertIsNone(node)
        node = transformed.find(".//a")
        self.assertIsNone(node)
        # self.assertIsNotNone(transformed.find(".//sup"))
        self.assertEqual(etree.tostring(transformed), b"<root/>")

    def test_pipe_aname__removes_navigation_to_note_go_and_back(self):
        text = """<root><a href="#tx01">
            <graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/>
        </a><a name="tx01" id="tx01"/></root>"""

        raw, transformed = text, etree.fromstring(text)
        raw, transformed = self.pipeline.AnchorAndInternalLinkPipe(
            self.pipeline
        ).transform((raw, transformed))

        node = transformed.find(".//xref")
        self.assertIsNone(node)

        node = transformed.find(".//a")
        self.assertIsNone(node)

        self.assertIsNone(transformed.find(".//graphic"))

    def test_pipe_aname__removes_navigation_to_note_go_and_back_case2(self):
        text = """<root><a name="1not" id="1not"/>TEXTO NOTA</root>"""

        raw, transformed = text, etree.fromstring(text)

        raw, transformed = self.pipeline.DocumentPipe(self.pipeline).transform(
            (raw, transformed)
        )
        raw, transformed = self.pipeline.AnchorAndInternalLinkPipe(
            self.pipeline
        ).transform((raw, transformed))

        node_fn = transformed.find(".//fn[p]")
        self.assertIsNotNone(node_fn)
        self.assertIsNone(node_fn.tail)

        node_p = transformed.find(".//fn/p")
        self.assertIsNotNone(node_p)

        self.assertEqual(node_p.text, "TEXTO NOTA")

    def test_pipe_a_anchor__remove_xref_with_graphic(self):
        text = """<root><a href="#top"><graphic xmlns:ns2="http://www.w3.org/1999/xlink"
            ns2:href="/img/revistas/gs/v29n2/seta.gif"/></a></root>"""

        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        node = transformed.find(".//xref")
        self.assertIsNone(node)

        node = transformed.find(".//graphic")
        self.assertIsNone(node)

        self.assertEqual(etree.tostring(transformed), b"<root/>")

    def test_pipe_a_anchor__remove_xref(self):
        text = """<root>Demographic and Health Surveys. Available from: <a href="#fn1">b</a></root>"""

        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        self.assertEqual(
            etree.tostring(transformed),
            b"<root>Demographic and Health Surveys. Available from: b</root>",
        )

    def test_pipe_a_anchor__keep_xref(self):
        text = """<root><table-wrap id="tab1" xref_id="tab1"/><a href="#tab1">Tabela 1</a> Demographic and Health Surveys. Available from: </root>"""

        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        self.assertEqual(
            etree.tostring(transformed),
            b'<root><table-wrap id="tab1"/><xref rid="tab1" ref-type="table">Tabela 1</xref> Demographic and Health Surveys. Available from: </root>',
        )

    def test_pipe_a_anchor__xref_bibr_case1(self):
        text = """<root><a href="#ref">(9,10)</a>Tabela 1 </root>"""

        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        self.assertEqual(
            etree.tostring(transformed),
            b'<root><xref rid="B9" ref-type="bibr">(9,10)</xref>Tabela 1 </root>',
        )

    def test_pipe_a_anchor__xref_bibr_case2(self):
        text = """<root><a href="#ref">9</a>Tabela 1 </root>"""

        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        self.assertEqual(
            etree.tostring(transformed),
            b'<root><xref rid="B9" ref-type="bibr">9</xref>Tabela 1 </root>',
        )

    def test_pipe_a_anchor__xref_bibr_case3(self):
        text = """<root><a href="#ref">(9-10)</a>Tabela 1 </root>"""

        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        self.assertEqual(
            etree.tostring(transformed),
            b'<root><xref rid="B9" ref-type="bibr">(9-10)</xref>Tabela 1 </root>',
        )

    @unittest.skip("TODO")
    def test_pipe_a_anchor__xref_figure(self):
        text = """<root><a href="#tabela1">Tabela 1</a> resultado global do levantamento efetuado <img src="/img/revistas/rsp/v8n3/05t1.gif"/></root>"""

        data = self._transform(text, self.pipeline.ImgPipe())
        raw, transformed = self.pipeline.APipe(super_obj=self.pipeline).transform(data)

        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><xref rid="t1" ref-type="table">Tabela 1</xref> resultado global do levantamento efetuado <table-wrap id="t1"><graphic xmlns:ns0="http://www.w3.org/1999/xlink" ns0:href="/img/revistas/rsp/v8n3/05t1.gif"/></table-wrap></root>""",
        )

    def test_pipe_a_hiperlink(self):

        text = [
            "<root>",
            '<p><a href="https://new.scielo.br"/></p>',
            '<p><a href="//www.google.com"><img src="mail.gif"/></a></p>',
            '<p><a href="ftp://www.bbc.com">BBC</a></p>',
            '<p><a href="../www.bbc.com">Enviar <b>e-mail para</b> mim</a></p>',
            "</root>",
        ]
        text = "".join(text)
        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )

        nodes = transformed.findall(".//ext-link")
        self.assertEqual(len(nodes), 4)
        data = [
            ("https://new.scielo.br", b""),
            ("//www.google.com", b'<img src="mail.gif"/>'),
            ("ftp://www.bbc.com", b"BBC"),
            ("../www.bbc.com", b"Enviar <b>e-mail para</b> mim"),
        ]
        for node, item in zip(nodes, data):
            link, content = item
            with self.subTest(node=node):
                self.assertIn(content, etree.tostring(node).strip())
                self.assertEqual(
                    link, node.attrib["{http://www.w3.org/1999/xlink}href"]
                )
                self.assertEqual("uri", node.attrib["ext-link-type"])
                self.assertEqual(len(node.attrib), 2)

    def test_pipe_remove_a_without_href(self):
        text = "<root><a>Teste</a></root>"
        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )
        self.assertIsNone(transformed.find(".//a"))

    def test_pipe_a_href_error(self):
        text = '<root><a href="error">Teste</a></root>'
        raw, transformed = self._transform(
            text, self.pipeline.APipe(super_obj=self.pipeline)
        )
        self.assertEqual(
            etree.tostring(transformed).strip(),
            b'<root><a href="error">Teste</a></root>',
        )

    def test_pipe_td(self):
        text = '<root><td width="" height="" style="style"><p>Teste</p></td></root>'
        raw, transformed = self._transform(text, self.pipeline.TdCleanPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><td style="style"><p>Teste</p></td></root>',
        )

    def test_pipe_blockquote(self):
        text = "<root><p><blockquote>Teste</blockquote></p></root>"
        raw, transformed = self._transform(text, self.pipeline.BlockquotePipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"<root><p><disp-quote>Teste</disp-quote></p></root>",
        )

    def test_pipe_remove_deprecated_small(self):
        text = "<root><p><bold><small>   Teste</small></bold></p></root>"
        raw, transformed = self._transform(text, self.pipeline.DeprecatedHTMLTagsPipe())
        self.assertEqual(
            etree.tostring(transformed), b"<root><p><bold>   Teste</bold></p></root>"
        )

    def test_pipe_remove_deprecated_big(self):
        text = "<root><p><big>Teste</big></p></root>"
        raw, transformed = self._transform(text, self.pipeline.DeprecatedHTMLTagsPipe())
        self.assertEqual(etree.tostring(transformed), b"<root><p>Teste</p></root>")

    def test_pipe_remove_deprecated_dir(self):
        text = "<root><p><dir>Teste</dir></p></root>"
        raw, transformed = self._transform(text, self.pipeline.DeprecatedHTMLTagsPipe())
        self.assertEqual(etree.tostring(transformed), b"<root><p>Teste</p></root>")

    def test_pipe_remove_deprecated_font(self):
        text = "<root><p><font>Teste</font></p></root>"
        raw, transformed = self._transform(text, self.pipeline.DeprecatedHTMLTagsPipe())
        self.assertEqual(etree.tostring(transformed), b"<root><p>Teste</p></root>")

    def test_remove_exceding_style_tags(self):
        text = "<root><p><b></b></p><p><b>A</b></p><p><i><b/></i>Teste</p></root>"
        raw, transformed = self._transform(
            text, self.pipeline.RemoveExcedingStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed), b"<root><p/><p><b>A</b></p><p>Teste</p></root>"
        )

    def test_remove_exceding_style_tags_2(self):
        text = "<root><p><b><i>dado<u></u></i></b></p></root>"
        raw, transformed = self._transform(
            text, self.pipeline.RemoveExcedingStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed), b"<root><p><b><i>dado</i></b></p></root>"
        )

    def test_remove_exceding_style_tags_3(self):
        text = "<root><p><b>Titulo</b></p><p><b>Autor</b></p><p>Teste<i><b/></i></p></root>"
        raw, transformed = self._transform(
            text, self.pipeline.RemoveExcedingStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed),
            b"<root><p><b>Titulo</b></p><p><b>Autor</b></p><p>Teste</p></root>",
        )

    def test_remove_exceding_style_tags_4(self):
        text = '<root><p><b>   <img src="x"/></b></p><p><b>Autor</b></p><p>Teste<i><b/></i></p></root>'
        raw, transformed = self._transform(
            text, self.pipeline.RemoveExcedingStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><p>   <img src="x"/></p><p><b>Autor</b></p><p>Teste</p></root>',
        )

    def test_pipe_graphicChildren_sub_remove(self):
        text = """<root><p><sub><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></sub></p></root>"""
        raw, transformed = self._transform(text, self.pipeline.GraphicChildrenPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><p><sub><inline-graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></sub></p></root>""",
        )

    def test_pipe_graphicChildren_italic(self):
        text = """<root><p><italic>Essa foto<graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></italic></p></root>"""
        raw, transformed = self._transform(text, self.pipeline.GraphicChildrenPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><p><italic>Essa foto<inline-graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></italic></p></root>""",
        )

    def test_pipe_graphicChildren_bold(self):
        text = """<root><p><bold><p>nova imagem</p><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></bold></p></root>"""
        raw, transformed = self._transform(text, self.pipeline.GraphicChildrenPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><p><bold><p>nova imagem</p><inline-graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></bold></p></root>""",
        )

    def test_pipe_remove_comments(self):
        text = """<root><!-- COMMENT 1 --><x>TEXT 1</x><y>TEXT 2 <!-- COMMENT 2 --></y></root>"""
        raw, transformed = self._transform(text, self.pipeline.RemoveCommentPipe())
        self.assertEqual(
            etree.tostring(transformed), b"""<root><x>TEXT 1</x><y>TEXT 2 </y></root>"""
        )

    def test_pipe_disp_quote(self):
        text = """<root><disp-quote>TEXT</disp-quote></root>"""
        raw, transformed = self._transform(text, self.pipeline.DispQuotePipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><disp-quote><p>TEXT</p></disp-quote></root>""",
        )

    def test_pipe_disp_quote_case2(self):
        text = """<root><disp-quote><p>TEXT 1</p>TEXT 2</disp-quote></root>"""
        raw, transformed = self._transform(text, self.pipeline.DispQuotePipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><disp-quote><p>TEXT 1</p><p>TEXT 2</p></disp-quote></root>""",
        )

    def test_pipe_disp_quote_case3(self):
        text = """<root><disp-quote><italic>TEXT 1</italic></disp-quote></root>"""
        raw, transformed = self._transform(text, self.pipeline.DispQuotePipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><disp-quote><p><italic>TEXT 1</italic></p></disp-quote></root>""",
        )

    def test__process(self):
        def f(node):
            node.tag = node.tag.upper()
            return node

        apply_change = ("div", "img", "i")

        tags = ("div", "img", "i", "p")
        expected_tags = ("DIV", "IMG", "I", "p")
        text = "<root><div>bla</div><img>bla</img><p>bla</p><i>bla</i></root>"
        tree = etree.fromstring(text)
        for tag, expected_tag in zip(tags, expected_tags):
            with self.subTest(tag=tag):
                if tag in apply_change:
                    _process(tree, tag, f)

                found = tree.findall(".//%s" % expected_tag)
                self.assertIsNotNone(found)

    def test_pipe_remove_ref_id(self):
        text = """<root><a xref_id="B1" id="B1">Texto</a></root>"""
        raw, transformed = self._transform(text, self.pipeline.RemoveRefIdPipe())
        self.assertEqual(
            etree.tostring(transformed), b"""<root><a id="B1">Texto</a></root>"""
        )

    def test_pipe_remove_id_duplicated(self):
        text = """<root><a id="B1">Texto</a><p>Texto</p><a id="B1">Texto</a></root>"""
        raw, transformed = self._transform(text, self.pipeline.RemoveDuplicatedIdPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><a id="B1">Texto</a><p>Texto</p><a id="B1-duplicate-0">Texto</a></root>""",
        )


class Test_RemovePWhichIsParentOfPPipe_Case1(unittest.TestCase):
    def setUp(self):
        self.text = """<root>
            <body>
                <p>
                    <p>paragrafo 1</p>
                    <p>paragrafo 2</p>
                </p>
            </body>
            </root>"""
        self.xml = etree.fromstring(self.text)
        self.pipe = HTML2SPSPipeline(
            pid="S1234-56782018000100011"
        ).RemovePWhichIsParentOfPPipe()

    def _compare_tags_and_texts(self, transformed, expected):
        def normalize(xmltree):
            s = "".join(etree.tostring(xmltree, encoding="unicode").split())
            s = s.replace("><", ">BREAK<")
            return s.split("BREAK")

        self.assertEqual(
            [node.tag for node in transformed.findall(".//body//*")],
            [node.tag for node in expected.findall(".//body//*")],
        )
        self.assertEqual(
            [
                node.text.strip() if node.text else ""
                for node in transformed.findall(".//body//*")
            ],
            [
                node.text.strip() if node.text else ""
                for node in expected.findall(".//body//*")
            ],
        )
        self.assertEqual(normalize(transformed), normalize(expected))

    def test_identify_extra_p_tags(self):
        expected = etree.fromstring(
            """<root>
            <body>
                <REMOVE_P>
                    <p>paragrafo 1</p>
                    <p>paragrafo 2</p>
                </REMOVE_P>
            </body>
            </root>"""
        )
        self.pipe._identify_extra_p_tags(self.xml)
        self.assertEqual(len(self.xml.findall(".//body//p")), 2)
        self.assertEqual(len(self.xml.findall(".//body//*")), 3)
        self._compare_tags_and_texts(self.xml, expected)

    def test_transform(self):
        expected = etree.fromstring(
            """<root>
            <body>
            <p>paragrafo 1</p>
            <p>paragrafo 2</p>
            </body>
            </root>"""
        )

        data = self.text, self.xml
        raw, transformed = self.pipe.transform(data)
        print("?????", etree.tostring(transformed))

        self.assertEqual(len(transformed.findall(".//body//p")), 2)
        self.assertEqual(len(transformed.findall(".//body//*")), 2)
        self._compare_tags_and_texts(transformed, expected)


class Test_RemovePWhichIsParentOfPPipe_Case2(unittest.TestCase):
    def setUp(self):
        self.text = """<root>
            <body>
                <p>
                    texto 0
                    <p>paragrafo 1</p>
                    texto 2
                    <p>paragrafo 3</p>
                    texto 4
                </p>
            </body>
            </root>"""
        self.xml = etree.fromstring(self.text)
        self.pipe = HTML2SPSPipeline(
            pid="S1234-56782018000100011"
        ).RemovePWhichIsParentOfPPipe()

    def _compare_tags_and_texts(self, transformed, expected):
        def normalize(xmltree):
            s = "".join(etree.tostring(xmltree, encoding="unicode").split())
            s = s.replace("><", ">BREAK<")
            return s.split("BREAK")

        self.assertEqual(
            [node.tag for node in transformed.findall(".//body//*")],
            [node.tag for node in expected.findall(".//body//*")],
        )
        self.assertEqual(
            [
                node.text.strip() if node.text else ""
                for node in transformed.findall(".//body//*")
            ],
            [
                node.text.strip() if node.text else ""
                for node in expected.findall(".//body//*")
            ],
        )
        self.assertEqual(normalize(transformed), normalize(expected))

    def test__tag_texts(self):
        expected = etree.fromstring(
            """<root>
            <body>
                <p>
                    <p>texto 0</p>
                    <p>paragrafo 1</p>
                    <p>texto 2</p>
                    <p>paragrafo 3</p>
                    <p>texto 4</p>
                </p>
            </body>
            </root>"""
        )
        xml = self.xml
        self.pipe._tag_texts(xml)
        result = xml.findall(".//body//p")
        self.assertEqual(len(xml.findall(".//body")), 1)
        self.assertEqual(len(result), 6)
        self._compare_tags_and_texts(self.xml, expected)

    def test__identify_extra_p_tags(self):
        expected = etree.fromstring(
            """<root>
            <body>
                <REMOVE_P>
                    texto 0
                    <p>paragrafo 1</p>
                    texto 2
                    <p>paragrafo 3</p>
                    texto 4
                </REMOVE_P>
            </body>
            </root>"""
        )
        xml = self.xml
        self.pipe._identify_extra_p_tags(xml)
        self.assertEqual(len(xml.findall(".//body")), 1)
        self._compare_tags_and_texts(xml, expected)

    def test_transform(self):
        expected = etree.fromstring(
            """<root>
            <body>
            <p>texto 0</p>
            <p>paragrafo 1</p>
            texto 2
            <p>paragrafo 3</p>
            texto 4
            </body>
            </root>"""
        )
        raw, transformed = self.pipe.transform((self.text, self.xml))
        self.assertEqual(len(transformed.findall(".//body")), 1)
        self._compare_tags_and_texts(self.xml, expected)


class Test_RemovePWhichIsParentOfPPipe_Case3(unittest.TestCase):
    def setUp(self):
        self.text = """<root>
            <body>
                <p>
                    <p>texto 0</p>
                    <p>paragrafo 1</p>
                    <p>
                        <p>
                            paragrafo 2
                            <p>texto 3</p>
                        </p>
                        <p>paragrafo 4</p>
                    </p>

                    <p>paragrafo 5</p>
                    <p>texto 6</p>
                </p>
            </body>
            </root>"""
        self.xml = etree.fromstring(self.text)
        self.pipe = HTML2SPSPipeline(
            pid="S1234-56782018000100011"
        ).RemovePWhichIsParentOfPPipe()

    def _compare_tags_and_texts(self, transformed, expected):
        def normalize(xmltree):
            s = "".join(etree.tostring(xmltree, encoding="unicode").split())
            s = s.replace("><", ">BREAK<")
            return s.split("BREAK")

        self.assertEqual(
            [node.tag for node in transformed.findall(".//body//*")],
            [node.tag for node in expected.findall(".//body//*")],
        )
        self.assertEqual(
            [
                node.text.strip() if node.text else ""
                for node in transformed.findall(".//body//*")
            ],
            [
                node.text.strip() if node.text else ""
                for node in expected.findall(".//body//*")
            ],
        )
        self.assertEqual(normalize(transformed), normalize(expected))

    def test__identify_extra_p_tags(self):
        expected = etree.fromstring(
            """<root>
            <body>
                <REMOVE_P>
                    <p>texto 0</p>
                    <p>paragrafo 1</p>
                    <REMOVE_P>
                        <REMOVE_P>
                            paragrafo 2
                            <p>texto 3</p>
                        </REMOVE_P>
                        <p>paragrafo 4</p>
                    </REMOVE_P>
                    <p>paragrafo 5</p>
                    <p>texto 6</p>
                </REMOVE_P>
                </body>
            </root>"""
        )
        self.pipe._identify_extra_p_tags(self.xml)
        self._compare_tags_and_texts(self.xml, expected)

    def test_transform(self):
        expected = etree.fromstring(
            """<root>
            <body>
                <p>texto 0</p>
                <p>paragrafo 1</p>
                <p>paragrafo 2</p>
                <p>texto 3</p>
                <p>paragrafo 4</p>
                <p>paragrafo 5</p>
                <p>texto 6</p>
            </body>
            </root>"""
        )
        raw, transformed = self.pipe.transform((self.xml, expected))
        self.assertEqual(len(transformed.findall(".//body")), 1)
        self._compare_tags_and_texts(transformed, expected)


class TestInferer(unittest.TestCase):
    def test_tag_and_reftype_from_a_href_text(self):
        result = Inferer().tag_and_reftype_from_a_href_text(
            "APPENDIX- Click to enlarge"
        )
        self.assertEqual(result, ("app", "app"))


class TestRemoveElementOrComment(unittest.TestCase):
    def test_etree_remove_removes_element_and_text_after_element(self):
        text = "<root><a name='bla'/>texto sera removido tambem</root>"
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        xml.remove(node)
        self.assertEqual(etree.tostring(xml), b"<root/>")

    def test_etree_remove_removes_comment_and_text_after_comment(self):
        text = "<root><!-- comentario -->texto sera removido tambem</root>"
        xml = etree.fromstring(text)
        comment = xml.xpath("//comment()")
        xml.remove(comment[0])
        self.assertEqual(etree.tostring(xml), b"<root/>")

    def test__remove_element_or_comment_keep_text_after_element(self):
        text = "<root><a name='bla'/>texto a manter</root>"
        expected = b"<root>texto a manter</root>"
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        removed = _remove_element_or_comment(node)
        self.assertEqual(removed, "a")
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_element_or_comment_removes_keep_text_after_comment(self):
        text = "<root><!-- comentario -->texto a manter</root>"
        expected = b"<root>texto a manter</root>"
        xml = etree.fromstring(text)
        comment = xml.xpath("//comment()")
        _remove_element_or_comment(comment[0])
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_element_or_comment_keeps_spaces_after_element(self):
        text = "<root> <a name='bla'/> texto a manter</root>"
        expected = b"<root>texto a manter</root>"
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        removed = _remove_element_or_comment(node)
        self.assertEqual(removed, "a")
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_element_or_comment_keeps_spaces_after_comment(self):
        text = "<root> <!-- comentario --> texto a manter</root>"
        expected = b"<root>texto a manter</root>"
        xml = etree.fromstring(text)
        comment = xml.xpath("//comment()")
        _remove_element_or_comment(comment[0])
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_element_or_comment_xref(self):
        text = """<root><xref href="#corresp"><graphic xmlns:ns2="http://www.w3.org/1999/xlink"
        ns2:href="/img/revistas/gs/v29n2/seta.gif"/></xref></root>"""

        xml = etree.fromstring(text)
        node = xml.find(".//xref")

        _remove_element_or_comment(node)
        self.assertEqual(
            etree.tostring(xml),
            b'<root><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/></root>',
        )

    def test__remove_element_or_comment_xref(self):
        text = """<root>
        <a name="back" id="back"/>
        <a href="#home">*</a>
        Corresponding author
        </root>
        """
        expected = b"""<root>
        <a name="back" id="back"/>
        *
        Corresponding author
        </root>
        """.strip()
        xml = etree.fromstring(text)
        nodes = xml.findall(".//a")
        _remove_element_or_comment(nodes[1])
        self.assertEqual(etree.tostring(xml), expected)


class TestAddAssetInfoToTablePipe(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        self.pipeline = ConvertElementsWhichHaveIdPipeline(self.html_pl)

    def test_pipe_table(self):
        text = """<root><table id="B1"><tr><td>Texto</td></tr></table></root>"""
        xml = etree.fromstring(text)
        data = text, xml
        raw, transformed = self.pipeline.AddAssetInfoToTablePipe(
            super_obj=self.html_pl
        ).transform(data)
        table = transformed.find(".//table")
        self.assertEqual(table.attrib.get("xml_id"), "b1")
        self.assertEqual(table.attrib.get("xml_label"), "Tab")


class TestCreateAssetElementsFromImgOrTableElementsPipe(unittest.TestCase):
    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline(HTML2SPSPipeline(pid="S1234-56782018000100011"))
        self.pipe = pipeline.CreateAssetElementsFromImgOrTableElementsPipe(pipeline)

    def _transform(self, text):
        xml = etree.fromstring(text)
        return self.pipe.transform((text, xml))

    def test_transform__creates_fig(self):
        text = """<root>
            <p><img align="x" src="a04qdr04.gif"
                xml_id="qdr04" xml_reftype="fig"
                xml_tag="fig"
                xml_label="Fig"/></p>
        </root>"""
        text, xml = self._transform(text)
        self.assertIsNotNone(xml.findall(".//fig/img"))

    def test_transform__creates_fig_with_label_and_caption(self):
        text = """<root>
            <p><img align="x" src="a04qdr04.gif"
                xml_id="qdr04" xml_reftype="fig"
                xml_tag="fig"
                xml_label="Fig"/></p>
            <p>Figura 1 - texto figura</p>
        </root>"""
        text, xml = self._transform(text)
        self.assertIsNotNone(xml.findall(".//fig/img"))
        self.assertIsNotNone(xml.findall(".//fig/label"))
        self.assertIsNotNone(xml.findall(".//fig/caption"))

    def test_transform__creates_table_wrap(self):
        text = """<root>
            <p><img align="x" src="a04t04.gif"
                xml_id="t04" xml_reftype="table"
                xml_tag="table-wrap"
                xml_label="Tab"/></p>
        </root>"""
        text, xml = self._transform(text)
        self.assertIsNotNone(xml.findall(".//table-wrap/img"))

    def test_transform__creates_table_wrap_with_label_and_caption(self):
        text = """<root>
            <p>Tabela</p>
            <p><img align="x" src="a04t04.gif"
                xml_id="t04" xml_reftype="table"
                xml_tag="table-wrap"
                xml_label="Tab"/></p>
        </root>"""
        text, xml = self._transform(text)
        self.assertIsNotNone(xml.findall(".//table-wrap/img"))
        self.assertIsNotNone(xml.findall(".//table-wrap/label"))
        self.assertIsNotNone(xml.findall(".//table-wrap/caption"))

    def test_transform__creates_table_wrap_with_table_and_label_only(self):
        text = """<root>
            <p>Tabela</p>
            <p><table
                xml_id="t04" xml_reftype="table"
                xml_tag="table-wrap"
                xml_label="Tab"/></p>
        </root>"""
        text, xml = self._transform(text)
        self.assertIsNotNone(xml.findall(".//table-wrap/table"))
        self.assertIsNotNone(xml.findall(".//table-wrap/label"))
        self.assertEqual(xml.findall(".//table-wrap/caption"), [])

    def test_transform__completes_fig_with_label_and_caption(self):
        text = """<root>
            <p><fig id="qdr04" xref_id="qdr04"></fig></p>
            <p>Quadro 1. Esta é descriçãp da Doc...</p>
            <p><img align="x" src="a04qdr04.gif"
                xml_id="qdr04" xml_reftype="fig"
                xml_tag="fig"
                xml_label="Quadro"/></p>
        </root>"""

        text, xml = self._transform(text)
        self.assertEqual(len(xml.findall(".//fig")), 1)
        self.assertIsNotNone(xml.find(".//fig/label"))
        self.assertIsNotNone(xml.find(".//fig/caption"))
        self.assertIsNotNone(xml.find(".//fig/img"))
        children = xml.find(".//fig").getchildren()
        self.assertEqual(children[0].tag, "label")
        self.assertEqual(children[0].text, "Quadro 1")
        self.assertEqual(children[1].findtext("title"), "Esta é descriçãp da Doc...")
        self.assertEqual(children[2].tag, "img")

    def test_transform__completes_table_wrap(self):
        text = """<root>
            <p><table-wrap id="t04" xref_id="t04"></table-wrap></p>
            <p>Tabela 1. Esta é descriçãp da Doc...</p>
            <p><img align="x" src="a04t04.gif"
                xml_id="t04" xml_reftype="table"
                xml_tag="table-wrap"
                xml_label="Tabela"/></p>
        </root>"""

        text, xml = self._transform(text)
        self.assertEqual(len(xml.findall(".//table-wrap")), 1)
        self.assertIsNotNone(xml.find(".//table-wrap/label"))
        self.assertIsNotNone(xml.find(".//table-wrap/caption"))
        self.assertIsNotNone(xml.find(".//table-wrap/img"))
        children = xml.find(".//table-wrap").getchildren()
        self.assertEqual(children[0].tag, "label")
        self.assertEqual(children[0].text, "Tabela 1")
        self.assertEqual(children[1].findtext("title"), "Esta é descriçãp da Doc...")
        self.assertEqual(children[2].tag, "img")

    def test__find_label_and_caption_in_node_label_without_number(self):
        text = """<root>
            <p><bold>Figura</bold> - Legenda da figura</p>
            <a xml_label="fig">Figura</a>
        </root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        label_and_caption_node = xml.find(".//p")
        result = self.pipe._find_label_and_caption_in_node(node, label_and_caption_node)
        _node, label, caption = result
        self.assertIsNotNone(result)
        self.assertIs(label_and_caption_node, _node)
        self.assertEqual(label.text, "Figura")
        self.assertEqual(caption.findtext("title"), "- Legenda da figura")

    def test__find_label_and_caption_in_node_label_figure_a(self):
        text = """<root>
            <p><bold>Figura A</bold> - Legenda da figura</p>
            <a xml_label="fig">Figura A</a>
        </root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        label_and_caption_node = xml.find(".//p")
        result = self.pipe._find_label_and_caption_in_node(node, label_and_caption_node)
        _node, label, caption = result
        self.assertIsNotNone(result)
        self.assertIs(label_and_caption_node, _node)
        self.assertEqual(label.text, "Figura A")
        self.assertEqual(caption.findtext("title"), "- Legenda da figura")

    def test_find_label_and_caption_in_node(self):
        text = """<root>
            <p><bold>Figura</bold> <bold>1B</bold> - Legenda da figura</p>
            <a xml_label="fig">Figura 1B</a>
        </root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        label_and_caption_node = xml.find(".//p")
        result = self.pipe._find_label_and_caption_in_node(node, label_and_caption_node)
        _node, label, caption = result
        self.assertIsNotNone(result)
        self.assertIs(label_and_caption_node, _node)
        self.assertEqual(label.text, "Figura 1B")
        self.assertEqual(caption.findtext("title"), "- Legenda da figura")

    def test__find_label_and_caption_around_node_previous(self):
        text = """<root>
            <p><bold>Table</bold> - Legenda da table</p>
            <p><a xml_label="Tab">Table</a></p>
        </root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        result = self.pipe._find_label_and_caption_around_node(node)
        label, caption = result
        self.assertIsNotNone(result)
        self.assertEqual(label.text, "Table")
        self.assertEqual(caption.findtext("title"), "- Legenda da table")

    def test__find_label_and_caption_around_node_next(self):
        text = """<root>
            <p><a xml_label="Fig">Figura 1</a></p>
            <p><bold>Figura</bold> <bold>1</bold> - Legenda da figura</p>
        </root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        result = self.pipe._find_label_and_caption_around_node(node)
        label, caption = result
        self.assertIsNotNone(result)
        self.assertEqual(label.text, "Figura 1")
        self.assertEqual(caption.findtext("title"), "- Legenda da figura")

    def test__find_label_and_caption_around_node_for_img(self):
        text = """<root>
            <p><img xml_label="Figura" xml_id="f1"/></p>
            <p><bold>Figura</bold> <bold>1</bold> - Legenda da figura</p>
        </root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//img")
        result = self.pipe._find_label_and_caption_around_node(node)
        label, caption = result
        self.assertIsNotNone(result)
        self.assertEqual(label.text, "Figura 1")
        self.assertEqual(caption.findtext("title"), "- Legenda da figura")


class TestCreateAssetElementsFromExternalLinkElementsPipe(unittest.TestCase):
    def setUp(self):
        html_pl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        self.pipeline = ConvertElementsWhichHaveIdPipeline(html_pl)
        self.pipe = self.pipeline.CreateAssetElementsFromExternalLinkElementsPipe(
            html_pl
        )

    def _transform(self, text):
        xml = etree.fromstring(text)
        return self.pipe.transform((text, xml))

    def test_transform(self):
        text = """<root>
            <p><a href="en_a05tab02.gif"
                xml_id="qdr04" xml_reftype="fig"
                xml_tag="fig">Fig 1</a> tail 1</p>
            <p><a href="a04t04.gif"
                xml_id="t04" xml_reftype="table"
                xml_tag="table-wrap">Table 1</a> tail 2</p>
        </root>"""
        text, xml = self._transform(text)
        xref = xml.findall(".//xref")
        p = xml.findall(".//p")
        self.assertEqual(len(p), 4)
        self.assertEqual(len(xref), 2)
        self.assertEqual(len(xml.findall(".//a")), 0)
        self.assertEqual(xref[0].attrib.get("ref-type"), "fig")
        self.assertEqual(xref[1].attrib.get("ref-type"), "table")
        self.assertEqual(xref[0].attrib.get("rid"), "qdr04")
        self.assertEqual(xref[1].attrib.get("rid"), "t04")

        self.assertIsNotNone(p[1].find("fig"))
        self.assertIsNotNone(p[3].find("table-wrap"))

    def test_transform_fig_with_subtitle(self):
        text = """<root>
            <p><a align="x" href="a04qdr04.gif"
                xml_id="qdr04" xml_reftype="fig"
                xml_tag="fig">Figura</a></p>
        </root>"""
        text, xml = self._transform(text)
        children = xml.find(".//fig").getchildren()
        self.assertIsNone(xml.find(".//fig/label"))
        self.assertEqual(children[0].tag, "graphic")
        self.assertIsNone(xml.find(".//fig/a"))


class TestConvertElementsWhichHaveIdPipeline(unittest.TestCase):
    def test_transform_two_internal_link_img_aname(self):
        text = """<root>
        <p>Para uma avalição mais precisa das formulações semi-discretas,
        calculamos os logaritmos dos erros considerando malhas na
        <a href="#tab02">Tabela 2</a>. </p>
        <p><a name="tab02" id="tab02"/></p>
        <p>Tabela 2</p>
        <p align="center"><img src="/img/revistas/tema/v14n3/a05tab02.jpg"/></p>
        <p><a href="#tab02">Tabela 2</a></p>.</root>"""

        raw = text
        xml = etree.fromstring(text)
        pl_html = HTML2SPSPipeline(pid="S1234-56782018000100011")
        pl_asset = ConvertElementsWhichHaveIdPipeline(pl_html)

        raw, xml = pl_html.DocumentPipe(pl_html).transform((raw, xml))
        print(etree.tostring(xml))
        raw, xml = pl_html.AnchorAndInternalLinkPipe(pl_html).transform((raw, xml))
        print(etree.tostring(xml))
        self.assertIsNone(xml.find(".//a[@id]"))
        self.assertIsNotNone(xml.find(".//table-wrap[@id]"))
        self.assertEqual(len(xml.findall(".//xref[@ref-type='table']")), 2)
        self.assertIsNone(xml.find(".//table-wrap[@id]/img"))

        raw, xml = pl_html.ConvertElementsWhichHaveIdPipe(pl_html).transform((raw, xml))
        self.assertIsNotNone(xml.find(".//table-wrap[@id]/img"))
        self.assertIsNotNone(xml.find(".//table-wrap[@id]/label"))
        self.assertIsNone(xml.find(".//table-wrap[@id]/caption"))


class TestConversionToAnnex(unittest.TestCase):
    def test_convert_to_app(self):
        text = """<root>
        <a href="#anx01">Anexo 1</a>
        <p><a name="anx01" id="anx01"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg"/></p>
        </root>
        """

        xml = etree.fromstring(text)
        htmlpl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text, xml = htmlpl.DocumentPipe(htmlpl).transform((text, xml))
        self.assertEqual(
            etree.tostring(xml),
            b"""<root>
        <a href="#anx01" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1">Anexo 1</a>
        <p><a name="anx01" id="anx01" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>""",
        )

        text, xml = htmlpl.AnchorAndInternalLinkPipe(htmlpl).transform((text, xml))
        self.assertEqual(
            etree.tostring(xml),
            b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p><app id="anx01"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>""",
        )
        assetpl = ConvertElementsWhichHaveIdPipeline(htmlpl)
        text, xml = assetpl.CreateAssetElementsFromExternalLinkElementsPipe(
            htmlpl
        ).transform((text, xml))
        self.assertEqual(
            etree.tostring(xml),
            b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p><app id="anx01"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>""",
        )

        text, xml = assetpl.CreateAssetElementsFromImgOrTableElementsPipe(
            htmlpl
        ).transform((text, xml))
        self.assertEqual(
            etree.tostring(xml),
            b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p><app id="anx01"><img src="/img/revistas/trends/v33n3/a05tab01.jpg"/></app></p>
        <p/>
        </root>""",
        )
        self.assertIsNotNone(xml.find(".//app/img"))


class TestConversionToTableWrap(unittest.TestCase):
    def test_convert_to_table_wrap(self):
        text = """<root>
        <a href="#tab01">Table 1</a>
        <p><a name="tab01" id="tab01"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05t01.jpg"/></p>
        </root>
        """
        xml = etree.fromstring(text)

        html_pl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text, xml = html_pl.DocumentPipe(html_pl).transform((text, xml))
        text, xml = html_pl.AnchorAndInternalLinkPipe(html_pl).transform((text, xml))

        asset_pl = ConvertElementsWhichHaveIdPipeline(html_pl)
        text, xml = asset_pl.CreateAssetElementsFromImgOrTableElementsPipe(
            asset_pl
        ).transform((text, xml))

        self.assertIsNotNone(xml.find(".//table-wrap/img"))


class TestConversionToCorresp(unittest.TestCase):
    def test_convert_to_corresp(self):
        text = """<root>
        <a name="home" id="home"/>
        <a name="back" id="back"/>
        <a href="#home">*</a>
        Corresponding author
        </root>
        """
        expected_after_internal_link_as_asterisk_pipe = b"""<root>
        <a name="home" id="home"/>
        <a name="back" id="back"/>
        *
        Corresponding author
        </root>"""
        expected_after_anchor_and_internal_link_pipe = b"""<root><fn id="back" fn-type="corresp"><p>* Corresponding author</p></fn></root>"""

        xml = etree.fromstring(text)
        pl = HTML2SPSPipeline(pid="S1234-56782018000100011")

        text, xml = pl.InternalLinkAsAsteriskPipe(pl).transform((text, xml))
        self.assertNotIn(b'<a href="#home">*</a>', etree.tostring(xml))
        self.assertEqual(
            etree.tostring(xml), expected_after_internal_link_as_asterisk_pipe
        )

        text, xml = pl.DocumentPipe(pl).transform((text, xml))
        self.assertIn(
            b'<a name="back" id="back" xml_tag="corresp" xml_reftype="corresp" xml_id="back"/>',
            etree.tostring(xml),
        )

        text, xml = pl.AnchorAndInternalLinkPipe(pl).transform((text, xml))
        self.assertEqual(
            etree.tostring(xml), expected_after_anchor_and_internal_link_pipe
        )


class TestConversionToFig(unittest.TestCase):
    def test_convert_to_figure(self):
        text = """<root><p>Monthly AE rate ranged from 0.92 to 9.77/100
        patient-days, with a mean of 5.34
        (<a href="#fig01en">Figure 1</a>).
        Mean extubation rates per year were 4.38±1.94, 5.36±2.59
        and 4.73±2.16 in 2006, 2007 and 2008, respectively.
        AE rates according to the variables analyzed
        are described in
        <a href="/img/revistas/jped/v86n3/en_a05tab02.gif">Table 2</a>.</p>
        <p><a name="fig01en" id="663f1en"/>
        <img src="/img/revistas/jped/v86n3/en_a05fig01.gif"/></p></root>"""

        xml = etree.fromstring(text)
        pl = HTML2SPSPipeline(pid="S1234-56782018000100011")

        text, xml = pl.FixElementAPipe(pl).transform((text, xml))
        text, xml = pl.DocumentPipe(pl).transform((text, xml))
        _xml = etree.tostring(xml)

        self.assertIn(
            b'<a href="#fig01en" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1">Figure 1</a>',
            _xml,
        )
        self.assertIn(
            b'<a name="fig01en" id="fig01en" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1"/>',
            _xml,
        )
        self.assertIn(
            b'<img src="/img/revistas/jped/v86n3/en_a05fig01.gif" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1"/>',
            _xml,
        )
        text, xml = pl.AnchorAndInternalLinkPipe(pl).transform((text, xml))
        _xml = etree.tostring(xml)
        self.assertIn(b'<xref ref-type="fig" rid="fig01en">Figure 1</xref>', _xml)
        self.assertIn(b'<fig id="fig01en"/>', _xml)

        apl = ConvertElementsWhichHaveIdPipeline(pl)
        text, xml = apl.CreateAssetElementsFromImgOrTableElementsPipe(apl).transform(
            (text, xml)
        )
        self.assertIsNotNone(xml.findall(".//fig/img"))

        text, xml = pl.ImgPipe(pl).transform((text, xml))
        self.assertIsNotNone(xml.findall(".//fig/graphic"))


class TestRemoveThumbImg(unittest.TestCase):
    def test_convert_to_figure(self):
        text = """<root xmlns:xlink="http://www.w3.org/1999/xlink"><p><a href="/img/revistas/hoehnea/v37n3/a05img01.jpg"><img src="/img/revistas/hoehnea/v37n3/a05img01-thumb.jpg"/><br/> Clique para ampliar</a></p></root>"""

        expected = b"""<root xmlns:xlink="http://www.w3.org/1999/xlink"><p><graphic xlink:href="/img/revistas/hoehnea/v37n3/a05img01.jpg"></graphic></p></root>"""

        xml = etree.fromstring(text)
        pl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        apl = ConvertElementsWhichHaveIdPipeline(pl)

        text, xml = pl.RemoveThumbImgPipe().transform((text, xml))
        self.assertNotIn(
            b'<img src="/img/revistas/hoehnea/v37n3/a05img01-thumb.jpg"/>',
            etree.tostring(xml),
        )
        text, xml = apl.CreateAssetElementsFromExternalLinkElementsPipe(pl).transform(
            (text, xml)
        )
        text, xml = pl.ImgPipe(pl).transform((text, xml))

        self.assertEqual(etree.tostring(xml), expected)


class TestFixBodyChildrenPipe(unittest.TestCase):
    def test_fix_body_children_pipe_inserts_bold_in_p(self):
        text = """<root><body><bold>título</bold>texto fora do bold</body></root>"""
        expected = (
            """<root><body><p><bold>título</bold>texto fora do bold</p></body></root>"""
        )
        xml = etree.fromstring(text)
        pl = HTML2SPSPipeline(pid="pid")
        text, xml = pl.FixBodyChildrenPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml, encoding="unicode"), expected)

    def test_fix_body_children_pipe_inserts_text_in_p(self):
        text = b"""<root><body><p>texto dentro de p</p> texto </body></root>"""
        expected = (
            b"""<root><body><p>texto dentro de p</p><p>texto</p>  </body></root>"""
        )
        xml = etree.fromstring(text)
        pl = HTML2SPSPipeline(pid="pid")
        text, xml = pl.FixBodyChildrenPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)


class Test_HTML2SPSPipeline(unittest.TestCase):

    def test_pipeline(self):
        text = """<root>
        <p>&#60;</p>
        <p> a &lt; b</p>
            <p>La nueva época de la revista
            <italic>Salud Pública de México </italic>
            </p></root>"""
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        xml = etree.fromstring(text)
        text, xml = pipeline.SetupPipe(pipeline).transform(text)
        pipes = (
            pipeline.SaveRawBodyPipe(pipeline),
            pipeline.DeprecatedHTMLTagsPipe(),
            pipeline.RemoveImgSetaPipe(),
            pipeline.RemoveDuplicatedIdPipe(),
            pipeline.RemoveExcedingStyleTagsPipe(),
            pipeline.RemoveEmptyPipe(),
            pipeline.RemoveStyleAttributesPipe(),
            pipeline.RemoveCommentPipe(),
            pipeline.BRPipe(),
            pipeline.PPipe(),
            pipeline.DivPipe(),
            pipeline.LiPipe(),
            pipeline.OlPipe(),
            pipeline.UlPipe(),
            pipeline.DefListPipe(),
            pipeline.DefItemPipe(),
            pipeline.IPipe(),
            pipeline.EmPipe(),
            pipeline.UPipe(),
            pipeline.BPipe(),
            pipeline.StrongPipe(),
            pipeline.RemoveThumbImgPipe(),
            pipeline.FixElementAPipe(pipeline),
            pipeline.InternalLinkAsAsteriskPipe(pipeline),
            pipeline.DocumentPipe(pipeline),
            pipeline.AnchorAndInternalLinkPipe(pipeline),
            pipeline.ConvertElementsWhichHaveIdPipe(pipeline),
            pipeline.APipe(pipeline),
            pipeline.ImgPipe(pipeline),
            pipeline.TdCleanPipe(),
            pipeline.TableCleanPipe(),
            pipeline.BlockquotePipe(),
            pipeline.HrPipe(),
            pipeline.TagsHPipe(),
            pipeline.DispQuotePipe(),
            pipeline.GraphicChildrenPipe(),
            pipeline.FixBodyChildrenPipe(),
            pipeline.RemovePWhichIsParentOfPPipe(),
            pipeline.RemoveRefIdPipe(),
            pipeline.SanitizationPipe()
            )
        for pipe in pipes:
            with self.subTest(str(pipe)):
                text, xml = pipe.transform((text, xml))
                resultado_unicode = etree.tostring(xml, encoding="unicode")
                resultado_b = etree.tostring(xml)
                self.assertIn(b"&#233;poca", resultado_b)
                self.assertIn("época", resultado_unicode)
                self.assertIn("&lt;", resultado_unicode)

class TestHTMLEscapingPipe(unittest.TestCase):

    def test_pipe(self):
        text = """<root>
        <p>&#60;</p>
        <p> a &lt; b</p>
            <p>La nueva época de la revista
            <italic>Salud Pública de México </italic>
            </p></root>"""
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        xml = etree.fromstring(text)
        text, xml = pipeline.SetupPipe(pipeline).transform(text)
        text, xml = pipeline.HTMLEscapingPipe().transform((text, xml))
        resultado_unicode = etree.tostring(xml, encoding="unicode")
        resultado_b = etree.tostring(xml)
        self.assertIn(b"&#233;poca", resultado_b)
        self.assertIn("época", resultado_unicode)
        self.assertIn("&amp;lt;", resultado_unicode)


class TestConvertElementsWhichHaveIdPipeline(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        self.pl = ConvertElementsWhichHaveIdPipeline(self.html_pl)

    def test_remove_thumb_img_pipe(self):
        text = """<root xmlns:xlink="http://www.w3.org/1999/xlink"><p><a href="/img/revistas/hoehnea/v37n3/a05img01.jpg"><img src="/img/revistas/hoehnea/v37n3/a05img01-thumb.jpg"/><br/> Clique para ampliar</a></p></root>"""
        expected = b"""<root xmlns:xlink="http://www.w3.org/1999/xlink"><p><img src="/img/revistas/hoehnea/v37n3/a05img01.jpg"></img></p></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pl.RemoveThumbImgPipe().transform((text, xml))
        self.assertNotIn(
            b'<img src="/img/revistas/hoehnea/v37n3/a05img01-thumb.jpg"/>',
            etree.tostring(xml),
        )
        self.assertEqual(etree.tostring(xml), expected)

    def test_fix_element_a(self):
        text = """<root><a name="_ftnref19" href="#_ftn2" id="_ftnref19"><sup>1</sup></a></root>"""
        expected = b"""<root><a name="_ftnref19" id="_ftnref19"/><a href="#_ftn2"><sup>1</sup></a></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pl.FixElementAPipe(self.pl).transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_asterisk_in_a_href(self):
        text = '<root><a name="1a" id="1a"/><a href="#1b"><sup>*</sup></a></root>'
        expected = b'<root><a name="1a" id="1a"/><sup>*</sup></root>'
        xml = etree.fromstring(text)

        text, xml = self.pl.InternalLinkAsAsteriskPipe(
            super_obj=self.pl
        ).transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)
