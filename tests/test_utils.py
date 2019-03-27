import os
import unittest
from unittest.mock import patch
from lxml import etree
from documentstore_migracao.utils import files, xml, request, dicts

from . import SAMPLES_PATH, COUNT_SAMPLES_FILES


class TestUtilsFiles(unittest.TestCase):
    def test_list_dir(self):
        self.assertEqual(len(files.list_dir(SAMPLES_PATH)), COUNT_SAMPLES_FILES)

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

    @patch("documentstore_migracao.utils.xml.etree.fromstring")
    def test_str2objXML_except(self, mk_fromstring):
        def _side_effect(arg):
            if arg == "<body></body>":
                return b"<body></body>"
            raise etree.XMLSyntaxError("Test Error - READING XML", 1, 1, 1)

        mk_fromstring.side_effect = _side_effect
        obj = xml.str2objXML("<a><b>bar</b></a>")

        self.assertIn(b"<body></body>", obj)

    def test_find_medias(self):

        with open(os.path.join(SAMPLES_PATH, "S0036-36341997000100003.xml"), "r") as f:
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


class TestUtilsDicts(unittest.TestCase):
    def test_merge(self):
        result = {"1": {"count": 2, "files": ("a", "b")}}

        data = {"count": 1, "files": ("c", "d")}
        dicts.merge(result, "1", data)
        self.assertEqual(result["1"]["count"], 3)

    def test_group(self):
        groups = dicts.group(range(10), 3)
        self.assertEqual(list(groups)[0], (0, 1, 2))

    def test_grouper(self):
        result = dicts.grouper(3, "abcdefg", "x")
        self.assertEqual(list(result)[0], ("a", "b", "c"))
