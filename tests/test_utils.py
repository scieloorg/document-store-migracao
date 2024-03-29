import os
import unittest
import tempfile
from requests.exceptions import HTTPError
from unittest.mock import patch, MagicMock
from lxml import etree
from documentstore_migracao.utils.string import normalize
from documentstore_migracao.utils import files, xml, request, dicts, string

from . import SAMPLES_PATH, COUNT_SAMPLES_FILES


class TestUtilsFiles(unittest.TestCase):
    def test_extract_filename_ext_by_path(self):
        filename, extension = files.extract_filename_ext_by_path(
            "xml/conversion/S0044-59672014000400003/S0044-59672014000400003.pt.xml"
        )
        self.assertEqual(filename, "S0044-59672014000400003")
        self.assertEqual(extension, ".xml")

    def test_xml_files_list(self):
        self.assertEqual(len(files.xml_files_list(SAMPLES_PATH)), COUNT_SAMPLES_FILES)

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

    def test_write_binary_file(self):
        expected_text = b"<a><b>bar</b></a>"
        filename = "foo_test_binary.txt"

        try:
            files.write_file_binary(filename, expected_text)

            with open(filename, "rb") as f:
                text = f.read()
        finally:
            os.remove(filename)

        self.assertEqual(expected_text, text)

    @patch("documentstore_migracao.utils.files.shutil.move")
    def test_move_xml_to(self, mk_move):

        files.move_xml_to("test.xml", "/tmp/xml/source", "/tmp/xml/destiny")
        mk_move.assert_called_once_with(
            "/tmp/xml/source/test.xml", "/tmp/xml/destiny/test.xml"
        )

    def test_create_dir_exist(self):
        self.assertFalse(files.create_dir("/tmp"))

    def test_create_dir_not_exist(self):
        try:
            files.create_dir("/tmp/create_dir")
            self.assertTrue(os.path.exists("/tmp/create_dir"))

        finally:
            os.rmdir("/tmp/create_dir")

    def test_create_path_by_file(self):
        try:
            path = files.create_path_by_file(
                "/tmp/",
                "/xml/conversion/S0044-59672014000400003/S0044-59672014000400003.pt.xml",
            )

            self.assertEqual("/tmp/S0044-59672014000400003", path)
            self.assertTrue(os.path.exists("/tmp/S0044-59672014000400003"))

        finally:
            os.rmdir("/tmp/S0044-59672014000400003")

    def test_sha1(self):
        str_hash = files.sha1(os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml"))
        self.assertEqual("16667b1e875308e3387091fb6203a9da25e03d28", str_hash)


class TestString(unittest.TestCase):
    def test_string_normalize_excludes_exceding_spaces(self):
        text = "<a><b>barão  </b>             \t\n<b>serão</b></a>"
        expected_text = "<a><b>barão </b> <b>serão</b></a>"
        resultado = normalize(text)
        self.assertEqual(expected_text, resultado)


class TestUtilsXML(unittest.TestCase):
    def test_str2objXML(self):
        expected_text = "<a><b>barão</b></a>"
        obj = xml.str2objXML(expected_text)
        self.assertIn(expected_text, etree.tostring(obj, encoding="unicode"))

    def test_file2objXML(self):
        file_path = os.path.join(SAMPLES_PATH, "any.xml")
        expected_text = "<root><a><b>bar</b></a></root>"
        obj = xml.file2objXML(file_path)
        self.assertIn(expected_text, str(etree.tostring(obj)))

    def test_file2objXML_raise_LoadToXMLError_for_filenotfound(self):
        file_path = os.path.join(SAMPLES_PATH, "none.xml")
        with self.assertRaises(xml.LoadToXMLError):
            xml.file2objXML(file_path)

    def test_file2objXML_raise_XMLSyntaxError_for_filenotfound(self):
        file_path = os.path.join(SAMPLES_PATH, "file.txt")
        with self.assertRaises(Exception):
            xml.file2objXML(file_path)

    def test_objXML2file(self):
        xml_obj = etree.fromstring(
            """<root>
                <p>TEXTO é ç á à è</p>
            </root>"""
        )
        test_dir = tempfile.mkdtemp()
        file_name = os.path.join(test_dir, "test.xml")
        xml.objXML2file(file_name, xml_obj)
        with open(file_name) as f:
            text = f.read()
            self.assertIn("<?xml version='1.0' encoding='utf-8'?>", text)
            self.assertIn("é ç á à è", text)


class TestUtilsRequest(unittest.TestCase):
    @patch("documentstore_migracao.utils.request.requests")
    def test_get(self, mk_requests):

        expected = {"params": {"collection": "spa"}}
        request.get("http://api.test.com", **expected)
        mk_requests.get.assert_called_once_with("http://api.test.com", **expected)

    @patch("documentstore_migracao.utils.request.requests")
    def test_get_raises_exception_if_requests_exception(self, mk_requests):
        mk_response = MagicMock()
        mk_response.raise_for_status.side_effect = HTTPError
        mk_requests.get.return_value = mk_response
        self.assertRaises(
            request.HTTPGetError, request.get, "http://api.test.com", **{}
        )


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


class TestReferencesNumberExtract(unittest.TestCase):
    def test_extract_2_from_reference_text(self):
        self.assertEqual("2", xml.extract_reference_order("2. ref"))

    def test_should_extract_2_when_are_spaces_between_number_and_text(self):
        self.assertEqual("2", xml.extract_reference_order("2   ref"))

    def test_should_extract_2_when_the_number_is_inner_a_html_tag(self):
        self.assertEqual("2", xml.extract_reference_order("<span>2<span>"))

    def test_should_return_an_empty_string_when_does_not_extract_the_reference_order(
        self
    ):
        self.assertEqual("", xml.extract_reference_order("ref ref ref ref"))

    def test_should_return_an_empty_string_when_the_number_is_an_parameter_value(self):
        self.assertEqual("", xml.extract_reference_order("<font size='2'>ref</font>"))


class TestXMLUtilsRemoveElements(unittest.TestCase):
    def setUp(self):
        self.xmltree = etree.fromstring(
            "<article><meta><body><p>text</p><p>second text</p></body></meta></article>"
        )

    def test_should_remove_only_first_p_element_from_body(self):
        xml.remove_element(self.xmltree.find(".//body"), ".//p")
        self.assertNotIn(b"<p>text</p>", etree.tostring(self.xmltree))
        self.assertIn(b"<p>second text</p>", etree.tostring(self.xmltree))


class TestFixNamespacePrefixW(unittest.TestCase):
    def test_fix_namespace_prefix_w_fixes_content(self):
        content = ' w:atributo="abc"'
        expected = ' w-atributo="abc"'
        self.assertEqual(xml.fix_namespace_prefix_w(content), expected)

    def test_fix_namespace_prefix_w_does_not_fix_content_because_it_does_not_match(self):
        items = [
            'w:attr= "abc"',
            'w:attr ="abc"',
            'w: attr="abc"',
            'w :attr="abc"',
        ]
        for item in items:
            with self.subTest(item):
                self.assertEqual(xml.fix_namespace_prefix_w(item), item)
