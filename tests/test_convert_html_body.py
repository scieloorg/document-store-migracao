import os
import unittest
from unittest.mock import patch
from lxml import etree

from documentstore_migracao.utils import files, xml, request
from documentstore_migracao.utils.convert_html_body import HTML2SPSPipeline, _process
from . import SAMPLES_PATH


class TestUtilsFiles(unittest.TestCase):
    def test_list_dir(self):
        self.assertEqual(len(files.list_dir(SAMPLES_PATH)), 6)

    def test_read_file(self):
        data = files.read_file(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )
        self.assertIn("0036-3634", data)

    def test_write_file(self):
        expected_text = "<a><b>bar</b></a>"
        filename = "foo_test.txt"

        try:
            files.write_file(filename, expected_text)

            with open(filename, "r") as f:
                text = f.read()
        finally:
            os.remove(filename)

        self.assertEqual(expected_text, text)


class TestUtilsXML(unittest.TestCase):
    def test_str2objXML(self):

        expected_text = "<a><b>bar</b></a>"
        obj = xml.str2objXML(expected_text)

        self.assertIn(expected_text, str(etree.tostring(obj)))

    def test_find_medias(self):

        with open(os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml"), "r") as f:
            text = f.read()
        obj = etree.fromstring(text)
        medias = xml.find_medias(obj)

        self.assertFalse(len(medias))

    def test_pipe_body_xml(self):
        with open(os.path.join(SAMPLES_PATH, "S0036-36341997000100003.xml"), "r") as f:
            text = f.read()

        obj = etree.fromstring(text)
        html = xml.parser_body_xml(obj)
        tags = ("div", "img", "li", "ol", "ul", "i", "b", "a")
        for tag in tags:
            with self.subTest(tag=tag):
                expected = html.findall(".//%s" % tag)
                self.assertFalse(expected)


class TestUtilsRequest(unittest.TestCase):
    @patch("documentstore_migracao.utils.request.requests")
    def test_get(self, mk_requests):

        expected = {"params": {"collection": "spa"}}
        request.get("http://api.test.com", **expected)
        mk_requests.get.assert_called_once_with("http://api.test.com", **expected)


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

    def test_pipe_p(self):
        text = '<root><p align="x">bla</p><p baljlba="1"/></root>'
        raw, transformed = self._transform(text, self.pipeline.PPipe())

        self.assertEqual(
            etree.tostring(transformed),
            b"<root><p>bla</p><p/></root>")

    def test_pipe_div(self):
        text = '<root><div align="x" id="intro">bla</div><div baljlba="1"/></root>'
        raw, transformed = self._transform(text, self.pipeline.DivPipe())

        self.assertEqual(
            etree.tostring(transformed),
            b'<root><sec id="intro">bla</sec><sec/></root>')

    def test_pipe_img(self):
        text = '<root><img align="x" src="a04qdr04.gif"/><img align="x" src="a04qdr08.gif"/></root>'
        raw, transformed = self._transform(text, self.pipeline.ImgPipe())

        nodes = transformed.findall('.//graphic')

        self.assertEqual(len(nodes), 2)
        for node, href in zip(nodes, ["a04qdr04.gif", "a04qdr08.gif"]):
            with self.subTest(node=node):
                self.assertEqual(
                    href, node.attrib["{http://www.w3.org/1999/xlink}href"]
                )
                self.assertEqual(len(node.attrib), 1)

    def test_pipe_li(self):
        text = '<root><li align="x" src="a04qdr04.gif">Texto dentro de <b>li</b> 1</li><li align="x" src="a04qdr08.gif">Texto dentro de <b>li</b> 2</li></root>'
        expected = [b'Texto dentro de <b>li</b> 1', b'Texto dentro de <b>li</b> 2']
        raw, transformed = self._transform(text, self.pipeline.LiPipe())

        nodes = transformed.findall('.//list-item')
        self.assertEqual(len(nodes), 2)
        for node, text in zip(nodes, expected):
            with self.subTest(node=node):
                self.assertIn(
                    text,
                    etree.tostring(node))
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

        nodes = transformed.findall('.//list')
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 1)
                self.assertEqual(node.attrib['list-type'], 'order')

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

        nodes = transformed.findall('.//list')
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 1)
                self.assertEqual(node.attrib['list-type'], 'bullet')

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

        nodes = transformed.findall('.//italic')
        self.assertEqual(len(nodes), 4)
        texts = [
            b'<italic>texto 1</italic> 1',
            b'<italic>texto <b>2</b></italic> 2',
            b'<italic><b>texto S</b></italic> 1',
            b'<italic><b>texto</b> G</italic> 2',
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

        nodes = transformed.findall('.//bold')
        self.assertEqual(len(nodes), 4)
        texts = [
            b'<bold>texto 1</bold> 1',
            b'<bold>texto <sup>2</sup></bold> 2',
            b'<bold><sup>texto S</sup></bold> 1',
            b'<bold><sup>texto</sup> G</bold> 2',
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(len(node.attrib), 0)
                self.assertEqual(text, etree.tostring(node))

    """
    def test_pipe_a_mailto(self):
        text = ''
            '<root>'
            '<p><a href="mailto:a@scielo.org">Enviar e-mail para A</a></p>'
            '<p><a href="mailto:x@scielo.org"><img src="mail.gif"/></a></p>'
            '<p><a href="mailto:a04qdr04@scielo.org">Enviar e-mail para a04qdr04</a></p>'
            '<p><a href="mailto:a04qdr08@scielo.org">Enviar e-mail para mim</a></p>'
            '</root>'
        raw, transformed = self._transform(text, self.pipeline.APipe())

        nodes = transformed.findall('.//p')
        self.assertEqual(len(nodes), 4)
        texts = [
            b'<p>Enviar e-mail para A <email>a@scielo.org</email></p>',
            b'<p><img src="mail.gif"/> <email>x@scielo.org</email></p>',
            b'<p>Enviar e-mail para a04qdr04 <email>a04qdr04@scielo.org</email></p>',
            b'<p>Enviar e-mail para mim <email>a04qdr08@scielo.org</email></p>',
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(text, etree.tostring(node).strip())


    def test_pipe_a_anchor(self):
        text = ''
            '<root>'
            '<p><a href="a"/></p>'
            '<p><a href="x"><img src="mail.gif"/></a></p>'
            '<p><a href="a04qdr04">Enviar <b>e-mail</b> para a04qdr04</a></p>'
            '<p><a href="a04qdr08">Enviar e-mail para mim</a></p>'
            '</root>'
        raw, transformed = self._transform(text, self.pipeline.APipe())

        nodes = transformed.findall('.//p')
        self.assertEqual(len(nodes), 4)
        texts = [
            b'<p>Enviar e-mail para A <email>a@scielo.org</email></p>',
            b'<p><img src="mail.gif"/> <email>x@scielo.org</email></p>',
            b'<p>Enviar e-mail para a04qdr04 <email>a04qdr04@scielo.org</email></p>',
            b'<p>Enviar e-mail para mim <email>a04qdr08@scielo.org</email></p>',
        ]
        for node, text in zip(nodes, texts):
            with self.subTest(node=node):
                self.assertEqual(text, etree.tostring(node).strip())

        node = self.etreeXML.find(".//font[@size='1']/a")
        data = self.etreeXML, node
        self.pipeline.APipe().transform(data)

        self.assertEqual(node.attrib["rid"], "home")

    """
    def test_pipe_a_hiperlink(self):

        text = [
            '<root>',
            '<p><a href="https://new.scielo.br"/></p>',
            '<p><a href="https://www.google.com"><img src="mail.gif"/></a></p>',
            '<p><a href="https://www.bbc.com">BBC</a></p>',
            '<p><a href="http://www.bbc.com">Enviar <b>e-mail para</b> mim</a></p>',
            '</root>',
        ]
        text = ''.join(text)
        raw, transformed = self._transform(text, self.pipeline.APipe())

        nodes = transformed.findall('.//ext-link')
        self.assertEqual(len(nodes), 4)
        data = [
            ('https://new.scielo.br', b''),
            ('https://www.google.com', b'<img src="mail.gif"/>'),
            ('https://www.bbc.com', b'BBC'),
            ('http://www.bbc.com', b'Enviar <b>e-mail para</b> mim'),
        ]
        for node, item in zip(nodes, data):
            link, content = item
            with self.subTest(node=node):
                self.assertIn(content, etree.tostring(node).strip())
                self.assertEqual(link, node.attrib['{http://www.w3.org/1999/xlink}href'])
                self.assertEqual('uri', node.attrib['ext-link-type'])
                self.assertEqual(len(node.attrib), 2)

    def test_pipe_remove_a_without_href(self):
        text = '<root><a>Teste</a></root>'
        raw, transformed = self._transform(text, self.pipeline.APipe())
        self.assertIsNone(transformed.find('.//a'))

    def test__process(self):
        def f(node):
            node.tag = node.tag.upper()
            return node

        apply_change = ("div", "img", "i")

        tags = ("div", "img", "i", "p")
        expected_tags = ("DIV", "IMG", "I", "p")
        text = '<root><div>bla</div><img>bla</img><p>bla</p><i>bla</i></root>'
        tree = etree.fromstring(text)
        for tag, expected_tag in zip(tags, expected_tags):
            with self.subTest(tag=tag):
                if tag in apply_change:
                    _process(tree, tag, f)

                found = tree.findall(".//%s" % expected_tag)
                self.assertIsNotNone(found)
