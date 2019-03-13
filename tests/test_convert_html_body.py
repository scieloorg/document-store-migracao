import os
import unittest
from unittest.mock import patch
from lxml import etree

from documentstore_migracao.utils import files, xml, request
from documentstore_migracao.utils.convert_html_body import HTML2SPSPipeline
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
    def get_tree(self, text):
        return etree.fromstring(text)

    def setUp(self):
        filename = os.path.join(SAMPLES_PATH, "example_convert_html.xml")
        with open(filename, "r") as f:
            self.xml_txt = f.read()
        self.etreeXML = etree.fromstring(self.xml_txt)
        self.convert = HTML2SPSPipeline()

    def test_create_instance(self):
        expected_text = "<p>La nueva epoca de la revista<italic>Salud Publica de Mexico </italic></p>"
        pipeline = HTML2SPSPipeline()
        raw, xml = pipeline.SetupPipe().transform(expected_text)
        self.assertIn(expected_text, str(etree.tostring(xml)))

    def test_pipe_p(self):
        text = '<root><p align="x">bla</p><p baljlba="1"/></root>'
        raw = self.get_tree(text)
        data = text, raw
        raw, transformed = self.convert.PPipe().transform(data)
        self.assertEqual(raw, text)
        self.assertEqual(b"<root><p>bla</p><p/></root>", etree.tostring(transformed))

    def test_pipe_div(self):
        text = '<root><div align="x" id="intro">bla</div><div baljlba="1"/></root>'
        raw = self.get_tree(text)
        data = text, raw
        raw, transformed = self.convert.DivPipe().transform(data)
        self.assertEqual(raw, text)
        self.assertEqual(b'<root><sec id="intro">bla</sec><sec/></root>', etree.tostring(transformed))

    def test_pipe_img(self):
        text = '<root><img align="x" src="a04qdr04.gif"/><img align="x" src="a04qdr08.gif"/></root>'
        raw = self.get_tree(text)
        data = text, raw
        raw, transformed = self.convert.ImgPipe().transform(data)
        self.assertEqual(raw, text)
        nodes = transformed.findall('.//graphic')
        self.assertEqual(len(nodes), 2)
        for node, href in zip(nodes, ["a04qdr04.gif", "a04qdr08.gif"]):
            with self.subTest(node=node):
                self.assertEqual(href, node.attrib["{http://www.w3.org/1999/xlink}href"])
                self.assertEqual(len(node.attrib), 1)


"""

    def test_pipe_li(self):
        node = self.etreeXML.find(".//li")
        data = self.etreeXML, node
        self.convert.LiPipe().transform(data)

        self.assertEqual(node.tag, "list-item")

    def test_pipe_ol(self):
        node = self.etreeXML.find(".//ol")
        data = self.etreeXML, node
        self.convert.OlPipe().transform(data)

        self.assertEqual("order", node.attrib["list-type"])

    def test_pipe_ul(self):
        node = self.etreeXML.find(".//ul")
        data = self.etreeXML, node
        self.convert.UlPipe().transform(data)

        self.assertEqual("bullet", node.attrib["list-type"])

    def test_pipe_i(self):
        node = self.etreeXML.find(".//i")
        data = self.etreeXML, node
        self.convert.IPipe().transform(data)

        self.assertEqual(node.tag, "italic")

    def test_pipe_b(self):
        node = self.etreeXML.find(".//b")
        data = self.etreeXML, node
        self.convert.BPipe().transform(data)

        self.assertEqual(node.tag, "bold")

    def test_pipe_a_mail(self):
        node = self.etreeXML.find(".//font[@size='2']/a")
        data = self.etreeXML, node
        self.convert.APipe().transform(data)

        self.assertEqual(node.text, "lugope2@hotmail.com.mx")

    def test_pipe_a_anchor(self):
        node = self.etreeXML.find(".//font[@size='1']/a")
        data = self.etreeXML, node
        self.convert.APipe().transform(data)

        self.assertEqual(node.attrib["rid"], "home")

    def test_pipe_a_hiperlink(self):
        node = self.etreeXML.find(".//font[@size='3']/a")
        data = self.etreeXML, node
        self.convert.APipe().transform(data)

        self.assertEqual(node.attrib["ext-link-type"], "uri")

    def test_pipe_a_keyError(self):
        node = self.etreeXML.find(".//font[@size='4']/a")
        data = self.etreeXML, node
        with self.assertLogs("documentstore_migracao.utils.convert_html_body") as log:
            self.convert.APipe().transform(data)

        has_message = False
        for log_message in log.output:
            if "Tag 'a' sem href removendo node do xml" in log_message:
                has_message = True
        self.assertTrue(has_message)

    def test_process(self):
        obj = HTML2SPSPipeline().deploy(self.xml_txt)
        
        tags = ("div", "img", "li", "ol", "ul", "i", "b", "a")
        for tag in tags:
            with self.subTest(tag=tag):
                expected = obj.obj_xml.findall(".//%s" % tag)
                self.assertFalse(expected)
"""
