import os
import unittest
from unittest.mock import patch
from lxml import etree

from documentstore_migracao.utils import files, xml, request
from documentstore_migracao.utils.convert_html_body import Convert2SPSBody
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

    def test_parser_body_xml(self):
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


class TestConvert2SPSBody(unittest.TestCase):
    def setUp(self):
        filename = os.path.join(SAMPLES_PATH, "example_convert_html.xml")
        with open(filename, "r") as f:
            self.xml_txt = f.read()

        self.etreeXML = etree.fromstring(self.xml_txt)
        self.convert = Convert2SPSBody("<samples />")

    def test_create_instance(self):
        expected_text = "<p>La nueva epoca de la revista<italic>Salud Publica de Mexico </italic></p>"
        obj = Convert2SPSBody(expected_text)

        self.assertIn(expected_text, str(etree.tostring(obj.obj_xml)))

    def test_parser_p(self):
        node = self.etreeXML.find(".//p")
        self.convert.parser_p(node)
        self.assertEqual(node.attrib, {})

    def test_parser_div(self):
        node = self.etreeXML.find(".//div")
        self.convert.parser_div(node)
        self.assertEqual(node.attrib["id"], "home")

    def test_parser_img(self):
        node = self.etreeXML.find(".//img")
        self.convert.parser_img(node)

        self.assertIn("class", node.attrib.keys())
        self.assertIn("a04qdr04.gif", node.attrib["{http://www.w3.org/1999/xlink}href"])

    def test_parser_li(self):
        node = self.etreeXML.find(".//li")
        self.convert.parser_li(node)

        self.assertEqual(node.tag, "list-item")

    def test_parser_ol(self):
        node = self.etreeXML.find(".//ol")
        self.convert.parser_ol(node)

        self.assertEqual("order", node.attrib["list-type"])

    def test_parser_ul(self):
        node = self.etreeXML.find(".//ul")
        self.convert.parser_ul(node)

        self.assertEqual("bullet", node.attrib["list-type"])

    def test_parser_i(self):
        node = self.etreeXML.find(".//i")
        self.convert.parser_i(node)

        self.assertEqual(node.tag, "italic")

    def test_parser_b(self):
        node = self.etreeXML.find(".//b")
        self.convert.parser_b(node)

        self.assertEqual(node.tag, "bold")

    def test_parser_a_mail(self):
        node = self.etreeXML.find(".//font[@size='2']/a")
        self.convert.parser_a(node)

        self.assertEqual(node.text, "lugope2@hotmail.com.mx")

    def test_parser_a_anchor(self):
        node = self.etreeXML.find(".//font[@size='1']/a")
        self.convert.parser_a(node)

        self.assertEqual(node.attrib["rid"], "home")

    def test_parser_a_hiperlink(self):
        node = self.etreeXML.find(".//font[@size='3']/a")
        self.convert.parser_a(node)

        self.assertEqual(node.attrib["ext-link-type"], "uri")

    def test_parser_a_keyError(self):
        node = self.etreeXML.find(".//font[@size='4']/a")
        with self.assertLogs("documentstore_migracao.utils.convert_html_body") as log:
            self.convert.parser_a(node)

        has_message = False
        for log_message in log.output:
            if "Tag 'a' sem href removendo node do xml" in log_message:
                has_message = True
        self.assertTrue(has_message)

    def test_process(self):
        obj = Convert2SPSBody(self.xml_txt)
        obj.process()

        tags = ("div", "img", "li", "ol", "ul", "i", "b", "a")
        for tag in tags:
            with self.subTest(tag=tag):
                expected = obj.obj_xml.findall(".//%s" % tag)
                self.assertFalse(expected)
