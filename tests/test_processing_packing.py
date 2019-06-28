import os
import shutil
import unittest
from unittest.mock import patch, ANY, Mock

from lxml import etree
from documentstore_migracao.utils.request import HTTPGetError

from documentstore_migracao.processing import packing
from . import utils, SAMPLES_PATH, TEMP_TEST_PATH, COUNT_SAMPLES_FILES


class TestProcessingPacking(unittest.TestCase):
    def test_pack_article_xml_missing_media(self):
        with utils.environ(
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
        ):
            packing.pack_article_xml(
                os.path.join(SAMPLES_PATH, "S0044-59672003000300002_sps_incompleto.xml")
            )
            files = set(
                os.listdir(
                    os.path.join(
                        SAMPLES_PATH,
                        "S0044-59672003000300002_sps_incompleto_INCOMPLETE",
                    )
                )
            )
            self.assertEqual(
                {
                    "1809-4392-aa-33-03-353-370-gv33n3a02.pdf",
                    "1809-4392-aa-33-03-353-370-ga02fig01.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab03.gif",
                    "1809-4392-aa-33-03-353-370-ga02fig02.jpg",
                    "1809-4392-aa-33-03-353-370-ga02tab04.gif",
                    "1809-4392-aa-33-03-353-370.err",
                    "1809-4392-aa-33-03-353-370-ga02fr01.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab05.gif",
                    "1809-4392-aa-33-03-353-370.xml",
                    "1809-4392-aa-33-03-353-370-ga02tab02.gif",
                },
                files,
            )
            self.assertEqual(10, len(files))

    def test_pack_article_xml_has_media(self):
        with utils.environ(
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
            SCIELO_COLLECTION="scl",
        ):
            packing.pack_article_xml(
                os.path.join(SAMPLES_PATH, "S0044-59672003000300002_sps_completo.xml")
            )
            files = set(
                os.listdir(
                    os.path.join(SAMPLES_PATH, "S0044-59672003000300002_sps_completo")
                )
            )
            self.assertEqual(
                {
                    "1809-4392-aa-33-03-353-370-ga02tab04.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab05.gif",
                    "1809-4392-aa-33-03-353-370-ga02fig02.jpg",
                    "1809-4392-aa-33-03-353-370-ga02tab02.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab03.gif",
                    "1809-4392-aa-33-03-353-370-ga02fr01.gif",
                    "1809-4392-aa-33-03-353-370.xml",
                    "1809-4392-aa-33-03-353-370-ga02fig01.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab01a.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab01b.gif",
                    "1809-4392-aa-33-03-353-370-gv33n3a02.pdf",
                },
                files,
            )
            self.assertEqual(11, len(files))

    def test_pack_article_xml_has_no_media(self):
        with utils.environ(
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
        ):
            packing.pack_article_xml(os.path.join(SAMPLES_PATH, "any.xml"))
            files = set(os.listdir(os.path.join(SAMPLES_PATH, "any")))
            self.assertEqual({"any.xml"}, files)
            self.assertEqual(1, len(files))

    @patch("documentstore_migracao.processing.packing.pack_article_xml")
    def test_pack_article_ALLxml(self, mk_pack_article_xml):

        with utils.environ(VALID_XML_PATH=SAMPLES_PATH):
            packing.pack_article_ALLxml()
            mk_pack_article_xml.assert_called_with(ANY)
            self.assertEqual(len(mk_pack_article_xml.mock_calls), COUNT_SAMPLES_FILES)

    @patch("documentstore_migracao.processing.packing.pack_article_xml")
    def test_pack_article_ALLxml_with_errors(self, mk_pack_article_xml):

        mk_pack_article_xml.side_effect = [
            PermissionError("Permission error message"),
            OSError("OSError message"),
            etree.Error(ANY),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            OSError("OSError message"),
            None,
            None,
        ]

        with utils.environ(VALID_XML_PATH=SAMPLES_PATH):
            with self.assertLogs("documentstore_migracao.processing.packing") as log:
                packing.pack_article_ALLxml()

            msg = []
            for log_message in log.output:
                if "Falha no empacotamento" in log_message:
                    msg.append(log_message)
            self.assertEqual(len(msg), 4)


class TestProcessingPackingDownloadAsset(unittest.TestCase):
    def setUp(self):
        if os.path.isdir(TEMP_TEST_PATH):
            shutil.rmtree(TEMP_TEST_PATH)
        os.makedirs(TEMP_TEST_PATH)

        new_fname = "novo"
        dest_path = TEMP_TEST_PATH
        self.dest_filename = os.path.join(dest_path, new_fname + ".gif")
        if os.path.isfile(self.dest_filename):
            os.unlink(self.dest_filename)

    def tearDown(self):
        shutil.rmtree(TEMP_TEST_PATH)

    @patch("documentstore_migracao.utils.request.get")
    def test_download_asset(self, request_get):
        request_get.return_value.ok = True
        request_get.return_value.content = b"conteudo"
        old_path = "/img/en/scielobre.gif"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        self.assertFalse(os.path.isfile(self.dest_filename))
        error = packing.download_asset(old_path, new_fname, dest_path)
        self.assertIsNone(error)
        with open(self.dest_filename) as fp:
            self.assertTrue(fp.read(), b"conteudo")

    @patch("documentstore_migracao.utils.request.get")
    def test_download_asset_raise_HTTPGetError_exception(self, mk_request_get):
        mk_request_get.side_effect = HTTPGetError
        old_path = "/img/en/scielobre.gif"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        error = packing.download_asset(old_path, new_fname, dest_path)
        self.assertIsNotNone(error)


class TestProcessingpack_PackingAssets(unittest.TestCase):
    def setUp(self):
        if os.path.isdir(TEMP_TEST_PATH):
            shutil.rmtree(TEMP_TEST_PATH)
        os.makedirs(TEMP_TEST_PATH)
        self.good_pkg_path = os.path.join(TEMP_TEST_PATH, "good")
        self.bad_pkg_path = os.path.join(TEMP_TEST_PATH, "bad")

    def tearDown(self):
        shutil.rmtree(TEMP_TEST_PATH)

    @patch("documentstore_migracao.utils.request.get")
    def test__pack_incomplete_package(self, mk_request_get):
        asset_replacements = [
            ("/img/revistas/a01.gif", "f01"),
            ("/img/revistas/a02.gif", "f02"),
        ]
        m = Mock()
        m.content = b"conteudo"
        pkg_path = self.good_pkg_path
        bad_pkg_path = self.bad_pkg_path
        pkg_name = "pacote_sps"

        mk_request_get.side_effect = [HTTPGetError("Error"), m]
        result_path = packing.packing_assets(
            asset_replacements, pkg_path, bad_pkg_path, pkg_name
        )
        self.assertEqual(result_path, bad_pkg_path)
        self.assertFalse(os.path.isdir(pkg_path))
        self.assertEqual(["f02.gif", pkg_name + ".err"], os.listdir(bad_pkg_path))
        with open(os.path.join(bad_pkg_path, pkg_name + ".err")) as fp:
            self.assertEqual(fp.read(), "/img/revistas/a01.gif f01 Error")

    @patch("documentstore_migracao.utils.request.get")
    def test__pack_incomplete_package_same_dir(self, mk_request_get):
        asset_replacements = [
            ("/img/revistas/a01.gif", "f01"),
            ("/img/revistas/a02.gif", "f02"),
        ]
        m = Mock()
        m.content = b"conteudo"
        pkg_path = self.good_pkg_path
        bad_pkg_path = self.good_pkg_path
        renamed_path = pkg_path + "_INCOMPLETE"
        pkg_name = "pacote_sps"
        mk_request_get.side_effect = [HTTPGetError("Error"), m]
        result_path = packing.packing_assets(
            asset_replacements, pkg_path, bad_pkg_path, pkg_name
        )
        self.assertEqual(result_path, renamed_path)
        self.assertFalse(os.path.isdir(pkg_path))
        self.assertEqual(["f02.gif", pkg_name + ".err"], os.listdir(renamed_path))
        with open(os.path.join(renamed_path, pkg_name + ".err")) as fp:
            self.assertEqual(fp.read(), "/img/revistas/a01.gif f01 Error")

    @patch("documentstore_migracao.utils.request.get")
    def test__pack_complete_package(self, mk_request_get):
        asset_replacements = [
            ("/img/revistas/a01.gif", "f01"),
            ("/img/revistas/a02.gif", "f02"),
        ]
        mk_request_get_result1 = Mock()
        mk_request_get_result1.content = b"conteudo"
        mk_request_get_result2 = Mock()
        mk_request_get_result2.content = b"conteudo"

        pkg_path = self.good_pkg_path
        bad_pkg_path = self.bad_pkg_path
        pkg_name = "pacote_sps"
        mk_request_get.side_effect = [mk_request_get_result1, mk_request_get_result2]
        result_path = packing.packing_assets(
            asset_replacements, pkg_path, bad_pkg_path, pkg_name
        )
        self.assertEqual(result_path, pkg_path)
        self.assertFalse(os.path.isdir(bad_pkg_path))
        self.assertEqual({"f01.gif", "f02.gif"}, set(os.listdir(pkg_path)))
