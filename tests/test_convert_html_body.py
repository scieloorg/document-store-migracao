# code=utf-8

import os
import unittest
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
        self
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

    def test_pipe_remove_id_duplicated(self):
        text = """<root>
        <a id="B1" name="B1">Texto 1</a><p>Texto 2</p>
        <a id="B1" name="B1">Texto 3</a></root>"""
        expected = b"""<root>
        <a id="B1" name="B1">Texto 1</a><p>Texto 2</p>
        Texto 3</root>"""

        raw, transformed = self._transform(
            text,
            ConvertElementsWhichHaveIdPipeline().EvaluateElementAToDeleteOrMarkAsFnLabelPipe(),
        )
        self.assertEqual(etree.tostring(transformed), expected)


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
        text, xml = self.pl.CompleteElementAWithNameAndIdPipe().transform((text, xml))
        self.assertEqual(etree.tostring(xml), expected)

    def test_pipe_asterisk_in_a_href(self):
        text = """<root><a href="#1a"><sup>*</sup></a>
        <a name="1a" id="1a"/><a href="#1b"><sup>*</sup></a></root>"""
        expected = b"""<root><a href="#1a"><sup>*</sup></a>
        <a name="1a" id="1a"/><sup>*</sup></root>"""
        xml = etree.fromstring(text)

        text, xml = self.pl.EvaluateElementAToDeleteOrMarkAsFnLabelPipe().transform(
            (text, xml)
        )
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

    def test_pipe_remove_anchor_and_links_to_text_removes_some_elements(self):
        text = """<root>
        <a href="#nota" xml_tag="xref" xml_id="nota" xml_label="1" xml_reftype="fn">1</a>
        <a name="texto" xml_tag="fn" xml_id="texto" xml_reftype="fn"/>
        <a name="nota"  xml_tag="fn" xml_id="nota" xml_reftype="fn"/>
        <a href="#texto" xml_tag="xref" xml_id="texto" xml_reftype="xref">1</a> Nota bla bla
        </root>"""
        raw, transformed = text, etree.fromstring(text)
        raw, transformed = self.pl.EvaluateElementAToDeleteOrMarkAsFnLabelPipe().transform(
            (raw, transformed)
        )
        nodes = transformed.findall(".//a[@name='nota']")
        self.assertEqual(len(nodes), 1)
        nodes = transformed.findall(".//a[@href='#nota']")
        self.assertEqual(len(nodes), 1)

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
                if result != expected:
                    print("")
                    print(result)
                    print(expected)
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
        self.assertEqual(len(xml.findall(".//a[@name]")), 1)
        self.assertEqual(len(xml.findall(".//a[@href]")), 2)

        a_href_items = xml.findall(".//a[@href]")
        self.assertEqual(a_href_items[0].get("href"), "#a05tab01")
        self.assertEqual(a_href_items[1].get("href"), "#a05tab01")


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


class TestFnAddContentPipe(unittest.TestCase):
    def setUp(self):
        self.html_pl = HTML2SPSPipeline(pid="pid")
        self.pl = ConvertElementsWhichHaveIdPipeline()
        self.pipe = self.pl.FnAddContentPipe()

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
        expected = """<root><fn id="nt01"><label>**</label>
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
        expected = b"""<root><fn><label><sup>**</sup></label> TEXTO NOTA</fn></root>"""
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
           <italic>Isso é conhecido pelos pesquisadores como</italic></fn>
         </root>"""
        expected = """<root><fn id="nt01"><p>
            <italic>Isso é conhecido pelos pesquisadores como</italic></p></fn>
        </root>"""

        xml = etree.fromstring(text)

        text, xml = self.pipe.transform((text, xml))
        fn = xml.find(".//fn")
        self.assertEqual(
            fn.find("p/italic").text, "Isso é conhecido pelos pesquisadores como"
        )
        self.assertIsNone(fn.find("p/italic").tail)
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
        text, xml = self.html_pl.ConvertElementsWhichHaveIdPipe().transform((text, xml))
        text, xml = self.html_pl.RemoveInvalidBRPipe().transform((text, xml))
        text, xml = self.html_pl.BRPipe().transform((text, xml))
        text, xml = self.html_pl.BR2PPipe().transform((text, xml))

        print(etree.tostring(xml))

        p = xml.findall(".//fn/p")
        self.assertEqual(xml.find(".//fn/label/bold").text, "Correspondence to:")
        self.assertEqual(p[0].text.strip(), "Maria Auxiliadora Prolungatti Cesar")
        self.assertEqual(
            p[1].text.strip(),
            "Serviço de Clínica Cirúrgica do Hospital Universitário de Taubaté",
        )
        self.assertEqual(p[2].text.strip(), "Avenida Granadeiro Guimarães, 270")
        self.assertEqual(p[3].text.strip(), "CEP: 12100-000 – Taubaté (SP), Brazil.")
        self.assertEqual(p[4].find("email").text, "prolungatti@uol.com.br")

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
        self
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
