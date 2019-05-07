import os
import unittest
from unittest.mock import patch, ANY

from documentstore_migracao.main.tools import tools_parser
from documentstore_migracao.tools import generation, constructor
from . import utils, SAMPLES_PATH, COUNT_SAMPLES_FILES


class TestMainTools(unittest.TestCase):
    @patch("documentstore_migracao.tools.generation.article_ALL_html_generator")
    def test_arg_generationFiles(self, mk_article_ALL_html_generator):

        with utils.environ(VALID_XML_PATH="/tmp", GENERATOR_PATH="/tmp"):
            tools_parser(["generation"])
            mk_article_ALL_html_generator.assert_called_once_with("/tmp", "/tmp")

    @patch("documentstore_migracao.tools.constructor.article_ALL_constructor")
    def test_arg_constructionFiles(self, mk_article_ALL_constructor):

        with utils.environ(VALID_XML_PATH="/tmp", CONSTRUCTOR_PATH="/tmp"):
            tools_parser(["construction"])
            mk_article_ALL_constructor.assert_called_once_with("/tmp", "/tmp")


class TestProcessingConstructor(unittest.TestCase):
    @patch("documentstore_migracao.tools.constructor.xml.objXML2file")
    def test_article_xml_constructor(self, mk_write_file):

        constructor.article_xml_constructor(
            os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml"), "/tmp"
        )
        mk_write_file.assert_called_with(
            "/tmp/S0044-59672003000300001.pt.xml", ANY, pretty=True
        )

    @patch("documentstore_migracao.tools.constructor.article_xml_constructor")
    def test_article_ALL_constructor(self, mk_article_xml_constructor):

        constructor.article_ALL_constructor(SAMPLES_PATH, "/tmp")
        mk_article_xml_constructor.assert_called_with(ANY, "/tmp")

    @patch("documentstore_migracao.tools.constructor.article_xml_constructor")
    def test_article_ALL_constructor_with_exception(self, mk_article_xml_constructor):

        mk_article_xml_constructor.side_effect = KeyError("Test Error - constructor")
        with self.assertLogs("documentstore_migracao.tools.constructor") as log:
            constructor.article_ALL_constructor(SAMPLES_PATH, "/tmp")

        has_message = False
        for log_message in log.output:
            if "Test Error - constructor" in log_message:
                has_message = True
        self.assertTrue(has_message)


class TestProcessingGeneration(unittest.TestCase):
    def test_article_html_generator(self):

        filename = "/tmp/S0044-59672003000300001.pt.pt.html"
        try:
            generation.article_html_generator(
                os.path.join(SAMPLES_PATH, "S0044-59672003000300001.pt.xml"), "/tmp"
            )
            with open(filename, "r") as f:
                text = f.read()

        finally:
            os.remove(filename)

        self.assertIn("S0044-59672003000300001", text)

    @patch("documentstore_migracao.tools.generation.article_html_generator")
    def test_article_ALL_html_generator(self, mk_article_html_generator):

        generation.article_ALL_html_generator(SAMPLES_PATH, "/tmp")
        mk_article_html_generator.assert_called_with(ANY, "/tmp")
        self.assertEqual(len(mk_article_html_generator.mock_calls), COUNT_SAMPLES_FILES)

    @patch("documentstore_migracao.tools.generation.article_html_generator")
    def test_article_ALL_html_generator_with_exception(self, mk_article_html_generator):

        mk_article_html_generator.side_effect = KeyError("Test Error - Generation")
        with self.assertLogs("documentstore_migracao.tools.generation") as log:
            generation.article_ALL_html_generator(SAMPLES_PATH, "/tmp")

        has_message = False
        for log_message in log.output:
            if "Test Error - Generation" in log_message:
                has_message = True
        self.assertTrue(has_message)

    def test_not_arg(self):

        with self.assertRaises(SystemExit) as cm:
            tools_parser([])
            self.assertEqual("Vc deve escolher algum parametro", str(cm.exception))
