import os
import json
import shutil
import unittest
from unittest.mock import patch, ANY, Mock

from documentstore_migracao.processing import packing
from . import utils, SAMPLES_PATH, TEMP_TEST_PATH, COUNT_SAMPLES_FILES


class TestProcessingPacking(unittest.TestCase):

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test_pack_article_xml_missing_media(self, mk_read_file_binary):
        with utils.environ(
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
        ):

            mk_read_file_binary.return_value = b"img content"

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
                    "1809-4392-aa-33-03-353-370-ga02fig01.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab03.gif",
                    "1809-4392-aa-33-03-353-370-ga02fig02.jpg",
                    "1809-4392-aa-33-03-353-370-ga02tab04.gif",
                    "1809-4392-aa-33-03-353-370.err",
                    "1809-4392-aa-33-03-353-370-ga02fr01.gif",
                    "1809-4392-aa-33-03-353-370-ga02tab05.gif",
                    "1809-4392-aa-33-03-353-370.xml",
                    "1809-4392-aa-33-03-353-370-ga02tab02.gif",
                    "v33n3a02.pdf",
                    "manifest.json",
                },
                files,
            )
            self.assertEqual(11, len(files))

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
                    "v33n3a02.pdf",
                    "manifest.json",
                },
                files,
            )
            self.assertEqual(12, len(files))

    @patch("documentstore_migracao.processing.packing.SPS_Package.get_renditions_metadata")
    @patch("documentstore_migracao.processing.packing.get_asset")
    def test_pack_article_write_manifest_json_file_with_renditions(
        self, mk_get_asset, mk_get_renditions_metadata
    ):
        with utils.environ(
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
            SCIELO_COLLECTION="scl",
        ):
            mk_get_asset.return_value = None
            mk_get_renditions_metadata.return_value = (
                [
                    ("http://scielo.br/a01.pdf", "a01"),
                    ("http://scielo.br/pt_a01.pdf", "pt_a01"),
                ],
                {
                    'en': 'http://www.scielo.br/pdf/aa/v1n1/a01.pdf',
                    'pt': 'http://www.scielo.br/pdf/aa/v1n1/pt_a01.pdf',
                }
            )
            xml_path_dir = os.path.join(SAMPLES_PATH, "S0044-59672003000300002_sps_completo.xml")
            packing.pack_article_xml(xml_path_dir)
            manifest_file = os.path.join(
                SAMPLES_PATH, "S0044-59672003000300002_sps_completo", "manifest.json")
            with open(manifest_file) as f:
                self.assertEqual(
                    json.loads(f.read()),
                    {
                        'en': 'http://www.scielo.br/pdf/aa/v1n1/a01.pdf',
                        'pt': 'http://www.scielo.br/pdf/aa/v1n1/pt_a01.pdf',
                    }
                )

    def test_pack_article_xml_has_no_media(self):
        with utils.environ(
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
        ):
            packing.pack_article_xml(os.path.join(SAMPLES_PATH, "any.xml"))
            files = set(os.listdir(os.path.join(SAMPLES_PATH, "any")))
            self.assertEqual({"any.xml", "manifest.json"}, files)
            self.assertEqual(2, len(files))

    @patch("documentstore_migracao.processing.packing.pack_article_xml")
    def test_pack_article_ALLxml(self, mk_pack_article_xml):

        with utils.environ(VALID_XML_PATH=SAMPLES_PATH):
            packing.pack_article_ALLxml()
            mk_pack_article_xml.assert_called_with(file_xml_path=ANY, poison_pill=ANY)
            self.assertEqual(len(mk_pack_article_xml.mock_calls), COUNT_SAMPLES_FILES)


class TestProcessingPackingGetAsset(unittest.TestCase):
    def setUp(self):
        if os.path.isdir(TEMP_TEST_PATH):
            shutil.rmtree(TEMP_TEST_PATH)
        os.makedirs(TEMP_TEST_PATH)

        new_fname = "novo"
        dest_path = TEMP_TEST_PATH
        self.dest_filename_img = os.path.join(dest_path, new_fname + ".gif")
        self.dest_filename_pdf = os.path.join(dest_path, new_fname + ".pdf")
        if os.path.isfile(self.dest_filename_img):
            os.unlink(self.dest_filename_img)

    def tearDown(self):
        shutil.rmtree(TEMP_TEST_PATH)

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test_get_asset(self, read_file_binary):
        read_file_binary.return_value = b"conteudo"
        old_path = "/img/en/scielobre.gif"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        self.assertFalse(os.path.isfile(self.dest_filename_img))
        path = packing.get_asset(old_path, new_fname, dest_path)
        self.assertIsNone(path)
        with open(self.dest_filename_img) as fp:
            self.assertTrue(fp.read(), b"conteudo")

    def test_get_asset_img_path(self):
        with utils.environ(
            SOURCE_IMG_FILE=os.path.join(os.path.dirname(__file__), "samples"),
        ):
            old_path = "/img/sample.jpg"
            new_fname = "novo"
            dest_path = TEMP_TEST_PATH

            self.assertFalse(os.path.isfile(self.dest_filename_img))
            packing.get_asset(old_path, new_fname, dest_path)

            img_new_path = os.path.join(dest_path, new_fname + ".jpg")
            self.assertTrue(os.path.exists(img_new_path))

    def test_get_asset_pdf_path(self):
        with utils.environ(
            SOURCE_PDF_FILE=os.path.join(os.path.dirname(__file__), "samples"),
        ):
            old_path = "/pdf/sample.pdf"
            new_fname = "novo"
            dest_path = TEMP_TEST_PATH

            self.assertFalse(os.path.isfile(self.dest_filename_pdf))
            packing.get_asset(old_path, new_fname, dest_path)

            pdf_new_path = os.path.join(dest_path, new_fname + ".pdf")
            self.assertTrue(os.path.exists(pdf_new_path))

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test_get_asset_in_img_folder(self, read_file_binary):
        read_file_binary.return_value = b"conteudo img"
        old_path = "/img/en/scielobre.gif"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        self.assertFalse(os.path.isfile(self.dest_filename_img))

        path = packing.get_asset(old_path, new_fname, dest_path)

        self.assertIsNone(path)

        with open(self.dest_filename_img) as fp:
            self.assertTrue(fp.read(), b"conteudo img")

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test_get_asset_in_pdf_folder(self, read_file_binary):
        read_file_binary.return_value = b"conteudo pdf"
        old_path = "/pdf/en/asset.pdf"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        self.assertFalse(os.path.isfile(self.dest_filename_img))

        path = packing.get_asset(old_path, new_fname, dest_path)

        self.assertIsNone(path)

        with open(self.dest_filename_pdf) as fp:
            self.assertTrue(fp.read(), b"conteudo pdf")

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test_get_asset_raise_IOError_exception(self, mk_read_file_binary):
        mk_read_file_binary.side_effect = IOError
        old_path = "/img/en/scielobre.gif"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        error = packing.get_asset(old_path, new_fname, dest_path)
        self.assertIsNotNone(error)

    def test_invalid_relative_URL_returns_error(self):
        """
        Testa correção do bug:
        https://github.com/scieloorg/document-store-migracao/issues/158
        """
        error = packing.get_asset("//www. [ <a href=", "novo", TEMP_TEST_PATH)
        self.assertTrue(error.startswith("[Errno 2] No such file or directory"))


class TestProcessingpack_PackingAssets(unittest.TestCase):
    def setUp(self):
        if os.path.isdir(TEMP_TEST_PATH):
            shutil.rmtree(TEMP_TEST_PATH)
        os.makedirs(TEMP_TEST_PATH)
        self.good_pkg_path = os.path.join(TEMP_TEST_PATH, "good")
        self.bad_pkg_path = os.path.join(TEMP_TEST_PATH, "bad")

    def tearDown(self):
        shutil.rmtree(TEMP_TEST_PATH)

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test__pack_incomplete_package(self, mk_read_file_binary):
        asset_replacements = [
            ("/img/revistas/a01.gif", "f01"),
            ("/img/revistas/a02.gif", "f02"),
        ]
        m = Mock()
        m.return_value = b"conteudo"
        pkg_path = self.good_pkg_path
        bad_pkg_path = self.bad_pkg_path
        pkg_name = "pacote_sps"

        mk_read_file_binary.side_effect = [IOError("Error"), m.return_value]
        result_path = packing.packing_assets(
            asset_replacements, pkg_path, bad_pkg_path, pkg_name
        )
        self.assertEqual(result_path, bad_pkg_path)
        self.assertFalse(os.path.isdir(pkg_path))
        self.assertEqual(["f02.gif", pkg_name + ".err"], os.listdir(bad_pkg_path))
        with open(os.path.join(bad_pkg_path, pkg_name + ".err")) as fp:
            self.assertEqual(fp.read(), "/img/revistas/a01.gif f01 Error")

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test__pack_incomplete_package_same_dir(self, mk_read_file_binary):
        asset_replacements = [
            ("/img/revistas/a01.gif", "f01"),
            ("/img/revistas/a02.gif", "f02"),
        ]
        m = Mock()
        m.return_value = b"conteudo"
        pkg_path = self.good_pkg_path
        bad_pkg_path = self.good_pkg_path
        renamed_path = pkg_path + "_INCOMPLETE"
        pkg_name = "pacote_sps"
        mk_read_file_binary.side_effect = [IOError("Error"), m.return_value]
        result_path = packing.packing_assets(
            asset_replacements, pkg_path, bad_pkg_path, pkg_name
        )
        self.assertEqual(result_path, renamed_path)
        self.assertFalse(os.path.isdir(pkg_path))
        self.assertEqual(["f02.gif", pkg_name + ".err"], os.listdir(renamed_path))
        with open(os.path.join(renamed_path, pkg_name + ".err")) as fp:
            self.assertEqual(fp.read(), "/img/revistas/a01.gif f01 Error")

    @patch("documentstore_migracao.utils.files.read_file_binary")
    def test__pack_complete_package(self, mk_read_file_binary):
        asset_replacements = [
            ("/img/revistas/a01.gif", "f01"),
            ("/img/revistas/a02.gif", "f02"),
        ]
        mk_read_file_binary_result1 = Mock()
        mk_read_file_binary_result1.return_value = b"conteudo"
        mk_read_file_binary_result2 = Mock()
        mk_read_file_binary_result2.return_value = b"conteudo"

        pkg_path = self.good_pkg_path
        bad_pkg_path = self.bad_pkg_path
        pkg_name = "pacote_sps"
        mk_read_file_binary.side_effect = [mk_read_file_binary_result1.return_value, mk_read_file_binary_result2.return_value]
        result_path = packing.packing_assets(
            asset_replacements, pkg_path, bad_pkg_path, pkg_name
        )
        self.assertEqual(result_path, pkg_path)
        self.assertFalse(os.path.isdir(bad_pkg_path))
        self.assertEqual({"f01.gif", "f02.gif"}, set(os.listdir(pkg_path)))
