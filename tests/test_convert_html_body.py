import os
import unittest
from lxml import etree

from documentstore_migracao.utils.convert_html_body import HTML2SPSPipeline, _process
from . import SAMPLES_PATH


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
        self.pipeline = HTML2SPSPipeline()

    def test_create_instance(self):
        expected_text = "<p>La nueva epoca de la revista<italic>Salud Publica de Mexico </italic></p>"
        pipeline = HTML2SPSPipeline()
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
        text = "<root><p>Colonização micorrízica e concentração de nutrientes em três cultivares de bananeiras em um latossolo amarelo da Amazônia central</p> <p/> </root>"
        expected = "<root><p>Colonização micorrízica e concentração de nutrientes em três cultivares de bananeiras em um latossolo amarelo da Amazônia central</p>  </root>"
        raw, transformed = self._transform(text, self.pipeline.RemoveEmptyPipe())
        resultado = etree.tostring(transformed, encoding="unicode")
        self.assertEqual(
            expected.replace(">", ">[BREAK]").split("[BREAK]"),
            resultado.replace(">", ">[BREAK]").split("[BREAK]"),
        )

    def test_pipe_remove_empty_bold(self):
        text = "<root><p>Colonização micorrízica e concentração de nutrientes <bold> </bold> em três cultivares de bananeiras em um latossolo amarelo</p> </root>"
        expected = "<root><p>Colonização micorrízica e concentração de nutrientes  em três cultivares de bananeiras em um latossolo amarelo</p> </root>"
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
        self.assertEqual(etree.tostring(transformed), b"<root><hr/></root>")

    def test_pipe_br(self):
        text = '<root><p align="x">bla<br/> continua outra linha</p><p baljlba="1"/><td><br/></td><sec><br/></sec></root>'
        raw, transformed = self._transform(text, self.pipeline.BRPipe())

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
            etree.tostring(transformed), b'<root><sec id="intro">bla</sec><sec/></root>'
        )

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
            b"<list-item><p>Texto dentro de 3</p></list-item>",
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
            '{http://www.w3.org/1999/xlink}href': 'http://bla.org',
            'ext-link-type': 'uri'
        }
        xml = etree.fromstring(
            '<root><a href="http://bla.org">texto</a></root>')
        node = xml.find('.//a')

        self.pipeline.APipe()._parser_node_external_link(node)

        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))
        self.assertEqual(
            node.attrib.get(
                '{http://www.w3.org/1999/xlink}href'), 'http://bla.org')
        self.assertEqual(
            node.attrib.get('ext-link-type'), 'uri')
        self.assertEqual(node.tag, 'ext-link')
        self.assertEqual(node.text, 'texto')
        self.assertEqual(set(expected.keys()), set(node.attrib.keys()))

    def test_pipe_a___parser_node_external_link_for_email(self):
        """
        <ext-link ext-link-type="email" xlink:href="mailto:nuesslin@lrz.tum.de">
nuesslin@lrz.tum.de</ext-link>
        """
        expected_keys = [
            '{http://www.w3.org/1999/xlink}href',
            'ext-link-type'
        ]
        href = ['mailto:a@scielo.org', 'mailto:x@scielo.org']
        content = ['Enviar e-mail para A', '<img src="mail.gif" />']
        expected = """<root>
        <p><ext-link ext-link-type="email" xlink:href="mailto:a@scielo.org">Enviar e-mail para A</ext-link></p>
        <p><ext-link ext-link-type="email" xlink:href="mailto:x@scielo.org"><img src="mail.gif" /></ext-link></p>
        </root>"""
        text = """<root>
        <p><a href="mailto:a@scielo.org">Enviar e-mail para A</a></p>
        <p><a href="mailto:x@scielo.org"><img src="mail.gif" /></a></p>
        </root>"""
        xml = etree.fromstring(text)

        for i, node in enumerate(xml.findall('.//a')):
            with self.subTest(i):
                self.pipeline.APipe()._parser_node_external_link(node, "email")

                self.assertEqual(set(expected_keys), set(node.attrib.keys()))
                self.assertIn(
                    node.attrib.get(
                        '{http://www.w3.org/1999/xlink}href'),
                    href[i]
                    )
                self.assertEqual(
                    node.attrib.get('ext-link-type'), 'email')
                self.assertEqual(node.tag, 'ext-link')
                if node.text:
                    self.assertEqual(node.text, 'Enviar e-mail para A')
                else:
                    self.assertIn(
                        '<img src="mail.gif"/>',
                        etree.tostring(node, encoding="unicode"))

    def test_pipe_a_mailto(self):
        text = """<root>
        <p><a href="mailto:a@scielo.org">Enviar e-mail para A</a></p>
        <p><a href="mailto:x@scielo.org"><img src="mail.gif" /></a></p>
        <p><a href="mailto:a04qdr04@scielo.org">Enviar e-mail para a04qdr04</a></p>
        <p><a href="mailto:a04qdr08@scielo.org">Enviar e-mail para mim</a></p>
        </root>"""
        raw, transformed = self._transform(text, self.pipeline.APipe())

        nodes = transformed.findall(".//p/p")
        self.assertEqual(len(nodes), 0)
        texts = [
            b"<p>Enviar e-mail para A<email>a@scielo.org</email></p>",
            b'<p><img src="mail.gif"/><email>x@scielo.org</email></p>',
            b"<p>Enviar e-mail para a04qdr04<email>a04qdr04@scielo.org</email></p>",
            b"<p>Enviar e-mail para mim<email>a04qdr08@scielo.org</email></p>",
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(text, etree.tostring(node).strip())

    def test_pipe_a_anchor(self):
        node = self.etreeXML.find(".//font[@size='1']")
        data = self.etreeXML, node
        self.pipeline.APipe().transform(data)

        text = etree.tostring(node).strip()
        new_xml = etree.fromstring(text)

        self.assertEqual(new_xml.find("xref").attrib["rid"], "home")

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
        raw, transformed = self._transform(text, self.pipeline.APipe())

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
        raw, transformed = self._transform(text, self.pipeline.APipe())
        self.assertIsNone(transformed.find(".//a"))

    def test_pipe_a_href_error(self):
        text = '<root><a href="error">Teste</a></root>'
        raw, transformed = self._transform(text, self.pipeline.APipe())
        self.assertEqual(
            etree.tostring(transformed).strip(),
            b'<root><a href="error">Teste</a></root>'
        )

    def test_pipe_td(self):
        text = '<root><td width="" height="" style="style"><p>Teste</p></td></root>'
        raw, transformed = self._transform(text, self.pipeline.TdCleanPipe())
        self.assertEqual(
            etree.tostring(transformed), b'<root><td style="style">Teste</td></root>'
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

    def test_pipe_graphicChildren_block(self):
        text = """<root><p><block><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></block></p></root>"""
        raw, transformed = self._transform(text, self.pipeline.GraphicChildrenPipe())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><p><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/bul1.gif"/></p></root>""",
        )

    def test_pipe_remove_comments(self):
        text = """<root><!-- COMMENT 1 --><x>TEXT 1</x><y>TEXT 2 <!-- COMMENT 2 --></y></root>"""
        raw, transformed = self._transform(text, self.pipeline.RemoveCommentPipe())
        self.assertEqual(
            etree.tostring(transformed), b"""<root><x>TEXT 1</x><y>TEXT 2 </y></root>"""
        )

    def test_pipe_BodyAllowedTagPipe(self):
        text = """<body><p>TEXT 1</p><hr/><p>TEXT 2</p></body>"""
        raw, transformed = self._transform(text, self.pipeline.BodyAllowedTagPipe())
        self.assertEqual(
            etree.tostring(transformed), b"""<body><p>TEXT 1</p><p>TEXT 2</p></body>"""
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
        self.pipe = HTML2SPSPipeline().RemovePWhichIsParentOfPPipe()

    def _compare_tags_and_texts(self, transformed, expected):
        def normalize(xmltree):
            s = ''.join(etree.tostring(xmltree, encoding='unicode').split())
            s = s.replace('><', '>BREAK<')
            return s.split('BREAK')

        self.assertEqual(
            [node.tag for node in transformed.findall('.//body//*')],
            [node.tag for node in expected.findall('.//body//*')]
        )
        self.assertEqual(
            [node.text.strip() if node.text else ''
             for node in transformed.findall('.//body//*')],
            [node.text.strip() if node.text else ''
             for node in expected.findall('.//body//*')]
        )
        self.assertEqual(normalize(transformed), normalize(expected))

    def test_identify_extra_p_tags(self):
        expected = etree.fromstring("""<root>
            <body>
                <REMOVE_P>
                    <p>paragrafo 1</p>
                    <p>paragrafo 2</p>
                </REMOVE_P>
            </body>
            </root>""")
        self.pipe._identify_extra_p_tags(self.xml)
        self.assertEqual(len(self.xml.findall('.//body//p')), 2)
        self.assertEqual(len(self.xml.findall('.//body//*')), 3)
        self._compare_tags_and_texts(self.xml, expected)

    def test_transform(self):
        expected = etree.fromstring("""<root>
            <body>
            <p>paragrafo 1</p>
            <p>paragrafo 2</p>
            </body>
            </root>""")

        data = self.text, self.xml
        raw, transformed = self.pipe.transform(data)
        self.assertEqual(len(transformed.findall('.//body//p')), 2)
        self.assertEqual(len(transformed.findall('.//body//*')), 2)
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
        self.pipe = HTML2SPSPipeline().RemovePWhichIsParentOfPPipe()

    def _compare_tags_and_texts(self, transformed, expected):
        def normalize(xmltree):
            s = ''.join(etree.tostring(xmltree, encoding='unicode').split())
            s = s.replace('><', '>BREAK<')
            return s.split('BREAK')

        self.assertEqual(
            [node.tag for node in transformed.findall('.//body//*')],
            [node.tag for node in expected.findall('.//body//*')]
        )
        self.assertEqual(
            [node.text.strip() if node.text else ''
             for node in transformed.findall('.//body//*')],
            [node.text.strip() if node.text else ''
             for node in expected.findall('.//body//*')]
        )
        self.assertEqual(normalize(transformed), normalize(expected))

    def test__tag_texts(self):
        expected = etree.fromstring("""<root>
            <body>
                <p>
                    <p>texto 0</p>
                    <p>paragrafo 1</p>
                    <p>texto 2</p>
                    <p>paragrafo 3</p>
                    <p>texto 4</p>
                </p>
            </body>
            </root>""")
        xml = self.xml
        self.pipe._tag_texts(xml)
        result = xml.findall('.//body//p')
        self.assertEqual(len(xml.findall('.//body')), 1)
        self.assertEqual(len(result), 6)
        self._compare_tags_and_texts(self.xml, expected)

    def test__identify_extra_p_tags(self):
        expected = etree.fromstring("""<root>
            <body>
                <REMOVE_P>
                    texto 0
                    <p>paragrafo 1</p>
                    texto 2
                    <p>paragrafo 3</p>
                    texto 4
                </REMOVE_P>
            </body>
            </root>""")
        xml = self.xml
        self.pipe._identify_extra_p_tags(xml)
        self.assertEqual(len(xml.findall('.//body')), 1)
        self._compare_tags_and_texts(xml, expected)

    def test_transform(self):
        expected = etree.fromstring("""<root>
            <body>
            <p>texto 0</p>
            <p>paragrafo 1</p>
            <p>texto 2</p>
            <p>paragrafo 3</p>
            <p>texto 4</p>
            </body>
            </root>""")
        raw, transformed = self.pipe.transform((self.text, self.xml))
        self.assertEqual(len(transformed.findall('.//body')), 1)
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
        self.pipe = HTML2SPSPipeline().RemovePWhichIsParentOfPPipe()

    def _compare_tags_and_texts(self, transformed, expected):
        def normalize(xmltree):
            s = ''.join(etree.tostring(xmltree, encoding='unicode').split())
            s = s.replace('><', '>BREAK<')
            return s.split('BREAK')

        self.assertEqual(
            [node.tag for node in transformed.findall('.//body//*')],
            [node.tag for node in expected.findall('.//body//*')]
        )
        self.assertEqual(
            [node.text.strip() if node.text else ''
             for node in transformed.findall('.//body//*')],
            [node.text.strip() if node.text else ''
             for node in expected.findall('.//body//*')]
        )
        self.assertEqual(normalize(transformed), normalize(expected))

    def test__identify_extra_p_tags(self):
        expected = etree.fromstring("""<root>
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
            </root>""")
        self.pipe._identify_extra_p_tags(self.xml)
        self._compare_tags_and_texts(self.xml, expected)

    def test_transform(self):
        expected = etree.fromstring("""<root>
            <body>
                <p>texto 0</p>
                <p>paragrafo 1</p>
                <p>paragrafo 2</p>
                <p>texto 3</p>
                <p>paragrafo 4</p>
                <p>paragrafo 5</p>
                <p>texto 6</p>
            </body>
            </root>""")
        raw, transformed = self.pipe.transform((self.xml, expected))
        self.assertEqual(len(transformed.findall('.//body')), 1)
        self._compare_tags_and_texts(transformed, expected)
