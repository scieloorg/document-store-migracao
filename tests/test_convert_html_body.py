# code=utf-8

import os
import unittest
from unittest.mock import patch
from lxml import etree

from documentstore_migracao.utils.convert_html_body_inferer import Inferer
from documentstore_migracao.utils.convert_html_body import (
    HTML2SPSPipeline,
    ConvertElementsWhichHaveIdPipeline,
    Document,
    _process,
    _remove_tag,
    get_node_text,
    search_asset_node_backwards,
)
from . import SAMPLES_PATH


class TestGetNodeText(unittest.TestCase):
    def test_get_node_text_does_not_return_comment_text(self):
        text = """<root>
        <texto>texto <i>
        <bold>bold</bold>
        </i> <p/> <a>element a<!-- comentario a-->
        <ign/>
        </a> <!-- comentario n -->
        <ign/> pos bold</texto> apos</root>"""
        expected = """texto bold element a pos bold apos"""
        xml = etree.fromstring(text)
        result = get_node_text(xml)
        self.assertEqual(result, expected)

    def test_get_node_text_does_not_return_extra_spaces(self):
        text = """<root>
        <texto>texto          com         muitos espaços
        </texto> ...</root>"""
        expected = """texto com muitos espaços ..."""

        xml = etree.fromstring(text)
        result = get_node_text(xml)
        self.assertEqual(result, expected)

    def test_get_node_text_for_comment_returns_empty_str(self):
        text = """<root>
        <texto>texto <i>
        <bold>bold</bold>
        </i> <p/> <a>element a<!-- comentario a-->
        <ign/>
        </a> <!-- comentario n -->
        <ign/> pos bold</texto> apos</root>"""
        xml = etree.fromstring(text)
        result = get_node_text(xml.xpath("//comment()")[0])
        self.assertEqual(result, "")


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
        expected = "<root><p>Colonização micorrízica e concentração de nutrientes em três cultivares de bananeiras em um latossolo amarelo da Amazônia central</p>  </root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_bold(self):
        text = "<root><p>Colonização micorrízica e concentração de nutrientes <bold> </bold> em três cultivares de bananeiras em um latossolo amarelo</p> </root>"
        expected = "<root><p>Colonização micorrízica e concentração de nutrientes   em três cultivares de bananeiras em um latossolo amarelo</p> </root>"
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

    def test_pipe_remove_invalid_br_removes_br_which_is_at_the_beginning(self):
        text = "<root><td><br/> texto 2</td></root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveInvalidBRPipe())
        self.assertEqual(etree.tostring(transformed), b"<root><td> texto 2</td></root>")

    def test_pipe_remove_invalid_br_removes_br_which_is_at_the_end(self):
        text = "<root><td>texto 2<br/></td></root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveInvalidBRPipe())
        self.assertEqual(etree.tostring(transformed), b"<root><td>texto 2</td></root>")

    def test_pipe_remove_invalid_br_removes_br_which_is_alone_in_a_element(self):
        text = "<root><td><br/></td></root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveInvalidBRPipe())
        self.assertEqual(etree.tostring(transformed), b"<root><td/></root>")

    def test_pipe_br_creates_break(self):
        text = "<root><td>texto 1<br/> texto 2</td></root>"
        raw, transformed = self._transform(text, self.pipeline.BRPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"<root><td>texto 1<break/> texto 2</td></root>",
        )

    def test_pipe_br_do_nothing(self):
        text = "<root><sec>texto 1<br/> texto 2</sec></root>"
        raw, transformed = self._transform(text, self.pipeline.BRPipe())
        self.assertEqual(
            etree.tostring(transformed), b"<root><sec>texto 1<br/> texto 2</sec></root>"
        )

    def test_pipe_br_to_pipe_creates_p_for_each_item_which_is_separated_by_br(self):
        text = "<root><sec>texto 1<br/> texto 2</sec></root>"
        raw, transformed = self._transform(text, self.pipeline.BR2PPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b'<root><sec><p content-type="break">texto 1</p><p content-type="break"> texto 2</p></sec></root>',
        )

    def test_pipe_br_to_pipe_creates_p_for_each_item_which_is_separated_by_br_and_remove_extra_p(
        self,
    ):
        text = '<root><p align="x">bla<br/> continua outra linha</p></root>'
        raw, transformed = self._transform(text, self.pipeline.BR2PPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"<root><p>bla</p><p> continua outra linha</p></root>",
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

    def test_remove_or_move_style_tags(self):
        text = "<root><p><b></b></p><p><b>A</b></p><p><i><b/></i>Teste</p></root>"
        raw, transformed = self._transform(
            text, self.pipeline.RemoveOrMoveStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed), b"<root><p/><p><b>A</b></p><p>Teste</p></root>"
        )

    def test_remove_or_move_style_tags_2(self):
        text = "<root><p><b><i>dado<u></u></i></b></p></root>"
        raw, transformed = self._transform(
            text, self.pipeline.RemoveOrMoveStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed), b"<root><p><b><i>dado</i></b></p></root>"
        )

    def test_remove_or_move_style_tags_3(self):
        text = "<root><p><b>Titulo</b></p><p><b>Autor</b></p><p>Teste<i><b/></i></p></root>"
        raw, transformed = self._transform(
            text, self.pipeline.RemoveOrMoveStyleTagsPipe()
        )
        self.assertEqual(
            etree.tostring(transformed),
            b"<root><p><b>Titulo</b></p><p><b>Autor</b></p><p>Teste</p></root>",
        )

    def test_remove_or_move_style_tags_4(self):
        text = '<root><p><b>   <img src="x"/></b></p><p><b>Autor</b></p><p>Teste<i><b/></i></p></root>'
        expected = (
            b'<root><p>   <img src="x"/></p><p><b>Autor</b></p><p>Teste</p></root>'
        )
        raw, transformed = self._transform(
            text, self.pipeline.RemoveOrMoveStyleTagsPipe()
        )
        self.assertEqual(etree.tostring(transformed), expected)

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


class TestEvaluateElementAToDeleteOrMarkAsFnLabelPipe(unittest.TestCase):
    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.EvaluateElementAToDeleteOrMarkAsFnLabelPipe()

    def test_pipe_converts_a_href_item_in_label_and_delete_a_name(self):
        """
        Converte
        <root><a id="tx*" name="tx*" xml_text="*"/><a href="#tx*" link-type="internal" xml_text="*">*</a> Artigo apresentado no 12&#186; Congresso USP de Controladoria e Contabilidade, S&#227;o Paulo, julho de 2012
        </root>
        em:
        <label link-type="internal" xml_text="*" label-of="nt*">*</label> Artigo apresentado no 12&#186; Congresso USP de Controladoria e Contabilidade, S&#227;o Paulo, julho de 2012
        """
        text = """
        <root>
        <a id="tx*" name="tx*" xml_text="*"/>
        <a id="nt*" name="nt*" xml_text="*"/>
        <a href="#tx*" link-type="internal" xml_text="*">*</a> Artigo apresentado no 12&#186; Congresso USP de Controladoria e Contabilidade, S&#227;o Paulo, julho de 2012
        </root>
        """
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNone(xml.find(".//a[@name='tx*']"))
        self.assertIsNotNone(xml.find(".//a[@name='nt*']"))
        self.assertIsNotNone(xml.find(".//label[@label-of='nt*']"))

    def test_pipe_does_not_convert(self):
        """
        Mantém, não converte.
        <root>
        <a name="a05tab07" id="a05tab07" xml_text="tabelas 7"/>
        <a href="#a05tab07" link-type="internal" xml_text="tabelas 7">Tabelas 7</a> e
        <a href="#a05tab07" link-type="internal" xml_text="tabela 7">Tabela 7</a>), sendo este resultado consistente com o estudo de Kober et al. (2010).
        <a href="#a05tab07" link-type="internal" xml_text="tabelas 7">Tabelas 7</a> e '
        </root>
        """
        text = b"""
        <root>
        <a name="a05tab07" id="a05tab07" xml_text="tabelas 7"/>
        <a href="#a05tab07" link-type="internal" xml_text="tabelas 7">Tabelas 7</a> e
        <a href="#a05tab07" link-type="internal" xml_text="tabela 7">Tabela 7</a>), sendo este resultado consistente com o estudo de Kober et al. (2010).
        <a href="#a05tab07" link-type="internal" xml_text="tabelas 7">Tabelas 7</a> e '
        </root>
        """.strip()
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(len(xml.findall(".//a[@name]")), 1)
        self.assertEqual(len(xml.findall(".//a[@href]")), 3)
        self.assertEqual(etree.tostring(xml), text)

    def test_pipe_remove_a_name_and_a_href(self):
        """
        Remove
        <a name="top" id="top"/>
        <a href="#top"/>

        de
        <root>
        <a name="top" id="top"/>
        <a href="#top"/>
        </root>
        """
        text = b"""
        <root>
        <a name="top" id="top"/>
        <a href="#top"/>
        </root>
        """.strip()
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(len(xml.findall(".//a[@name]")), 0)
        self.assertEqual(len(xml.findall(".//a[@href]")), 0)
        self.assertEqual(etree.tostring(xml), b'<root>\n        \n        \n        </root>')

    def test_pipe_remove_id_duplicated(self):
        text = """<root>
        <a id="B1" name="B1">Texto 1</a><p>Texto 2</p>
        <a id="B1" name="B1">Texto 3</a></root>"""
        expected = b"""<root>
        <a id="B1" name="B1">Texto 1</a><p>Texto 2</p>
        Texto 3</root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_asterisk_in_a_href(self):
        text = """<root><a href="#1a"><sup>*</sup></a>
        <a name="1a" id="1a"/><a href="#1b"><sup>*</sup></a></root>"""
        expected = b"""<root><a href="#1a"><sup>*</sup></a>
        <a name="1a" id="1a"/><sup>*</sup></root>"""
        xml = etree.fromstring(text)

        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_remove_anchor_and_links_to_text_removes_some_elements(self):
        text = """<root>
        <a href="#nota" xml_tag="xref" xml_id="nota" xml_label="1" xml_reftype="fn">1</a>
        <a name="texto" xml_tag="fn" xml_id="texto" xml_reftype="fn"/>
        <a name="nota"  xml_tag="fn" xml_id="nota" xml_reftype="fn"/>
        <a href="#texto" xml_tag="xref" xml_id="texto" xml_reftype="xref">1</a> Nota bla bla
        </root>"""
        raw, transformed = text, etree.fromstring(text)
        raw, transformed = self.pipe.transform((raw, transformed))
        nodes = transformed.findall(".//a[@name='nota']")
        self.assertEqual(len(nodes), 1)
        nodes = transformed.findall(".//a[@href='#nota']")
        self.assertEqual(len(nodes), 1)

    def test_pipe_distinguishes_nota1_and_author1(self):
        """
        author1 e nota1 tem xml_text="1",
        no entanto um é nota e outro é referência bibliográfica
        """
        text = """<root>
        <a name="topo" id="topo" xml_text="1"/>
        <p>
        <bold>Franz R. Novak</bold>
        <a href="#autor1" link-type="internal" xml_text="1"><sup>1</sup></a>
        <bold>,João Aprígio Guerra de Almeida</bold>
        <a href="#autor2" link-type="internal" xml_text="2"><sup>2</sup></a>
        </p>
        <p>A relação de causa e efeito no processo de transmissão de doenças relacionadas especificamente com alimentos contaminados com material de origem fecal foi, inicialmente, defendida por Von Fristsch em 1880, quando identificou Klebsiella sp em fezes humanas. Posteriormente, a relação entre os microorganismos provenientes desse material e doenças do trato gastrintestinal foi estabelecida por Escherich, que descreveu o <italic>Bacillus coli</italic>, atualmente <italic>Escherichia coli</italic>, sugerindo que tal microorganismo pudesse ser utilizado como indicador de contaminação de origem fecal(<a href="#nota01" link-type="internal" xml_text="1">1</a>).</p>
        <p>
        <a name="nota01" id="nota01" xml_text="1"/>1. Guarraia LJ. Brief literature review of <italic>Klebsiella</italic> as pathogens. In: Seminar on the significance of fecal coliforms in industrial waste. E.P.A.T.R. 3., Denver (CO), USA: National Field Investigations Center; 1972. </p>
        <p>
        <a name="autor1" id="autor1" xml_text="1"/>
        <a href="#topo" link-type="internal" xml_text="1"><bold><sup>1</sup></bold></a><bold>Franz R. Novak</bold> - Doutor em Microbiologia pela Universidade Federal do Rio de Janeiro. Professor nos Cursos de Mestrado e Doutorado em Saúde da Mulher e da Criança do Instituto Fernandes Figueira - IFF / Fundação Oswaldo Cruz. Membro da equipe do Banco de Leite Humano do IFF.
        </p>
        <p>
        <a name="autor2" id="autor2" xml_text="2"/>
        <a href="#topo" link-type="internal" xml_text="2"><bold><sup>2</sup></bold></a> João Aprígio Guerra de Almeida - Doutor em Saúde Pública pelo Instituto Fernandes Figueira - IFF / Fundação Oswaldo Cruz. Professor nos Cursos de Mestrado e Doutorado em Saúde da Mulher e da Criança do Instituto Fernandes Figueira. Chefe do Banco de Leite Humano do IFF.
        </p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(
            b"""<label href="#topo" link-type="internal" xml_text="1" label-of="autor1"><bold><sup>1</sup></bold></label>""",
            result,
        )
        self.assertIn(
            b"""<label href="#topo" link-type="internal" xml_text="2" label-of="autor2"><bold><sup>2</sup></bold></label>""",
            result,
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


class TestRemoveNodeOrComment(unittest.TestCase):
    def test_etree_remove_removes_element_and_tail(self):
        text = "<root><a name='bla'/>texto sera removido tambem</root>"
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        xml.remove(node)
        self.assertEqual(etree.tostring(xml), b"<root/>")

    def test_etree_remove_removes_comment_and_tail(self):
        text = "<root><!-- comentario -->texto sera removido tambem</root>"
        xml = etree.fromstring(text)
        comment = xml.xpath("//comment()")
        xml.remove(comment[0])
        self.assertEqual(etree.tostring(xml), b"<root/>")


class TestRemoveTag(unittest.TestCase):
    def test__remove_tag_keeps_text_after_element(self):
        text = "<root><a name='bla'/>texto a manter</root>"
        expected = b"<root>texto a manter</root>"
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        removed = _remove_tag(node)
        self.assertEqual(removed, "a")
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_tag_keeps_spaces_after_element(self):
        text = "<root> <a name='bla'/> texto a manter</root>"
        expected = b"<root>  texto a manter</root>"
        xml = etree.fromstring(text)
        node = xml.find(".//a")
        removed = _remove_tag(node)
        self.assertEqual(removed, "a")
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_tag_removes_xref(self):
        text = """<root><xref href="#corresp"><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/></xref></root>"""
        expected = b"""<root><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/></root>"""
        xml = etree.fromstring(text)
        node = xml.find(".//xref")
        _remove_tag(node)
        self.assertEqual(etree.tostring(xml), expected)

    def test__remove_tag_removes_a_href_home_and_keeps_asterisk(self):
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
        _remove_tag(nodes[1])
        self.assertEqual(etree.tostring(xml), expected)


class TestConversionToAnnex(unittest.TestCase):
    def test_convert_to_app(self):
        text = """<root>
        <a href="#anx01">Anexo 1</a>
        <p><a name="anx01" id="anx01"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg"/></p>
        </root>
        """

        xml = etree.fromstring(text)
        pl = ConvertElementsWhichHaveIdPipeline()
        text, xml = pl.CompleteElementAWithXMLTextPipe().transform((text, xml))
        text, xml = pl.DeduceAndSuggestConversionPipe().transform((text, xml))
        self.assertEqual(
            etree.tostring(xml),
            b"""<root>
        <a href="#anx01" xml_text="anexo 1" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1">Anexo 1</a>
        <p><a name="anx01" id="anx01" xml_text="anexo 1" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>""",
        )

        expected = b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p><app name="anx01" id="anx01" xml_text="anexo 1" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>"""
        text, xml = pl.ApplySuggestedConversionPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

        text, xml = pl.AssetElementFixPositionPipe().transform((text, xml))
        expected = b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p/><app name="anx01" id="anx01" xml_text="anexo 1" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>"""
        self.assertEqual(etree.tostring(xml), expected)

        text, xml = pl.AssetElementAddContentPipe().transform((text, xml))
        expected = b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p/><app name="anx01" id="anx01" xml_text="anexo 1" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1" status="identify-content"><p content-type="img"><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </app>
        </root>"""
        self.assertEqual(etree.tostring(xml), expected)

        expected = b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p/><app id="anx01"><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></app>
        </root>"""
        text, xml = pl.AssetElementFixPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)
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
        pl = html_pl.ConvertElementsWhichHaveIdPipe()
        text, xml = pl.transform((text, xml))
        self.assertIsNone(xml.find(".//table-wrap/img"))
        self.assertIsNotNone(xml.find(".//table-wrap/graphic"))

    def test_convert_to_table_wrap_which_has_two_internal_links(self):
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
        pl = pl_html.ConvertElementsWhichHaveIdPipe()
        raw, xml = pl.transform((raw, xml))
        self.assertIsNone(xml.find(".//table-wrap[@id]/img"))
        self.assertIsNotNone(xml.find(".//table-wrap[@id]/graphic"))
        self.assertIsNotNone(xml.find(".//table-wrap[@id]/label"))
        self.assertIsNone(xml.find(".//table-wrap[@id]/caption"))


class TestConversionToCorresp(unittest.TestCase):
    def test_convert_to_corresp(self):
        text = """<root>
        <a href="#back">*</a>
        <a name="home" id="home"/>
        <a name="back" id="back"/>
        <a href="#home">*</a> Corresponding author
        </root>"""
        expected_1 = b"""<root>
        <a href="#back" xml_text="*">*</a>

        <a name="back" id="back" xml_text="*"/>
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        </root>"""
        expected_2 = b"""<root>
        <xref ref-type="fn" rid="back">*</xref>

        <fn id="back"/>
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        </root>"""

        xml = etree.fromstring(text)
        pl = ConvertElementsWhichHaveIdPipeline()
        text, xml = pl.CompleteElementAWithNameAndIdPipe().transform((text, xml))
        text, xml = pl.CompleteElementAWithXMLTextPipe().transform((text, xml))
        text, xml = pl.EvaluateElementAToDeleteOrMarkAsFnLabelPipe().transform(
            (text, xml)
        )

        expected = b"""<root>
        <a href="#back" xml_text="*">*</a>

        <a name="back" id="back" xml_text="*"/>
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        </root>"""
        result = etree.tostring(xml)
        self.assertNotIn(b'<a href="#home">*</a>', result)
        self.assertIn(b'<a href="#back" xml_text="*">*</a>', result)
        self.assertIn(b'<a name="back" id="back" xml_text="*"/>', result)
        self.assertIn(
            b'<label href="#home" xml_text="*" label-of="back">*</label> Corresponding author',
            result,
        )

        text, xml = pl.DeduceAndSuggestConversionPipe().transform((text, xml))
        self.assertIn(
            b'<a name="back" id="back" xml_text="*" xml_tag="fn" xml_reftype="fn" xml_id="back" xml_label="*"/>',
            etree.tostring(xml),
        )

        text, xml = pl.ApplySuggestedConversionPipe().transform((text, xml))
        expected = b"""<root>
        <xref ref-type="fn" rid="back">*</xref>

        <fn name="back" id="back" xml_text="*" xml_tag="fn" xml_reftype="fn" xml_id="back" xml_label="*"/>
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        </root>"""
        result = etree.tostring(xml)
        self.assertIn(b'<xref ref-type="fn" rid="back">*</xref>', result)
        self.assertIn(
            b'<fn name="back" id="back" xml_text="*" xml_tag="fn" xml_reftype="fn" xml_id="back" xml_label="*"/>',
            result,
        )
        self.assertIn(
            b'<label href="#home" xml_text="*" label-of="back">*</label> Corresponding author',
            result,
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
        pl = ConvertElementsWhichHaveIdPipeline()

        text, xml = pl.CompleteElementAWithNameAndIdPipe().transform((text, xml))
        text, xml = pl.CompleteElementAWithXMLTextPipe().transform((text, xml))
        text, xml = pl.DeduceAndSuggestConversionPipe().transform((text, xml))
        _xml = etree.tostring(xml)
        self.assertIn(
            b'<a href="#fig01en" xml_text="figure 1" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1">Figure 1</a>',
            _xml,
        )
        self.assertIn(
            b'<a name="fig01en" id="fig01en" xml_text="figure 1" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1"/>',
            _xml,
        )
        self.assertIn(
            b'<img src="/img/revistas/jped/v86n3/en_a05fig01.gif" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1"/>',
            _xml,
        )
        text, xml = pl.ApplySuggestedConversionPipe().transform((text, xml))
        _xml = etree.tostring(xml)
        self.assertIn(b'<xref ref-type="fig" rid="fig01en">Figure 1</xref>', _xml)
        self.assertIn(
            b'<fig name="fig01en" id="fig01en" xml_text="figure 1" xml_tag="fig" xml_reftype="fig" xml_id="fig01en" xml_label="figure 1"/>',
            _xml,
        )
        text, xml = pl.AssetElementAddContentPipe().transform((text, xml))
        self.assertIsNotNone(xml.findall(".//fig/img"))
        text, xml = pl.ImgPipe().transform((text, xml))
        self.assertIsNotNone(xml.findall(".//fig/graphic"))


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
        text, xml = pipeline.SetupPipe().transform(text)
        pipes = (
            pipeline.SaveRawBodyPipe(pipeline),
            pipeline.DeprecatedHTMLTagsPipe(),
            pipeline.RemoveImgSetaPipe(),
            pipeline.RemoveOrMoveStyleTagsPipe(),
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
            pipeline.ConvertElementsWhichHaveIdPipe(),
            pipeline.TdCleanPipe(),
            pipeline.TableCleanPipe(),
            pipeline.BlockquotePipe(),
            pipeline.HrPipe(),
            pipeline.TagsHPipe(),
            pipeline.DispQuotePipe(),
            pipeline.GraphicChildrenPipe(),
            pipeline.FixBodyChildrenPipe(),
            pipeline.RemovePWhichIsParentOfPPipe(),
            pipeline.SanitizationPipe(),
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
        text, xml = pipeline.SetupPipe().transform(text)
        text, xml = pipeline.HTMLEscapingPipe().transform((text, xml))
        resultado_unicode = etree.tostring(xml, encoding="unicode")
        resultado_b = etree.tostring(xml)
        self.assertIn(b"&#233;poca", resultado_b)
        self.assertIn("época", resultado_unicode)
        self.assertIn("&amp;lt;", resultado_unicode)


class TestConvertElementsWhichHaveIdPipeline(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="S1234-56782018000100011")
        self.pipe = self.html_pl.ConvertElementsWhichHaveIdPipe()
        self.pl = ConvertElementsWhichHaveIdPipeline()

    def test_remove_thumb_img_pipe(self):
        text = """<root xmlns:xlink="http://www.w3.org/1999/xlink"><p><a href="/img/revistas/hoehnea/v37n3/a05img01.jpg"><img src="/img/revistas/hoehnea/v37n3/a05img01-thumb.jpg"/><br/> Anexo 1 - Clique para ampliar</a></p></root>"""
        expected = b"""<root xmlns:xlink="http://www.w3.org/1999/xlink"><p><a href="/img/revistas/hoehnea/v37n3/a05img01.jpg">Anexo 1<br/></a></p></root>"""
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
        text, xml = self.pl.CompleteElementAWithNameAndIdPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_anchor_and_internal_link_pipe(self):
        text = b"""<root>
        <a href="#anx01" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1">Anexo 1</a>
        <p><a name="anx01" id="anx01" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pl.ApplySuggestedConversionPipe().transform((text, xml))
        expected = b"""<root>
        <xref ref-type="app" rid="anx01">Anexo 1</xref>
        <p><app name="anx01" id="anx01" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        <p><img src="/img/revistas/trends/v33n3/a05tab01.jpg" xml_tag="app" xml_reftype="app" xml_id="anx01" xml_label="anexo 1"/></p>
        </root>"""
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_aname__removes_navigation_to_note_go_and_back(self):
        text = """<root><a href="#tx01">
            <graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/>
        </a><a name="tx01" id="tx01"/></root>"""

        raw, transformed = text, etree.fromstring(text)
        raw, transformed = self.pl.ApplySuggestedConversionPipe().transform(
            (raw, transformed)
        )
        node = transformed.find(".//xref")
        self.assertIsNone(node)
        node = transformed.find(".//a")
        self.assertIsNone(node)
        self.assertIsNone(transformed.find(".//graphic"))

    def test_pipe_asterisk_in_a_name(self):
        text = '<root><a name="*" id="*"/></root>'
        expected = b"<root/>"
        xml = etree.fromstring(text)
        text, xml = self.pl.ApplySuggestedConversionPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_aname__removes__ftn(self):
        text = """<root><a name="_ftnref19" title="" href="#_ftn2" id="_ftnref19"><sup>1</sup></a></root>"""
        raw, transformed = text, etree.fromstring(text)
        raw, transformed = self.pl.ApplySuggestedConversionPipe().transform(
            (raw, transformed)
        )
        node = transformed.find(".//xref")
        self.assertIsNone(node)
        node = transformed.find(".//a")
        self.assertIsNone(node)
        # self.assertIsNotNone(transformed.find(".//sup"))
        self.assertEqual(etree.tostring(transformed), b"<root/>")

    def test_convert_elements_which_have_id_pipeline_removes_some_elements(self):
        text = """<root>
        <a href="#nt1">1</a>
        <a name="xnt1"/>
        <a name="nt1"/>
        <a href="#xnt1">1</a> Nota bla bla
        </root>"""
        expected = b"""
        <root>
        <xref ref-type="fn" rid="nt1">1</xref>
        <fn id="nt1"><label>1</label><p>Nota bla bla</p></fn></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        nodes = xml.findall(".//fn")
        self.assertEqual(len(nodes), 1)
        nodes = xml.findall(".//fn")
        self.assertEqual(nodes[0].find("label").text, "1")
        self.assertEqual(nodes[0].find("p").text.strip(), "Nota bla bla")

        nodes = xml.findall(".//xref")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].text, "1")


class TestDeduceAndSuggestConversionPipe(unittest.TestCase):
    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.DeduceAndSuggestConversionPipe()
        self.inferer = Inferer()
        self.text = """
        <root>
        <p>
            <a href="#tab01">Tabela 1</a>
            <a href="#tab01">Tabela 1</a>
            <a name="tab01"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg">Figure 1</a>

            <a href="f02.jpg">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg">Figure 3</a>
            <a href="f03.jpg">3</a>
        </p>
        </root>
        """
        self.xml = etree.fromstring(self.text)
        self.text, self.xml = pl.CompleteElementAWithXMLTextPipe().transform(
            (self.text, self.xml)
        )
        self.document = Document(self.xml)
        self.texts, self.files = self.document.a_href_items

    def test_identify_data(self):
        nodes = self.xml.findall(".//a")
        img = self.xml.findall(".//img")
        self.assertEqual(
            self.document.a_names, {"tab01": (nodes[2], [nodes[0], nodes[1]])}
        )
        self.assertEqual(
            self.texts,
            {
                "tabela 1": ([nodes[0], nodes[1]], []),
                "figure 1": ([], [nodes[3]]),
                "figure 2": ([], [nodes[4]]),
                "figure 3": ([], [nodes[5], nodes[6]]),
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
                result = etree.tostring(node)
                expected = etree.tostring(expected_node[i])
                self.assertEqual(result, expected)

    def test_add_xml_attribs_to_a_href_from_text(self):
        expected = """
        <root>
        <p>
            <a href="#tab01" xml_text="tabela 1" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a href="#tab01" xml_text="tabela 1" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01" xml_label="tabela 1">Tabela 1</a>
            <a name="tab01" xml_text="tabela 1" />
            <img src="tabela.jpg"/>

            <a href="f01.jpg" xml_text="figure 1" xml_tag="fig" xml_reftype="fig" xml_id="f01" xml_label="figure 1">Figure 1</a>

            <a href="f02.jpg" xml_text="figure 2" xml_tag="fig" xml_reftype="fig" xml_id="f02" xml_label="figure 2">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg" xml_text="figure 3" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">Figure 3</a>
            <a href="f03.jpg" xml_text="figure 3" xml_tag="fig" xml_reftype="fig" xml_id="f03" xml_label="figure 3">3</a>
        </p>
        </root>
        """
        self.pipe._add_xml_attribs_to_a_href_from_text(self.texts)
        self._assert(expected, "a_href_from_text")

    def test_add_xml_attribs_to_a_name(self):
        expected = """
        <root>
        <p>
            <a href="#tab01" xml_text="tabela 1" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01">Tabela 1</a>
            <a href="#tab01" xml_text="tabela 1" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01">Tabela 1</a>
            <a name="tab01" xml_text="tabela 1" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg" xml_text="figure 1">Figure 1</a>

            <a href="f02.jpg" xml_text="figure 2">2</a>

            <img src="app.jpg"/>

            <a href="f03.jpg" xml_text="figure 3">Figure 3</a>
            <a href="f03.jpg" xml_text="figure 3">3</a>
        </p>
        </root>
        """
        self.pipe._add_xml_attribs_to_a_name(self.document.a_names)
        self._assert(expected, "a_names")

    def test_add_xml_attribs_to_a_href_from_file_paths(self):
        expected = """
        <root>
        <p>
            <a href="#tab01" xml_text="tabela 1">Tabela 1</a>
            <a href="#tab01" xml_text="tabela 1">Tabela 1</a>
            <a name="tab01" xml_text="tabela 1"/>
            <img src="tabela.jpg" xml_tag="table-wrap" xml_reftype="table" xml_id="tab01"/>

            <a href="f01.jpg" xml_text="figure 1" xml_tag="fig" xml_reftype="fig" xml_id="f01">Figure 1</a>

            <a href="f02.jpg" xml_text="figure 2" xml_tag="fig" xml_reftype="fig" xml_id="f02">2</a>

            <img src="app.jpg" xml_tag="app" xml_reftype="app" xml_id="app"/>

            <a href="f03.jpg" xml_text="figure 3" xml_tag="fig" xml_reftype="fig" xml_id="f03">Figure 3</a>
            <a href="f03.jpg" xml_text="figure 3" xml_tag="fig" xml_reftype="fig" xml_id="f03">3</a>
        </p>
        </root>
        """
        self.pipe._add_xml_attribs_to_a_href_from_file_paths(self.files)
        self._assert(expected, "file_paths")

    def test_add_xml_attribs_to_img(self):
        expected = """
        <root>
        <p>
            <a href="#tab01">Tabela 1</a>
            <a href="#tab01">Tabela 1</a>
            <a name="tab01"/>
            <img src="tabela.jpg"/>

            <a href="f01.jpg">Figure 1</a>

            <a href="f02.jpg">2</a>

            <img src="app.jpg" xml_tag="app" xml_reftype="app" xml_id="app"/>

            <a href="f03.jpg">Figure 3</a>
            <a href="f03.jpg">3</a>
        </p>
        </root>
        """
        self.pipe._add_xml_attribs_to_img(self.document.images)
        self._assert(expected, "images", ".//img")


class TestAHrefPipe(unittest.TestCase):
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
        self.pipe = self.pipeline.AHrefPipe()

    def test_a_href_pipe_create_ext_link_for_uri(self):
        expected = {
            "{http://www.w3.org/1999/xlink}href": "http://bla.org",
            "ext-link-type": "uri",
        }
        xml = etree.fromstring('<root><a href="http://bla.org">texto</a></root>')
        node = xml.find(".//a")

        self.pipe._create_ext_link(node)

        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))
        self.assertEqual(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "http://bla.org"
        )
        self.assertEqual(node.attrib.get("ext-link-type"), "uri")
        self.assertEqual(node.tag, "ext-link")
        self.assertEqual(node.text, "texto")
        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))

    def test_a_href_pipe___creates_email_element_with_href_attribute(self):
        expected = """<root>
        <p><ext-link ext-link-type="email" xlink:href="mailto:a@scielo.org">Enviar e-mail para A</ext-link></p>
        </root>"""
        text = """<root>
        <p><a href="mailto:a@scielo.org">Enviar e-mail para A</a></p>
        </root>"""
        xml = etree.fromstring(text)

        node = xml.find(".//a")
        self.pipe._create_email(node)

        self.assertEqual(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "mailto:a@scielo.org"
        )
        self.assertEqual(node.tag, "ext-link")
        self.assertEqual(node.get("ext-link-type"), "email")
        self.assertEqual(node.text, "Enviar e-mail para A")

    def test_a_href_pipe___creates_email_(self):
        expected = """<root>
        <p>Enviar e-mail para <email>a@scielo.org</email>.</p>
        </root>"""
        text = """<root>
        <p><a href="mailto:a@scielo.org">Enviar e-mail para a@scielo.org.</a></p>
        </root>"""
        xml = etree.fromstring(text)

        node = xml.find(".//a")
        self.pipe._create_email(node)
        p = xml.find(".//p")
        self.assertEqual(p.text, "Enviar e-mail para ")
        email = p.find("email")
        self.assertEqual(email.text, "a@scielo.org")
        self.assertEqual(email.tail, ".")

    def test_a_href_pipe___creates_ext_link_with_img(self):

        expected = """<root>
        <p><ext-link ext-link-type="email" xlink:href="mailto:a@scielo.org"><img src="mail.gif" /></ext-link></p>
        </root>"""
        text = """<root>
        <p><a href="mailto:a@scielo.org"><img src="mail.gif"/></a></p>
        </root>"""
        xml = etree.fromstring(text)

        node = xml.find(".//a")
        self.pipe._create_email(node)

        self.assertEqual(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "mailto:a@scielo.org"
        )
        self.assertEqual(node.tag, "ext-link")
        self.assertEqual(node.get("ext-link-type"), "email")
        self.assertIsNotNone(node.find("img"))

    def test_a_href_pipe___creates_email(self):
        text = """<root>
        <p><a href="mailto:a@scielo.org">a@scielo.org</a></p>
        </root>"""
        raw, transformed = self._transform(text, self.pipe)

        node = transformed.find(".//email")
        self.assertEqual(node.text, "a@scielo.org")
        self.assertEqual(node.tag, "email")

    def test_a_href_pipe___create_email_mailto_empty(self):
        text = """<root><a href="mailto:">sfpyip@hku.hk</a>). Correspondence should be addressed to Dr Yip at this address.</root>"""
        raw, transformed = self._transform(text, self.pipe)

        node = transformed.find(".//email")
        self.assertEqual(node.text, "sfpyip@hku.hk")
        self.assertEqual(
            node.tail,
            "). Correspondence should be addressed to Dr Yip at this address.",
        )

    def test_a_href_pipe__hiperlink(self):
        text = [
            "<root>",
            '<p><a href="https://new.scielo.br"/></p>',
            '<p><a href="//www.google.com"><img src="mail.gif"/></a></p>',
            '<p><a href="ftp://www.bbc.com">BBC</a></p>',
            '<p><a href="../www.bbc.com">Enviar <b>e-mail para</b> mim</a></p>',
            "</root>",
        ]
        text = "".join(text)
        raw, transformed = self._transform(text, self.pipe)

        nodes = transformed.findall(".//ext-link")
        self.assertEqual(len(nodes), 3)
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

    def test_a_href_pipe_create_ext_link_for_bad_uri_format(self):
        expected = {
            "{http://www.w3.org/1999/xlink}href": "www.bla.org",
            "ext-link-type": "uri",
        }
        text = '<root><body><a href="www.bla.org">texto</a></body></root>'
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        node = xml.find(".//ext-link")

        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))
        self.assertEqual(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "www.bla.org"
        )
        self.assertEqual(node.attrib.get("ext-link-type"), "uri")
        self.assertEqual(node.tag, "ext-link")
        self.assertEqual(node.text, "texto")
        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))

    def test_a_href_pipe_create_ext_link_for_bad_uri_format_which_starts_with_http(
        self,
    ):
        expected = {
            "{http://www.w3.org/1999/xlink}href": "http//www.bla.org",
            "ext-link-type": "uri",
        }
        text = '<root><body><a href="http//www.bla.org">texto</a></body></root>'
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        node = xml.find(".//ext-link")
        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))
        self.assertEqual(
            node.attrib.get("{http://www.w3.org/1999/xlink}href"), "http//www.bla.org"
        )
        self.assertEqual(node.attrib.get("ext-link-type"), "uri")
        self.assertEqual(node.tag, "ext-link")
        self.assertEqual(node.text, "texto")
        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))


class TestImgPipe(unittest.TestCase):
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
        self.html_pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        self.pipeline = ConvertElementsWhichHaveIdPipeline()

    def test_pipe_img(self):
        text = '<root><img align="x" src="a04qdr04.gif"/><img align="x" src="a04qdr08.gif"/></root>'
        raw, transformed = self._transform(text, self.pipeline.ImgPipe())

        nodes = transformed.findall(".//graphic")

        self.assertEqual(len(nodes), 2)
        for node, href in zip(nodes, ["a04qdr04.gif", "a04qdr08.gif"]):
            with self.subTest(node=node):
                self.assertEqual(
                    href, node.attrib["{http://www.w3.org/1999/xlink}href"]
                )
                self.assertEqual(len(node.attrib), 1)


class TestConvertRemote2LocalPipe(unittest.TestCase):
    def test_transform_imports_html_content(self):
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text = """<root><body>
        <p>
        <a href="/img/revistas/eq/v33n3/html/a05tab01.htm">Tables 1-5</a>
        </p>
        </body></root>"""
        xml = etree.fromstring(text)

        text, xml = pipeline.ConvertRemote2LocalPipe().transform((text, xml))
        self.assertEqual(xml.find(".//a[@name]").get("name"), "a05tab01")

        self.assertEqual(xml.find(".//a[@href]").get("href"), "#a05tab01")

    def test_transform_makes_remote_image_local(self):
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text = """<root><body>
        <p>
        <a href="/img/revistas/rbs/v28n3/05t1.gif">Table 1</a>
        </p>
        </body></root>"""
        xml = etree.fromstring(text)

        text, xml = pipeline.ConvertRemote2LocalPipe().transform((text, xml))
        self.assertEqual(xml.find(".//a[@name]").get("name"), "05t1")
        self.assertEqual(
            xml.find(".//a[@name]/img").get("src"), "/img/revistas/rbs/v28n3/05t1.gif"
        )
        self.assertEqual(xml.find(".//a[@href]").get("href"), "#05t1")

    def test_transform_imports_html_content_once(self):
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text = """<root><body>
        <p>
        <a href="/img/revistas/eq/v33n3/html/a05tab01.htm">Tables 1-5</a>
        </p>
        <p>
        <a href="/img/revistas/eq/v33n3/html/a05tab01.htm">Tables 1-5</a>
        </p>
        </body></root>"""
        xml = etree.fromstring(text)

        text, xml = pipeline.ConvertRemote2LocalPipe().transform((text, xml))
        self.assertEqual(xml.find(".//a[@name]").get("name"), "a05tab01")
        self.assertEqual(len(xml.findall(".//a[@name]")), 5)
        self.assertEqual(len(xml.findall(".//a[@href]")), 2)

        a_href_items = xml.findall(".//a[@href]")
        self.assertEqual(a_href_items[0].get("href"), "#a05tab01")
        self.assertEqual(a_href_items[1].get("href"), "#a05tab01")

    @patch(
        "documentstore_migracao.utils.convert_html_body.Remote2LocalConversion._get_html_body"
    )
    def test_transform_preserve_original_a_href_if_html_not_found(
        self, mk_get_html_body
    ):
        mk_get_html_body.return_value = None
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text = """<root><body>
        <p>
        <a href="/img/revistas/az/v99nspe/html/a10tab02.htm">Table 2</a>
        </p>
        </body></root>"""
        xml = etree.fromstring(text)

        text, xml = pipeline.ConvertRemote2LocalPipe().transform((text, xml))
        a_href_items = xml.findall(".//a[@href]")
        self.assertEqual(
            a_href_items[0].get("href"), "/img/revistas/az/v99nspe/html/a10tab02.htm"
        )
        self.assertEqual(a_href_items[0].get("link-type"), "asset-not-found")

    def test_transform_removes_repeated_imported_images(self):
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011")
        text = """<root><body>
        <p>
        <a href="/img/revistas/eq/v33n3/html/a05tab01.htm">Tables 1-5</a>
        </p>
        <p>
        <a href="/img/revistas/eq/v33n3/html/tab01.jpg">Table 1</a>
        </p>
        </body></root>"""
        xml = etree.fromstring(text)

        def stub_get_html_body(ign, html_file):
            return etree.fromstring(
                """<body>
                    <img src="/img/revistas/eq/v33n3/html/tab01.jpg"/>
                </body>
            """
            )

        with patch(
            "documentstore_migracao.utils.convert_html_body.Remote2LocalConversion._get_html_body",
            new=stub_get_html_body,
        ):
            text, xml = pipeline.ConvertRemote2LocalPipe().transform((text, xml))

            a_name_items = xml.findall(".//a[@name]")
            self.assertEqual(len(a_name_items), 2)
            self.assertEqual(a_name_items[0].get("name"), "a05tab01")
            self.assertEqual(a_name_items[1].get("name"), "tab01")

            a_href_items = xml.findall(".//a[@href]")
            self.assertEqual(len(a_href_items), 2)
            self.assertEqual(a_href_items[0].get("href"), "#a05tab01")
            self.assertEqual(a_href_items[1].get("href"), "#tab01")

            img = xml.findall(".//img[@src]")
            self.assertEqual(len(img), 1)
            self.assertEqual(img[0].get("src"), "/img/revistas/eq/v33n3/html/tab01.jpg")


class TestCompleteElementAWithXMLTextPipe(unittest.TestCase):
    def test_add_xml_text_to_a_href_in_p_identifies_table_sequence(self):
        text = """<root>
        <p><a href="#tab1">Tabelas 1</a> e <a href="#tab2">2</a></p>
        </root>"""
        xml = etree.fromstring(text)
        pipeline = ConvertElementsWhichHaveIdPipeline()
        text, xml = pipeline.CompleteElementAWithXMLTextPipe().transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(b'<a href="#tab1" xml_text="tabelas 1">Tabelas 1</a>', result)
        self.assertIn(b'<a href="#tab2" xml_text="tabelas 2">2</a>', result)

    def test_add_xml_text_to_a_href_in_p_identifies_table_and_fn(self):
        text = """<root>
        <p><a href="#tab3">Tabela 3</a> e <a href="#f2">2</a></p>
        </root>"""
        xml = etree.fromstring(text)
        pipeline = ConvertElementsWhichHaveIdPipeline()
        text, xml = pipeline.CompleteElementAWithXMLTextPipe().transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(b'<a href="#tab3" xml_text="tabela 3">Tabela 3</a>', result)
        self.assertIn(b'<a href="#f2" xml_text="2">2</a>', result)

    def test_add_xml_text_to_other_a_update_a_name(self):
        text = """<root>
        <p><a href="#tab1">Tabelas 1</a> e <a href="#tab2">2</a></p>
        <p><a name="tab1"/>Tabela 1</p>
        <p><a name="tab2"/>Tabela 2</p>
        </root>"""
        xml = etree.fromstring(text)
        pipeline = ConvertElementsWhichHaveIdPipeline()
        text, xml = pipeline.CompleteElementAWithXMLTextPipe().transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(b'<a href="#tab1" xml_text="tabelas 1">Tabelas 1</a>', result)
        self.assertIn(b'<a href="#tab2" xml_text="tabelas 2">2</a>', result)
        self.assertIn(b'<a name="tab1" xml_text="tabelas 1"/>', result)
        self.assertIn(b'<a name="tab2" xml_text="tabelas 2"/>', result)


class TestFnPipe_AddContentToEmptyFn(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="pid")
        self.pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = self.pl.FnPipe_AddContentToEmptyFn()

    def test_transform_moves_italic(self):
        text = """<root><fn id="nt01"/>
           <italic>Isso é conhecido pelos pesquisadores como</italic>
         </root>"""
        expected = """<root><fn id="nt01">
            <italic>Isso é conhecido pelos pesquisadores como</italic></fn>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertIn("Isso", fn.find("italic").text)

    def test_transform_moves_text_children(self):
        text = """<root><fn id="nt01"/>**
           <italic>Isso é conhecido pelos pesquisadores como</italic>
         </root>"""
        expected = """<root><fn id="nt01">**
            <italic>Isso é conhecido pelos pesquisadores como</italic></fn>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        node = xml.find(".//fn")
        self.assertIn("**", node.text)
        self.assertIn("Isso", node.find("italic").text)

    def test_transform_moves_items_until_p_is_found(self):
        text = """<root><fn id="nt01"/>**
           <p><italic>Isso é conhecido pelos pesquisadores como</italic> .</p>
           <p/> .
           <p>Este texto não fará parte de fn</p>
         </root>"""
        expected = """<root><fn id="nt01">**
            <p><italic>Isso é conhecido pelos pesquisadores como</italic> .</p></fn>
            <p/> .
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertEqual(
            fn.find("p/italic").text, "Isso é conhecido pelos pesquisadores como"
        )
        self.assertEqual(fn.find("p/italic").tail.strip(), ".")
        self.assertEqual(len(fn.findall("p")), 1)

    def test_transform_includes_break(self):
        text = """<root><fn id="nt01"/>**
           <italic>Isso é conhecido pelos pesquisadores como</italic>
           <br/>Email: a@x.org
         </root>"""
        expected = """<root><fn id="nt01">**
            <italic>Isso é conhecido pelos pesquisadores como</italic>
            <br/>Email: a@x.org</fn>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        node = xml.find(".//fn")
        self.assertIn("**", node.text)
        self.assertIn("Isso", node.find("italic").text)
        self.assertIn("Email", node.find("br").tail)

    def test_transform_moves_items_until_another_fn_is_found(self):
        text = """<root><fn id="nt01"/>**
           <p><italic>Isso é conhecido pelos pesquisadores como</italic> .</p><fn id="nt02"/><label>***</label>
            <p>Isso é outra nota de rodapé.</p>
            <p/> .
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.findall(".//fn")
        self.assertEqual(
            fn[0].find("p/italic").text, "Isso é conhecido pelos pesquisadores como"
        )
        self.assertEqual(fn[0].find("p/italic").tail.strip(), ".")
        self.assertIsNotNone(len(fn[0].getchildren()), 1)
        self.assertEqual(fn[1].find("label").text, "***")
        self.assertEqual(fn[1].find("p").text, "Isso é outra nota de rodapé.")

    def test_transform_do_not_move_items_inside_because_fn_is_found(self):
        text = """<root><fn id="nt01"/>**
           <p><italic>Isso é conhecido pelos pesquisadores como</italic> .<fn id="nt02"/><label>***</label>
            <p>Isso é outra nota de rodapé.</p>
            <p/></p> .
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.findall(".//fn")
        self.assertIsNotNone(len(fn[0].getchildren()), 0)
        self.assertEqual(fn[1].find("label").text, "***")
        self.assertEqual(fn[1].find("p").text, "Isso é outra nota de rodapé.")


class TestFnIdentifyLabelAndPPipe(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="pid")
        self.pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = self.pl.FnIdentifyLabelAndPPipe()

    def test_transform_creates_p(self):
        text = """<root><fn>TEXTO NOTA</fn></root>"""
        expected = b"""<root><fn><p>TEXTO NOTA</p></fn></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertEqual(fn.find("p").text, "TEXTO NOTA")
        self.assertIsNone(fn.find("label"))

    def test_transform_creates_label_and_p(self):
        text = """<root><fn>** TEXTO NOTA</fn></root>"""
        expected = b"""<root><fn><label>**</label><p>TEXTO NOTA</p></fn></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertEqual(fn.find("p").text, "TEXTO NOTA")
        self.assertEqual(fn.find("label").text, "**")

    def test_transform__creates_label_from_style_tag(self):
        text = """<root><fn><sup>**</sup> TEXTO NOTA</fn></root>"""
        expected = (
            b"""<root><fn><label><sup>**</sup></label><p> TEXTO NOTA</p></fn></root>"""
        )
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertEqual(fn.find("p").text, " TEXTO NOTA")
        self.assertEqual(fn.find("label/sup").text, "**")

    def test__creates_p(self):
        text = """<root><fn id="nt01">
           <li>Isso é conhecido pelos pesquisadores como</li></fn>
         </root>"""
        expected = """<root><fn id="nt01"><p>
            <li>Isso é conhecido pelos pesquisadores como</li></p></fn>
        </root>"""

        xml = etree.fromstring(text)

        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertEqual(
            fn.find("p/li").text, "Isso é conhecido pelos pesquisadores como"
        )
        self.assertIsNone(fn.find("p/li").tail)
        self.assertIsNone(fn.find("label"))


class TestFnPipe(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="pid")

    def test__creates_fn_with_some_paragraphs(self):
        text = """<root>
          <p><fn id="nt"></fn>
          <bold>Correspondence to:</bold>
          <br/>
          Maria Auxiliadora Prolungatti Cesar
          <br/>
          Serviço de Clínica Cirúrgica do Hospital Universitário de Taubaté
          <br/>
          Avenida Granadeiro Guimarães, 270
          <br/>
          CEP: 12100-000 – Taubaté (SP), Brazil.
          <br/>
          E mail:
          <a href="mailto:prolungatti@uol.com.br">prolungatti@uol.com.br</a>
          </p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.html_pl.AHrefPipe().transform((text, xml))
        text, xml = self.html_pl.BRPipe().transform((text, xml))
        text, xml = self.html_pl.ConvertElementsWhichHaveIdPipe().transform((text, xml))
        text, xml = self.html_pl.RemoveInvalidBRPipe().transform((text, xml))
        text, xml = self.html_pl.BRPipe().transform((text, xml))
        text, xml = self.html_pl.BR2PPipe().transform((text, xml))

        p = xml.findall(".//fn/p")
        self.assertEqual(xml.find(".//fn/label/bold").text, "Correspondence to:")
        self.assertEqual(p[0].text.strip(), "Maria Auxiliadora Prolungatti Cesar")
        self.assertEqual(
            p[1].text.strip(),
            "Serviço de Clínica Cirúrgica do Hospital Universitário de Taubaté",
        )
        self.assertEqual(p[2].text.strip(), "Avenida Granadeiro Guimarães, 270")
        self.assertEqual(p[3].text.strip(), "CEP: 12100-000 – Taubaté (SP), Brazil.")
        self.assertEqual(p[5].find("email").text, "prolungatti@uol.com.br")

    def test_creates_fn_list(self):
        text = """
         <root>
         <p><b>C.T.L.S. Ghidini<sup>I, </sup>
         <a href="#nt"><sup>*</sup></a>;
         A.R.L. Oliveira<sup>II</sup>; M. Silva<sup>III</sup></b></p>

         <p>Conforme a nota 1<a href="#nt01">1</a></p>
         <p>Conforme a nota 2<a href="#nt02">2</a></p>
         <p>Conforme a nota 3<a href="#nt03">3</a></p>
         <p><a name="nt"></a><a href="#tx">*</a>
         Autor correspondente: Carla Ghidini    <br/>
         <a name="nt01"></a>
         <a href="#tx01">1</a> O número de condição de uma matriz <I>M </I>é definido por: &#954;<sub>2</sub>(<i>M</i>) = ||<I>M</I>||<sub>2</sub>||<I>M</I><sup>&#150;1</sup>||<sub>2</sub>.
         <br/>
         <a name="nt02"></a><a href="#tx02">2</a> <i>T</i><sub><I>k</I>+1,<I>k </I></sub>= <img src="/img/revistas/tema/v15n3/a05img16.jpg" align="absmiddle"/>, em que &#945;<I><sub>j</sub> = h<sub>ij</sub></I>, &#946;<I><sub>j</sub> = h</I><sub><i>j</i>&#150;1,<I>j</I></sub>.    <br/>
         <a name="nt03"></a><a href="#tx03">3</a> A norma-A é definida como: ||<i>w</i>||<i><sub>A</sub> </i>= <img src="/img/revistas/tema/v15n3/a05img15.jpg" align="absmiddle"/>.</p></root>"""

        xml = etree.fromstring(text)
        text, xml = self.html_pl.ConvertElementsWhichHaveIdPipe().transform((text, xml))
        fn = xml.findall(".//fn")
        self.assertEqual(fn[0].find("label").text, "*")
        self.assertEqual(fn[1].find("label").text, "1")
        self.assertEqual(fn[2].find("label").text, "2")
        self.assertEqual(fn[3].find("label").text, "3")
        self.assertIn("Autor correspondente", fn[0].find("p").text)
        self.assertIn("O número de condição", fn[1].find("p").text)
        self.assertIn("T", fn[2].find("p/i").text)
        self.assertIn("A norma-A", fn[3].find("p").text)

    def test_convert_elements_which_have_id_pipe_for_asterisk_corresponding_author(
        self,
    ):
        text = """<root><big>Peter M. Gaylarde; Christine C. Gaylarde
        <a href="#back"><sup>*</sup></a></big>
        <a name="back"></a><a href="#home">*</a> Corresponding author.
        Mailing Address:
        MIRCEN, Departamento de Solos, UFRGS, Caixa Postal 776, CEP 90001-970,
        Porto Alegre, RS, Brasil. Fax (+5551) 316-6029.
        Email
        <a href="mailto:chrisg@vortex.ufrgs.br">chrisg@vortex.ufrgs.br</a>
        </root>
        """
        expected = b"""<root><big>Peter M. Gaylarde; Christine C. Gaylarde
        <xref ref-type="fn" rid="back"><sup>*</sup></xref></big>
        <fn id="back"><label>*</label><p> Corresponding author.
        Mailing Address:
        MIRCEN, Departamento de Solos, UFRGS, Caixa Postal 776, CEP 90001-970,
        Porto Alegre, RS, Brasil. Fax (+5551) 316-6029.
        Email
        <email>chrisg@vortex.ufrgs.br</email>
        </p></fn></root>"""
        xml = etree.fromstring(text)
        text, xml = self.html_pl.AHrefPipe().transform((text, xml))
        text, xml = self.html_pl.ConvertElementsWhichHaveIdPipe().transform((text, xml))
        self.assertEqual(xml.find(".//xref/sup").text, "*")
        self.assertEqual(xml.find(".//fn/label").text, "*")
        self.assertEqual(xml.find(".//fn/p/email").text, "chrisg@vortex.ufrgs.br")
        self.assertIn("Corresponding author", xml.find(".//fn/p").text, "*")


class TestSwitchElementsAPipe(unittest.TestCase):
    def test_switches_elements_a(self):
        text = """<root>
        <body>
            <a href="#top2" xml_text="**">**</a>
            <a name="back2"/> Amostra depositada na Coleção
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = (
            ConvertElementsWhichHaveIdPipeline()
            .SwitchElementsAPipe()
            .transform((text, xml))
        )
        a = xml.findall(".//a")
        self.assertIn("Amostra depositada na Coleção", a[1].tail)
        self.assertEqual("#top2", a[1].get("href"))
        self.assertEqual("back2", a[0].get("name"))


class TestCompleteElementAWithXMLTextPipe(unittest.TestCase):
    def test_add_xml_text_to_a_href_in_p_identifies_table_sequence(self):
        text = """<root>
        <p><a href="#tab1">Tabelas 1</a> e <a href="#tab2">2</a></p>
        </root>"""
        xml = etree.fromstring(text)
        pipeline = ConvertElementsWhichHaveIdPipeline()
        text, xml = pipeline.CompleteElementAWithXMLTextPipe().transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(b'<a href="#tab1" xml_text="tabelas 1">Tabelas 1</a>', result)
        self.assertIn(b'<a href="#tab2" xml_text="tabelas 2">2</a>', result)

    def test_add_xml_text_to_a_href_in_p_identifies_table_and_fn(self):
        text = """<root>
        <p><a href="#tab3">Tabela 3</a> e <a href="#f2">2</a></p>
        </root>"""
        xml = etree.fromstring(text)
        pipeline = ConvertElementsWhichHaveIdPipeline()
        text, xml = pipeline.CompleteElementAWithXMLTextPipe().transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(b'<a href="#tab3" xml_text="tabela 3">Tabela 3</a>', result)
        self.assertIn(b'<a href="#f2" xml_text="2">2</a>', result)

    def test_add_xml_text_to_other_a_update_a_name(self):
        text = """<root>
        <p><a href="#tab1">Tabelas 1</a> e <a href="#tab2">2</a></p>
        <p><a name="tab1"/>Tabela 1</p>
        <p><a name="tab2"/>Tabela 2</p>
        </root>"""
        xml = etree.fromstring(text)
        pipeline = ConvertElementsWhichHaveIdPipeline()
        text, xml = pipeline.CompleteElementAWithXMLTextPipe().transform((text, xml))
        result = etree.tostring(xml)
        self.assertIn(b'<a href="#tab1" xml_text="tabelas 1">Tabelas 1</a>', result)
        self.assertIn(b'<a href="#tab2" xml_text="tabelas 2">2</a>', result)
        self.assertIn(b'<a name="tab1" xml_text="tabelas 1"/>', result)
        self.assertIn(b'<a name="tab2" xml_text="tabelas 2"/>', result)


class TestTablePipe(unittest.TestCase):
    def setUp(self):
        self.pipe = ConvertElementsWhichHaveIdPipeline().TablePipe()

    def test_table_must_be_child_of_table_wrap(self):
        text = """<root>
        <p>
            <table-wrap><p>Texto <table/></p></table-wrap>
        </p>
        </root>"""
        expected = """<root>
        <p>
            <table-wrap><p>Texto </p><table/></table-wrap>
        </p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIn(
            b"<table-wrap><p>Texto </p><table/></table-wrap>", etree.tostring(xml)
        )

    def test_table_in_fig_must_be_converted_to_array(self):
        text = """<root>
        <p>
            <fig><p>Texto <table/></p></fig>
        </p>
        </root>"""
        expected = """<root>
        <p>
            <fig><p>Texto </p><array/></fig>
        </p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIn(
            b"<fig><p>Texto </p><array><tbody/></array></fig>", etree.tostring(xml)
        )

    def test_table_which_is_not_table_wrap_child_must_be_converted_to_array_and_create_tbody(
        self,
    ):
        text = """<root>
        <table>
        <tr valign="bottom">
        <td align="left">3</td>
        <td align="char" char="." charoff="35%">14.4411</td>
        <td align="center">
        <graphic id="g14"/></td>
        <td align="char" char="." charoff="35%">14.4411</td>
        <td align="center">
        <graphic id="g15"/></td>
        <td align="char" char="." charoff="35%">14.4414</td>
        <td align="center">
        <graphic id="g16"/></td>
        <td align="char" char="." charoff="35%">14.4414</td>
        <td align="center">
        <graphic id="g17"/></td>
        </tr>
        </table>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find("array/tbody"))
        self.assertIsNone(xml.find(".//table"))

    def test_table_which_is_not_table_wrap_child_must_be_converted_to_array(self):
        text = """<root>
        <table>
        <tbody>
        <tr valign="bottom">
        <td align="left">3</td>
        <td align="char" char="." charoff="35%">14.4411</td>
        <td align="center">
        <graphic id="g14"/></td>
        <td align="char" char="." charoff="35%">14.4411</td>
        <td align="center">
        <graphic id="g15"/></td>
        <td align="char" char="." charoff="35%">14.4414</td>
        <td align="center">
        <graphic id="g16"/></td>
        <td align="char" char="." charoff="35%">14.4414</td>
        <td align="center">
        <graphic id="g17"/></td>
        </tr>
        </tbody>
        </table>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find("array/tbody"))
        self.assertIsNone(xml.find(".//table"))


class TestSupplementaryMaterial(unittest.TestCase):
    def setUp(self):
        self.pipe = ConvertElementsWhichHaveIdPipeline().SupplementaryMaterialPipe()

    def test_a_href_generates_supplementary_material(self):
        """
        <supplementary-material id="S1" xmlns:xlink="http://www.w3.org/1999/xlink"
        xlink:title="local_file" xlink:href="1471-2105-1-1-s1.pdf"
        mimetype="application/pdf">
        <label>Additional material</label>
        <caption>
        <p>Supplementary PDF file supplied by authors.</p>
        </caption>
        </supplementary-material>
        <p>RNAPs seem to have arisen twice in evolution
        (see the <inline-supplementary-material
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xlink:title="local_file" xlink:href="timeline">
        Timeline</inline-supplementary-material>). A large
        family of multisubunit RNAPs includes bacterial
        enzymes, archeal enzymes, eukaryotic nuclear RNAPs,
        plastid-encoded chloroplast RNAPs, and RNAPs from
        some eukaryotic viruses. ...</p>
        """
        text = """<root>
        <p><bold>Supplementary Information</bold></p>
        <p></p>
        <p>The supplementary material is available in pdf:
        [<a href="/pdf/qn/v36n3/a05ms01.pdf" link-type="pdf"
        xml_text="supplementary material">Supplementary material</a>]</p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        inline_supplement_material = xml.find(".//inline-supplementary-material")
        self.assertEqual(
            inline_supplement_material.get("{http://www.w3.org/1999/xlink}href"),
            "/pdf/qn/v36n3/a05ms01.pdf",
        )
        self.assertEqual(inline_supplement_material.text, "Supplementary material")
        self.assertIsNone(inline_supplement_material.find(".//a"))


class TestRemoveReferencesFromBody(unittest.TestCase):
    def test_remove_references_from_body_removes_references_from_body(self):
        text = """
        <body>
        <p></p>
        <p></p>
        <p><b>REFERENCES</b></p>
        <!-- ref --><p>7. Endean ED, Schwarcz TH, Barker DE, Munfakh NA, Wilson-Neely R, Hyde GL. Hip disarticulation: factors affecting outcome. J Vasc Surg.1991:398-404.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004773&amp;pid=S1646-706X201900020000200007&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>8. Remes L, Isoaho R, Vahlberg T, Viitanen M, Rautava P. Predictors for institutionalization and prosthetic ambulation after major lower extremity amputation during an eight-year follow-up. Aging Clin Exp Res.2009:129-135.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004775&amp;pid=S1646-706X201900020000200008&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>10. Moura D, Garruço A. Desarticulação da anca - Análise de uma série e revisão da literatura. Rev Bras Ortop, 2016: 1-5.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004778&amp;pid=S1646-706X201900020000200010&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>11. Dénes Z, Till A. Rehabilitation of patients after hipdisarticulation. Arch Orthop Trauma Surg. 1997:498-499.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004780&amp;pid=S1646-706X201900020000200011&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>12. Fenelon GC, Von Foerster G, Engelbrecht E. Disarticulation ofthe hip as a result of failed arthroplasty. A series of 11 cases. J Bone Joint Surg Br 1980:441-446.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004782&amp;pid=S1646-706X201900020000200012&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>13. Jain R, Grimer RJ, Carter SR, Tillman RM, Abudu AA. Outcome after disarticulation of the hip for sarcomas. Eur J Surg Oncol. 2005:1025-1028.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004784&amp;pid=S1646-706X201900020000200013&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>14. Daigeler A, Lehnhardt M, Khadra A, Hauser J, Steinstraesser L,Langer S, et al. Proximal major limb amputations - a retrospective analysis of 45 oncological cases. World J Surg Oncol. 2009:1-10.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004786&amp;pid=S1646-706X201900020000200014&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>15. Ebrahimzadeh MH, Kachooei AR, Soroush MR, HasankhaniEG, Razi S, Birjandinejad A. Long-term clinical outcomes ofwar-related hip disarticulation and transpelvic amputation. J Bone Joint Surg Am. 2013:1-6.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004788&amp;pid=S1646-706X201900020000200015&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        <!-- ref --><p>16. Zalavras CG, Rigopoulos N, Ahlmann E, Patzakis MJ. Hipdisarticulation for severe lower extremity infections. Clin Orthop Relat Res. 2009:1721-1726.            [&#160;<a href="javascript:void(0);" onclick="javascript: window.open('/scielo.php?script=sci_nlinks&amp;ref=004790&amp;pid=S1646-706X201900020000200016&amp;lng=en','','width=640,height=500,resizable=yes,scrollbars=1,menubar=yes,');">Links</a>&#160;]<!-- end-ref --></p>
        </body>
        """
        article_text = """
        <article>
            <back>
                <ref>7</ref>
                <ref>8</ref>
                <ref>10</ref>
                <ref>11</ref>
                <ref>12</ref>
                <ref>13</ref>
                <ref>14</ref>
                <ref>15</ref>
                <ref>16</ref>
            </back>
        </article>
        """
        article = etree.fromstring(article_text)
        ref_items = article.findall(".//ref")

        xml = etree.fromstring(text)
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011", ref_items=ref_items)
        text, xml = pipeline.RemoveReferencesFromBodyPipe(pipeline).transform(
            (text, xml)
        )
        self.assertEqual(len(xml.findall(".//p")), 2)

    def test_remove_references_from_body_does_not_remove_any_paragraph(self):
        text = """
        <body>
        <p><b>REFERENCES</b></p>

        <!-- ref -->
        <p align="LEFT"><font color="000000">1. Vengrenovitch, R.D. <i>Acta Metall.</i>, v. 30, p. 1079-1086, 1982. </font>
        <!-- end-ref -->
        <!-- ref --></p>
        <p align="LEFT"><font color="000000">2. Lameiras, F.S. <i>Scripta Metall.</i>, v. 28, p. 1435-1440, 1993. </font>
        <!-- end-ref -->
        <!-- ref --></p>
        <p align="LEFT"><font color="000000">3. Rivier, N.; Lissowski, A. <i>J. Phys. A: Math. Gen.</i>, n. 15, p. L143-L148, 1982. </font>
        <!-- end-ref -->
        <!-- ref --></p>
        <p align="LEFT"><font color="000000">4. Rivier, N. <i>Phil. Mag. B</i>, n. 52, p. 795, 1985. </font>
        <!-- end-ref -->
        <!-- ref --></p>
        <p align="LEFT"><font color="000000">5. Hunderi, O.; Ryum, N. <i>Acta Metall.</i>, v. 29, p. 1737-1745, 1981. </font>
        <!-- end-ref -->
        <!-- ref --></p>
        <p align="LEFT"><font color="000000">6. Barnsley, M. <i>Fractals Everywhere</i>, Academic Press, Inc., San Diego, Ca-USA, 1988. </font>
        <!-- end-ref -->
        <!-- ref --></p>
        <p align="LEFT"><font color="000000">7. Rhines, F.N.; K.R. Craig. <i>Metallurgical Trans.</i>, v. 5, p. 413-425, 1974. </font>
        <!-- end-ref --> </p></body>
        """
        article_text = """
        <article>
            <back>
                <ref>1</ref>
                <ref>2</ref>
                <ref>3</ref>
                <ref>40</ref>
                <ref>5</ref>
                <ref>6</ref>
                <ref>7</ref>
                <ref>8</ref>
            </back>
        </article>
        """
        article = etree.fromstring(article_text)
        ref_items = article.findall(".//ref")

        xml = etree.fromstring(text)
        pipeline = HTML2SPSPipeline(pid="S1234-56782018000100011", ref_items=ref_items)
        text, xml = pipeline.RemoveReferencesFromBodyPipe(pipeline).transform(
            (text, xml)
        )
        self.assertEqual(len(xml.findall(".//p")), 8)


class TestAssetThumbnailInLayoutTableAndLinkInThumbnail(unittest.TestCase):

    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.AssetThumbnailInLayoutTableAndLinkInThumbnail()

    def test_transform_converts_thumbnail_table_into_simpler_structure(self):
        text = """<root xmlns:xlink="http://www.w3.org/1999/xlink">
        <table border="0">
            <tr align="left" valign="top">
            <td>
            <a href="#472i01" link-type="internal">
            <img src="/img/revistas/bjmbr/v43n10/472i01peq.jpg" border="2"/>
        </a>
        </td> <td> <p align="left">
          <a name="Fig1" id="Fig1"/>Figure 1. Concentration of IL-6 (pg/10<sup>6 </sup>cells) produced by the suspension of plasmacytoid dendritic cells (pDC). Concentration (Conc.) 1: 20 IU/mL penicillin, 5 µg/mL vancomycin, 5 µg/mL amoxicillin, 75 ng/mL anti-FcεRI/mL, and 100 nM CpG. Concentration 2: 200 IU/mL penicillin, 50 µg/mL vancomycin, and 50 µg/mL amoxicillin. Concentration 3: 1000 IU/mL penicillin, 250 µg/mL vancomycin, and 250 µg/mL amoxicillin.</p> </td> </tr>
        </table>
          <p content-type="html">
            <a id="472i01" name="472i01"/>&#13;
         <p align="left">C.M.F. Lima, J.T. Schroeder, C.E.S. Galvão, F.M. Castro, J. Kalil and N.F. Adkinson Jr. Functional changes of dendritic cells in hypersensitivity reactions to amoxicillin. Braz J Med Biol Res 2010; 43: 964-968. &#13;
         </p>&#13;
           <p>
            <ext-link ext-link-type="uri" xlink:href="javascript:history.back()">
            <img src="/img/revistas/bjmbr/v43n10/472i01.jpg" align="BOTTOM" border="0" vspace="0" hspace="0" width="800" height="403" imported="true"/>
         </ext-link>
         </p>&#13;
           <p>&#13;
             <p align="left">Figure 1. Concentration of IL-6 (pg/10<sup>6 </sup>cells) produced by the suspension of plasmacytoid dendritic cells (pDC). Concentration (Conc.) 1: 20 IU/mL penicillin, 5 µg/mL vancomycin, 5 µg/mL amoxicillin, 75 ng/mL anti-FcεRI/mL, and 100 nM CpG. Concentration 2: 200 IU/mL penicillin, 50 µg/mL vancomycin, and 50 µg/mL amoxicillin. Concentration 3: 1000 IU/mL penicillin, 250 µg/mL vancomycin, and 250 µg/mL amoxicillin.</p>&#13;
           </p>&#13;
         &#13;
         &#13;
        </p>
        <p>[View larger version of this image (90 K JPG file)]</p> <hr align="LEFT" size="2"/>
        </root>"""
        expected = b"""<root xmlns:xlink="http://www.w3.org/1999/xlink">
        <p><a name="Fig1" id="Fig1"><img src="/img/revistas/bjmbr/v43n10/472i01.jpg" align="BOTTOM" border="0" vspace="0" hspace="0" width="800" height="403" imported="true"/>
        <p>Figure 1. Concentration of IL-6 (pg/10<sup>6 </sup>cells) produced by the suspension of plasmacytoid dendritic cells (pDC). Concentration (Conc.) 1: 20 IU/mL penicillin, 5 &#181;g/mL vancomycin, 5 &#181;g/mL amoxicillin, 75 ng/mL anti-Fc&#949;RI/mL, and 100 nM CpG. Concentration 2: 200 IU/mL penicillin, 50 &#181;g/mL vancomycin, and 50 &#181;g/mL amoxicillin. Concentration 3: 1000 IU/mL penicillin, 250 &#181;g/mL vancomycin, and 250 &#181;g/mL amoxicillin.</p></a></p><hr align="LEFT" size="2"/>
        </root>"""

        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find(".//a[@name='Fig1']"))
        self.assertEqual(xml.find(".//a[@name='Fig1']/p").text, 'Figure 1. Concentration of IL-6 (pg/10')
        self.assertTrue(
            xml.find(".//a[@name]/p").getchildren()[-1].tail.endswith(
                "amoxicillin."))
        self.assertIsNotNone(xml.find(".//a[@name='Fig1']/img[@src='/img/revistas/bjmbr/v43n10/472i01.jpg']"))

    def test_transform_when_thumbnail_image_has_not_same_name_as_normal_image(self):
        text = """<root xmlns:xlink="http://www.w3.org/1999/xlink">
                    <table width="100%" border="0">
                <tr align="left" valign="top">
                <td width="16%">
                <a href="#2406t01" link-type="internal">
                <img src="/img/revistas/bjmbr/v45n12/table.jpg" width="100" height="65" border="2"/>
            </a>
            </td> <td width="84%"> <p align="LEFT">
                <a name="Tab1" id="Tab1"/>Table 1. Distribution of serum hs-CRP concentration (<sup>mg/L</sup>) according to gender.</p> </td> </tr>
            </table>
            <p content-type="html">
                <a id="2406t01" name="2406t01"/>&#13;
            &#13;
             &#13;
            &#13;
               High sensitivity C-reactive protein distribution in the elderly: the Bambuí Cohort Study, Brazil. L.G.S. Assunção, S.M. Eloi-Santos, S.V. Peixoto, M.F. Lima-Costa and P.G. Vidigal. Braz J Med Biol Res 2012; 45: 1284-1286 &#13;
            &#13;
               <hr align="LEFT" width="100%" size="2"/>&#13;
            &#13;
               <p>
                <ext-link ext-link-type="uri" xlink:href="javascript:history.back()">
                <img src="/img/revistas/bjmbr/v45n12/2406t01.jpg" align="BOTTOM" border="0" vspace="0" hspace="0" width="600" height="303" imported="true"/>
             </ext-link>
             </p>&#13;
            &#13;
               &#13;
            &#13;
                 &#13;
            &#13;
               &#13;
            &#13;
             &#13;
            &#13;
             &#13;
            &#13;
            </p>
        <p>[View larger version of this table (57 K JPG file)]</p> <hr align="LEFT" width="100%" size="2"/>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find(".//a[@name='Tab1']"))
        p_text = xml.find(".//a[@name='Tab1']/p").text.strip()
        self.assertTrue(
            p_text.startswith(
                "Table 1. Distribution of serum hs-CRP concentration ("))
        self.assertTrue(
            xml.find(".//a[@name]/p").getchildren()[-1].tail.endswith(
                ") according to gender."))
        self.assertIsNotNone(
            xml.find(
                ".//a[@name='Tab1']/img[@src='/img/revistas/bjmbr/v45n12/2406t01.jpg']"))


class TestAssetThumbnailInLinkAndAnchorAndCaption(unittest.TestCase):

    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.AssetThumbnailInLinkAndAnchorAndCaption()

    def test_transform_converts_thumbnail_into_simpler_structure(self):
        text = """<root xmlns:xlink="http://www.w3.org/1999/xlink">
        <a href="#650i02" link-type="internal">
          <img src="/img/revistas/bjmbr/v43n10/650i02peq.jpg" border="2"/>
        </a>
        <p content-type="html">
          <a id="650i02" name="650i02"/>&#13;
         <p align="left">C. Raineki, A. Pickenhagen, T.L. Roth, D.M. Babstock, J.H. McLean, C.W. Harley, A.B. Lucion and R.M. Sullivan. The neurobiology of infant maternal odor learning. Braz J Med Biol Res 2010; 43: 914-919. &#13;
         </p>&#13;
           <p>
            <ext-link ext-link-type="uri" xlink:href="javascript:history.back()">
            <img src="/img/revistas/bjmbr/v43n10/650i02.jpg" align="BOTTOM" border="0" vspace="0" hspace="0" width="800" height="349" imported="true"/>
         </ext-link>
         </p>&#13;
           <p>&#13;
             <p align="LEFT">Figure 2. During early life (postnatal day 8), pairing an odor with a 0.5-mA shock does not produce a change in pCREB expression (top) or <italic>2</italic>-<italic>deoxy-d-glucose</italic> (2-DG) uptake (bottom) in the lateral (LA) and basolateral (BLA) amygdala. The expression of phosphorylated cAMP response element binding protein (pCREB) in the cortical amygdala (CoA), a component of the olfactory cortex, appears to be heightened by odor exposure.</p>&#13;
           </p>&#13;
         &#13;
         &#13;
        </p>
        <a name="Fig2" id="Fig2"/>
        Figure 2. During early life (postnatal day 8), pairing an odor with a 0.5-mA shock does not produce a change in pCREB expression (top) or <italic>2</italic>-<italic>deoxy-d-glucose</italic> (2-DG) uptake (bottom) in the lateral (LA) and basolateral (BLA) amygdala. The expression of phosphorylated cAMP response element binding protein (pCREB) in the cortical amygdala (CoA), a component of the olfactory cortex, appears to be heightened by odor exposure. <p>[View larger version of this image (340 K JPG file)]</p>
        <hr align="LEFT" size="2"/>
        </root>"""
        expected = b"""<root xmlns:xlink="http://www.w3.org/1999/xlink">
        <p><a name="Fig2" id="Fig2"><img src="/img/revistas/bjmbr/v43n10/650i02.jpg" align="BOTTOM" border="0" vspace="0" hspace="0" width="800" height="403" imported="true"/>
        <p>Figure 2. During early life (postnatal day 8), pairing an odor with a 0.5-mA shock does not produce a change in pCREB expression (top) or <italic>2</italic>-<italic>deoxy-d-glucose</italic> (2-DG) uptake (bottom) in the lateral (LA) and basolateral (BLA) amygdala. The expression of phosphorylated cAMP response element binding protein (pCREB) in the cortical amygdala (CoA), a component of the olfactory cortex, appears to be heightened by odor exposure. </p></a></p>
        <hr align="LEFT" size="2"/>
        </root>"""

        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find(".//a[@name='Fig2']"))
        self.assertEqual(xml.find(".//a[@name='Fig2']/p").text.strip(), 'Figure 2. During early life (postnatal day 8), pairing an odor with a 0.5-mA shock does not produce a change in pCREB expression (top) or')

        self.assertTrue(
            xml.find(".//a[@name='Fig2']/p").getchildren()[-1].tail.endswith(
                "appears to be heightened by odor exposure. "))
        self.assertIsNotNone(xml.find(".//a[@name='Fig2']/img[@src='/img/revistas/bjmbr/v43n10/650i02.jpg']"))


class TestAssetThumbnailInLayoutTableAndLinkInMessage(unittest.TestCase):

    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.AssetThumbnailInLayoutTableAndLinkInMessage()

    def test_transform(self):
        text = """<root>
        <table border="0" cellpadding="2" cellspacing="0" width="100%">
        <tr>
        <td>
            <a name="Fig3" id="Fig3"/>
            <img src="/img/revistas/bjmbr/v30n6/2677fig1peq.gif"/>
        </td>
        <td>Figure 3 - Gastric retention (%) 15 min after the infusion of test meals containing 2.5% glucose + 2.5% galactose (5% glu + gal), 5% lactose, 5% glucose + 5% galactose (10% glu + gal) or 10% lactose. The rats were fed normal chow (control) or chow with 20% (w/w) lactose (experimental) for four weeks after which time the gastric retention was measured (N = 12 per subgroup). The data are presented as box plots, where the intermediate, lower and upper horizontal lines indicate the median, first and third quartiles of the gastric retention values, respectively, and error bars indicate the maximum and minimum gastric retention values observed. Significant differences between subgroups tested by the Kruskal-Wallis test (P&lt;0.10) followed by the multiple comparisons test (P&lt;0.02) are indicated in the figure.</td> </tr>
        </table>
        <p>
            <a href="#2677fig1" link-type="internal">[View larger version of this image (28 K GIF file)]</a>
        </p>
        <p content-type="html">
            <a id="2677fig1" name="2677fig1"/>

            <p align="center">
                <img src="http://www.scielo.br/img/fbpe/bjmbr/v30n6/2677fig1.gif" imported="true" link-type="external"/> </p>

            <p>Figure 3 - Gastric retention (%) 15 min after the infusion of
            test meals containing 2.5% glucose + 2.5% galactose (5% glu +
            gal), 5% lactose, 5% glucose + 5% galactose (10% glu + gal) or
            10% lactose. The rats were fed normal chow (control) or chow with
            20% (w/w) lactose (experimental) for four weeks after which time
            the gastric retention was measured (N = 12 per subgroup). The
            data are presented as box plots, where the intermediate, lower
            and upper horizontal lines indicate the median, first and third
            quartiles of the gastric retention values, respectively, and
            error bars indicate the maximum and minimum gastric retention
            values observed. Significant differences between subgroups tested
            by the Kruskal-Wallis test (P&lt;0.10) followed by the multiple
            comparisons test (P&lt;0.02) are indicated in the figure.</p>
        </p>
        </root>"""
        expected = b"""<root xmlns:xlink="http://www.w3.org/1999/xlink">
            <p>
            <a name="Fig3" id="Fig3">
            <img src="/img/revistas/bjmbr/v30n6/2677fig1.gif" align="BOTTOM" border="0" vspace="0" hspace="0" width="800" height="403" imported="true"/>
            <p>Figure 3 - Gastric retention (%) 15 min after the infusion of
            test meals containing 2.5% glucose + 2.5% galactose (5% glu +
            gal), 5% lactose, 5% glucose + 5% galactose (10% glu + gal) or
            10% lactose. The rats were fed normal chow (control) or chow with
            20% (w/w) lactose (experimental) for four weeks after which time
            the gastric retention was measured (N = 12 per subgroup). The
            data are presented as box plots, where the intermediate, lower
            and upper horizontal lines indicate the median, first and third
            quartiles of the gastric retention values, respectively, and
            error bars indicate the maximum and minimum gastric retention
            values observed. Significant differences between subgroups tested
            by the Kruskal-Wallis test (P&lt;0.10) followed by the multiple
            comparisons test (P&lt;0.02) are indicated in the figure.</p>
            </a>
            <hr align="LEFT" size="2"/>
            </root>"""

        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find(".//a[@name='Fig3']"))
        p_text = xml.find(".//a[@name='Fig3']/p").text.strip()
        self.assertTrue(
            p_text.startswith(
                "Figure 3 - Gastric retention (%) 15 min after the infusion"))
        self.assertTrue(
            p_text.endswith(
                "are indicated in the figure."))
        self.assertIsNotNone(
            xml.find(
                ".//a[@name='Fig3']/img[@src='/img/revistas/bjmbr/v30n6/2677fig1.gif']"))


class TestRemoveTableUsedToDisplayFigureAndLabelAndCaptionSideBySide(unittest.TestCase):

    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.RemoveTableUsedToDisplayFigureAndLabelAndCaptionSideBySide()

    def test_transform(self):
        text = """<root>
        <table border="0" cellpadding="2" cellspacing="0" width="100%">
          <tr>
            <td>
              <a name="Fig1" id="Fig1"/>
            <img src="/img/revistas/bjmbr/v30n2/2635fig1.gif"/>
          </td>
          <td>Figure 1 - Effects of peripheral <sub>post-trial</sub> administration of</td>
          </tr>
        </table>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find(".//a[@name='Fig1']"))
        p_text = xml.find(".//a[@name='Fig1']/p").text.strip()
        self.assertTrue(
            p_text.startswith(
                "Figure 1 - Effects of peripheral"))
        self.assertTrue(
            xml.find(".//a[@name='Fig1']/p").getchildren()[-1].tail.startswith(
                " administration of"))
        self.assertIsNotNone(
            xml.find(
                ".//a[@name='Fig1']/img[@src='/img/revistas/bjmbr/v30n2/2635fig1.gif']"))


class TestRemoveTableUsedToDisplayFigureAndLabelAndCaptionInTwoLines(unittest.TestCase):
    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.RemoveTableUsedToDisplayFigureAndLabelAndCaptionInTwoLines()

    def test_transform(self):
        text = """<root>
        <p align="center">
            <a name="Fig1" id="Fig1"/> <img src="/img/revistas/bjmbr/v30n1/2560fig1peq.gif"/>
        </p>
        <p>Figure 1 - Effect of dexamethasone pretreatment on ethanol-induced hypothermia in rats. Rats received dexamethasone (2.0 mg/kg,<italic> ip</italic>) or saline administered 15 min before ethanol 20% w/v (2.0, 3.0 or 4.0 g/kg, <italic>ip</italic>) or saline. Colon temperature was measured 30, 60 and 90 min after ethanol administration. The animals were divided into 4 groups: saline + saline (open circles); dexamethasone + saline (filled circles); saline + ethanol (open squares), and dexamethasone + ethanol (filled squares). Data are reported as the mean ± SEM of the fall in temperature in degrees Celsius obtained for 10 animals compared to basal values. *P&lt;0.05 compared to saline + saline group; <sup>+</sup>P&lt;0.05 compared to saline + ethanol group (ANOVA).</p>
        <p>
            <a href="#2560fig1" link-type="internal">[View larger version of this image (14 K GIF file)]</a>
        </p>
        <p content-type="html">
            <a id="2560fig1" name="2560fig1"/>

        <p align="center">
          <img src="http://www.scielo.br/img/fbpe/bjmbr/v30n1/2560fig1.gif"
          imported="true" link-type="external"/> </p>

        <p>Figure 1 - Effect of dexamethasone pretreatment on
        ethanol-induced hypothermia in rats. Rats received dexamethasone
        (2.0 mg/kg,<italic> ip</italic>) or saline administered 15 min before
        ethanol 20% w/v (2.0, 3.0 or 4.0 g/kg, <italic>ip</italic>) or saline.
        Colon temperature was measured 30, 60 and 90 min after ethanol
        administration. The animals were divided into 4 groups: saline +
        saline (open circles); dexamethasone + saline (filled circles);
        saline + ethanol (open squares), and dexamethasone + ethanol
        (filled squares). Data are reported as the mean ± SEM of the
        fall in temperature in degrees Celsius obtained for 10 animals
        compared to basal values. *P&lt;0.05 compared to saline + saline
        group; <sup>+</sup>P&lt;0.05 compared to saline + ethanol group
        (ANOVA).</p></p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        print(etree.tostring(xml))
        self.assertIsNotNone(xml.find(".//a[@name='Fig1']"))
        p_text = xml.find(".//a[@name='Fig1']/p").text.strip()
        self.assertTrue(
            p_text.startswith(
                "Figure 1 - Effect of dexamethasone pretreatment on"))
        self.assertTrue(
            xml.find(".//a[@name='Fig1']/p").getchildren()[-1].tail.startswith(
                "P&lt;0.05 compared to saline + ethanol group"))
        self.assertIsNotNone(
            xml.find(
                ".//a[@name='Fig1']/img[@src='/img/revistas/bjmbr/v30n1/2560fig1.gif']"))

class TestAssetThumbnailInLayoutImgAndCaptionAndMessage(unittest.TestCase):

    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.AssetThumbnailInLayoutImgAndCaptionAndMessage()

    def test_transform(self):
        text = """<root>
        <p align="center">
            <a name="Fig1" id="Fig1"/> <img src="/img/revistas/bjmbr/v30n1/2560fig1peq.gif"/>
        </p>
        <p>Figure 1 - Effect of dexamethasone pretreatment on ethanol-induced hypothermia in rats. Rats received dexamethasone (2.0 mg/kg,<italic> ip</italic>) or saline administered 15 min before ethanol 20% w/v (2.0, 3.0 or 4.0 g/kg, <italic>ip</italic>) or saline. Colon temperature was measured 30, 60 and 90 min after ethanol administration. The animals were divided into 4 groups: saline + saline (open circles); dexamethasone + saline (filled circles); saline + ethanol (open squares), and dexamethasone + ethanol (filled squares). Data are reported as the mean ± SEM of the fall in temperature in degrees Celsius obtained for 10 animals compared to basal values. *P&lt;0.05 compared to saline + saline group; <sup>+</sup>P&lt;0.05 compared to saline + ethanol group (ANOVA).</p>
        <p>
            <a href="#2560fig1" link-type="internal">[View larger version of this image (14 K GIF file)]</a>
        </p>
        <p content-type="html">
            <a id="2560fig1" name="2560fig1"/>

        <p align="center">
          <img src="http://www.scielo.br/img/fbpe/bjmbr/v30n1/2560fig1.gif"
          imported="true" link-type="external"/> </p>

        <p>Figure 1 - Effect of dexamethasone pretreatment on
        ethanol-induced hypothermia in rats. Rats received dexamethasone
        (2.0 mg/kg,<italic> ip</italic>) or saline administered 15 min before
        ethanol 20% w/v (2.0, 3.0 or 4.0 g/kg, <italic>ip</italic>) or saline.
        Colon temperature was measured 30, 60 and 90 min after ethanol
        administration. The animals were divided into 4 groups: saline +
        saline (open circles); dexamethasone + saline (filled circles);
        saline + ethanol (open squares), and dexamethasone + ethanol
        (filled squares). Data are reported as the mean ± SEM of the
        fall in temperature in degrees Celsius obtained for 10 animals
        compared to basal values. *P&lt;0.05 compared to saline + saline
        group; <sup>+</sup>P&lt;0.05 compared to saline + ethanol group
        (ANOVA).</p></p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find(".//a[@name='Fig1']"))
        p_text = xml.find(".//a[@name='Fig1']/p").text.strip()
        self.assertTrue(
            p_text.startswith(
                "Figure 1 - Effect of dexamethasone pretreatment on"))
        self.assertTrue(
            xml.find(".//a[@name='Fig1']/p").getchildren()[-1].tail.endswith(
                "(ANOVA)."))
        self.assertIsNotNone(
            xml.find(
                ".//a[@name='Fig1']/img[@src='/img/revistas/bjmbr/v30n1/2560fig1.gif']"))


class TestRemoveTableUsedToDisplayFigureAndLabelAndCaptionInTwoLines(unittest.TestCase):

    def setUp(self):
        pipeline = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pipeline.RemoveTableUsedToDisplayFigureAndLabelAndCaptionInTwoLines()

    def test_transform(self):
        text = """<root>
        <table width="100%" cellpadding="2" cellspacing="0" border="0">
            <tr>
            <td width="38%" valign="TOP">
            <p align="center">
            <a name="Fig1" id="Fig1"/>
          <img src="/img/revistas/bjmbr/v31n12/3156i01.gif" align="BOTTOM" border="2" vspace="0" hspace="0"/>
        </p> <p>Figure 1 - Relationship between SHBG levels and 120-min proinsulin after a glucose load test in men.</p>
        </td> </tr>
        </table></root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))

        self.assertIsNotNone(xml.find(".//a[@name='Fig1']"))
        p_text = xml.find(".//a[@name='Fig1']/p").text.strip()
        self.assertTrue(
            p_text.startswith(
                "Figure 1 - Relationship between SHBG levels"))
        self.assertTrue(
            p_text.endswith(
                "load test in men."))
        self.assertIsNotNone(
            xml.find(
                ".//a[@name='Fig1']/img[@src='/img/revistas/bjmbr/v31n12/3156i01.gif']"))


class TestFixOutSitetablePiep(unittest.TestCase):

    def test_move_table_when_not_aligned_table_wrap(self):
        text = """<root>
            <p align="center">
                <table-wrap name="Tab1" id="Tab1" xml_text="table 1" xml_tag="table-wrap" xml_reftype="table" xml_id="Tab1" xml_label="table 1" status="identify-content">
                    <bold label-of="Tab1" content-type="label">Table 1</bold> - Protein-related sites.
                </table-wrap><br/>
            </p>
            <p>
                <table border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td>
                            <p align="center">
                                <bold>URL</bold>
                            </p>
                        </td>
                    </tr>
                </table>
            </p></root>"""

        xml = etree.fromstring(text)
        pl = ConvertElementsWhichHaveIdPipeline()
        text, xml = pl.FixOutSideTablePipe().transform((text, xml))
        self.assertIn('table',
                      [tag.tag for tag in xml.find(".//table-wrap/p").getchildren()])


class TestCreateSectionElemetWithSectionTitlePipe(unittest.TestCase):

    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.CreateSectionElemetWithSectionTitlePipe()

    def test_transform_creates_sec_elem_with_title_from_sec(self):
        text = """<root>
        <body>
            <p>
                <sec id="introduction"/>
                <bold>Introduction</bold>
            </p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(
            xml.findtext(".//sec[@id='introduction']/title"),
            "Introduction"
        )
        sec = xml.find(".//sec")
        self.assertEqual(sec.get("sec-type"), "intro")

    def test_transform_does_not_create_sec_elem_with_title_from_sec(self):
        text = """<root>
        <body>
            <p>
                <sec id="introduction"/>
                <xref>Introduction</xref>
            </p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(
            xml.findtext(".//sec[@id='introduction']/title"),
            None
        )
        sec = xml.find(".//sec")
        self.assertEqual(sec.get("sec-type"), "intro")

    def test_transform_creates_sec_elem_with_title_from_ordinary_sec(self):
        text = """<root>
        <body>
            <p>
                <ordinary-sec id="abstract"/>
                <bold>Abstract</bold>
            </p>
            <p>paragrafo 1 de Material and Methods</p>
            <p>paragrafo 2 de Material and Methods</p>
            <p>paragrafo 3 de Material and Methods</p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(
            xml.findtext(".//sec[@id='abstract']/title"),
            "Abstract"
        )
        self.assertIsNone(xml.findtext(".//sec[@sec-type]"))


class TestInsertSectionChildrenPipe(unittest.TestCase):

    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.InsertSectionChildrenPipe()

    def test_transform_inserts_elements_in_sec_until_find_other_sec(self):
        text = """<root>
        <body>
            <sec id="abstract">
                <title>Abstract</title>
            </sec>
            <p>paragrafo 1 de Abstract</p>
            <sec id="material">
                <title>Material and Methods</title>
            </sec>
            <p>paragrafo 1 de Material and Methods</p>
            <p>paragrafo 2 de Material and Methods</p>
            <p>paragrafo 3 de Material and Methods</p>
            <sec id="acknowledgments">
                <title>Acknowledgments</title>
            </sec>
            <p>paragrafo 1 de Acknowledgments</p>
            <p>paragrafo qq</p>
            <p>paragrafo qq</p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(
            len(xml.find(".//sec[@id='abstract']").getchildren()),
            2
        )
        self.assertEqual(
            len(xml.find(".//sec[@id='material']").getchildren()),
            4
        )

    def test_transform_inserts_only_one_element_in_sec_if_it_is_last_sec(self):
        text = """<root>
        <body>
            <sec id="acknowledgments">
                <title>Acknowledgments</title>
            </sec>
            <p>paragrafo 1 de Acknowledgments</p>
            <p>paragrafo qq</p>
            <p>paragrafo qq</p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(
            len(xml.find(".//sec[@id='acknowledgments']").getchildren()),
            2
        )


class TestAfterOneSectionAllTheOtherElementsMustBeSectionPipe(unittest.TestCase):

    def setUp(self):
        pl = HTML2SPSPipeline()
        self.pipe = pl.AfterOneSectionAllTheOtherElementsMustBeSectionPipe()

    def test_transform_(self):
        text = """<root>
        <body>
            <p>paragrafo qq 1</p>
            <p>paragrafo qq 2</p>
            <p>paragrafo qq 3</p>
            <sec id="abstract">
                <title>Abstract</title>
                <p>paragrafo 1 de Abstract</p>
            </sec>
            <p>paragrafo qq 4</p>
            <p>paragrafo qq 5</p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        body_chidren = xml.find(".//body").getchildren()
        self.assertEqual(
            [node.tag for node in body_chidren],
            ["p", "p", "p", "sec", "sec", "sec"]
        )
        self.assertEqual(body_chidren[-1].findtext("p"), "paragrafo qq 5")
        self.assertEqual(body_chidren[-2].findtext("p"), "paragrafo qq 4")


class TestRemoveEmptyPAndEmptySectionPipe(unittest.TestCase):

    def setUp(self):
        pl = HTML2SPSPipeline()
        self.pipe = pl.RemoveEmptyPAndEmptySectionPipe()

    def test_transform_remove_element(self):
        text = """<root>
        <body>
            <p>texto antes <a href="#ancora"><img/></a> texto depois</p>
            <p>parágrafo 1</p>
            <p></p>
            <p> </p>
            <p> <img/> </p>
        </body>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(len(xml.findall(".//p")), 3)


class TestRemoveXrefWhichRefTypeIsSecOrOrdinarySec(unittest.TestCase):
    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.RemoveXrefWhichRefTypeIsSecOrOrdinarySecPipe()

    def test_transform_removes_all_xref(self):
        text = """<root>
        <p>
        <xref ref-type="ordinary-sec" rid="abstract">Abstract</xref>
        </p>
        <p>
        <xref ref-type="sec" rid="introduction">Introduction</xref>
        </p>
        <p>
        <xref ref-type="sec" rid="material">Material and Methods</xref>
        </p>
        <p>
        <xref ref-type="sec" rid="results">Results</xref>
        </p>
        <p>
        <xref ref-type="sec" rid="discussion">Discussion</xref>
        </p>
        <p>
        <xref ref-type="ordinary-sec" rid="references">References</xref>
        </p>
        <p>
        <xref ref-type="ordinary-sec" rid="acknowledgments">Acknowledgments</xref>
        </p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(len(xml.findall(".//xref")), 0)


class TestRemoveFnWhichHasOnlyXref(unittest.TestCase):
    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.RemoveFnWhichHasOnlyXref()

    def test_transform(self):
        text = """<root>
        <p id="p1">
            <fn>
                <p id="p2">
                    <xref ref-type="ordinary-sec" rid="abstract">Abstract</xref>
                </p>
            </fn>
        </p>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertIsNotNone(xml.find("./p[@id='p1']/xref"))



class TestFnFixLabel(unittest.TestCase):
    def setUp(self):
        pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = pl.FnFixLabel()

    def test_fix_label_get_characters_from_previous_text_and_from_tail(self):
        text = """<root>
            <fn><p>(<label>1</label>) Texto</p></fn>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(xml.findtext("./fn/label"), "(1)")
        self.assertEqual(xml.find("./fn").getchildren()[0].tag, "label")

    def test_fix_label_get_characteres_from_previous_and_next(self):
        text = """<root>
            <fn><p>(</p><label>1</label><p>) Texto</p></fn>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(xml.findtext("./fn/label"), "(1)")
        self.assertEqual(xml.find("./fn").getchildren()[0].tag, "label")

    def test_fix_label_make_label_first_child_of_fn(self):
        text = """<root>
            <fn><p></p><p><label>1</label> Texto</p></fn>
        </root>"""
        xml = etree.fromstring(text)
        text, xml = self.pipe.transform((text, xml))
        self.assertEqual(xml.find("./fn").getchildren()[0].tag, "label")


class TestFnPipe_FindStyleTagWhichIsNextFromFnAndWrapItInLabel(unittest.TestCase):
    def test_transform(self):
        text = """<root>
        <body><fn/><bold>título</bold>texto fora do bold</body>
        </root>"""
        expected = (
            """<root>
        <body><fn/><label><bold>título</bold></label>texto fora do bold</body>
        </root>"""
        )
        xml = etree.fromstring(text)
        pl = ConvertElementsWhichHaveIdPipeline()
        pipe = pl.FnPipe_FindStyleTagWhichIsNextFromFnAndWrapItInLabel()
        text, xml = pipe.transform((text, xml))
        self.assertEqual(xml.findtext(".//label/bold"), "título")
        self.assertEqual(xml.find(".//label/bold").tail, "")
        self.assertEqual(xml.find(".//label").tail, "texto fora do bold")


class TestFnPipe_FindLabelOfAndCreateNewEmptyFnAsPreviousElemOfLabel(unittest.TestCase):
    def test_transform_creates_fn_to_second_label(self):
        text = """<root>
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        </root>"""
        xml = etree.fromstring(text)
        pl = ConvertElementsWhichHaveIdPipeline()
        pipe = pl.FnPipe_FindLabelOfAndCreateNewEmptyFnAsPreviousElemOfLabel()
        text, xml = pipe.transform((text, xml))
        labels = xml.findall(".//label")
        self.assertIsNone(labels[0].getprevious())
        self.assertEqual(labels[1].getprevious().tag, "fn")

    def test_transform_creates_fn_as_previous_elem_of_label(self):
        text = """<root>
        <label href="#home" xml_text="*" label-of="back">*</label> Corresponding author
        </root>"""
        xml = etree.fromstring(text)
        pl = ConvertElementsWhichHaveIdPipeline()
        pipe = pl.FnPipe_FindLabelOfAndCreateNewEmptyFnAsPreviousElemOfLabel()
        text, xml = pipe.transform((text, xml))
        labels = xml.findall(".//label")
        self.assertEqual(labels[0].getprevious().tag, "fn")
