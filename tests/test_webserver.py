import unittest
from webtest import TestApp
from pyramid import testing
from documentstore_migracao.webserver import views, main
from . import utils, SAMPLES_PATH, COUNT_SAMPLES_FILES


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_list_converted_xml_view(self):

        request = testing.DummyRequest()
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH, VALID_XML_PATH=''):
            info = views.list_converted_xml_view(request)
            self.assertEqual(info["page_title"], "Lista de XMLS Convertidos")
            self.assertEqual(len(info["xmls"]), COUNT_SAMPLES_FILES)

    def test_render_html_converted_view(self):
        request = testing.DummyRequest()
        request.matchdict = {
            "file_xml": "S0044-59672003000300001.pt.xml",
            "language": "pt",
        }
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH, VALID_XML_PATH=''):
            info = views.render_html_converted_view(request)
            self.assertIn("Luiz Antonio de Oliveira", str(info))


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        app = main({})
        self.testapp = TestApp(app)

    def test_root(self):
        with utils.environ(CONVERSION_PATH=SAMPLES_PATH, VALID_XML_PATH=''):
            res = self.testapp.get("/", status=200)
            self.assertTrue(b"Lista de XMLS Convertidos" in res.body)
