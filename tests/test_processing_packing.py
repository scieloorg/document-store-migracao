import os
import json
import shutil
import unittest
from unittest.mock import patch, ANY, Mock

from documentstore_migracao.processing import packing
from . import utils, SAMPLES_PATH, TEMP_TEST_PATH, COUNT_SAMPLES_FILES


class TestProcessingPacking(unittest.TestCase):

    def test_pack_article_xml_missing_media(self):
        with utils.environ(
            SOURCE_PATH=SAMPLES_PATH,
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
            SOURCE_PDF_FILE=os.path.join(os.path.dirname(__file__), "samples"),
            SOURCE_IMG_FILE=os.path.join(os.path.dirname(__file__), "samples")
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
            SOURCE_PATH=SAMPLES_PATH,
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
            SCIELO_COLLECTION="scl",
            SOURCE_PDF_FILE=os.path.join(os.path.dirname(__file__), "samples"),
            SOURCE_IMG_FILE=os.path.join(os.path.dirname(__file__), "samples")
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

    @patch("documentstore_migracao.processing.packing.SourceJson.get_renditions_metadata")
    @patch("documentstore_migracao.processing.packing.get_asset")
    def test_pack_article_write_manifest_json_file_with_renditions(
        self, mk_get_asset, mk_get_renditions_metadata
    ):
        with utils.environ(
            SOURCE_PATH=SAMPLES_PATH,
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

    @patch("documentstore_migracao.processing.packing.get_source_json")
    def test_pack_article_xml_has_no_media(self, mock_get_source_json):
        with utils.environ(
            SOURCE_PATH=SAMPLES_PATH,
            VALID_XML_PATH=SAMPLES_PATH,
            SPS_PKG_PATH=SAMPLES_PATH,
            INCOMPLETE_SPS_PKG_PATH=SAMPLES_PATH,
        ):
            mock_get_source_json.return_value = packing.SourceJson("{}")
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
    def test_get_asset_raises_AssetNotFoundError_exception(self, mk_read_file_binary):
        mk_read_file_binary.side_effect = IOError
        old_path = "/img/en/scielobre.gif"
        new_fname = "novo"
        dest_path = TEMP_TEST_PATH

        with self.assertRaises(packing.AssetNotFoundError):
            packing.get_asset(old_path, new_fname, dest_path)

    def test_invalid_relative_URL_raises_error(self):
        """
        Testa correção do bug:
        https://github.com/scieloorg/document-store-migracao/issues/158
        """
        with self.assertRaises(packing.AssetNotFoundError) as exc:
            packing.get_asset("//www. [ <a href=", "novo", TEMP_TEST_PATH)
        self.assertIn(
            "Not found",
            str(exc.exception)
        )


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
            asset_replacements, pkg_path, bad_pkg_path, pkg_name, "pid"
        )
        self.assertEqual(result_path, bad_pkg_path)
        self.assertFalse(os.path.isdir(pkg_path))
        self.assertEqual(["f02.gif", pkg_name + ".err"], os.listdir(bad_pkg_path))
        with open(os.path.join(bad_pkg_path, pkg_name + ".err")) as fp:
            self.assertIn("/img/revistas/a01.gif f01 Not found", fp.read())

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
            asset_replacements, pkg_path, bad_pkg_path, pkg_name, "pid"
        )
        self.assertEqual(result_path, renamed_path)
        self.assertFalse(os.path.isdir(pkg_path))
        self.assertEqual(["f02.gif", pkg_name + ".err"], os.listdir(renamed_path))
        with open(os.path.join(renamed_path, pkg_name + ".err")) as fp:
            self.assertIn("/img/revistas/a01.gif f01 Not found", fp.read())

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
            asset_replacements, pkg_path, bad_pkg_path, pkg_name, "pid"
        )
        self.assertEqual(result_path, pkg_path)
        self.assertFalse(os.path.isdir(bad_pkg_path))
        self.assertEqual({"f01.gif", "f02.gif"}, set(os.listdir(pkg_path)))


class TestCaseInsensitiveFind(unittest.TestCase):

    def test_case_insensitive_find_returns_itself(self):
        words = [
            "a18tab02M.gif", 'a18tab02m.gif', 'a18taB02m.gif',
        ]
        expected = "a18tab02M.gif"
        result = packing.case_insensitive_find("a18tab02M.gif", words)
        self.assertEqual(expected, result)

    def test_case_insensitive_find_returns_most_similar(self):
        words = [
            "A18tab02M.gif", 'a18tab02m.gif',
        ]
        expected = "a18tab02m.gif"
        result = packing.case_insensitive_find("a18tab02M.gif", words)
        self.assertEqual(expected, result)

    def test_case_insensitive_find_returns_WEBANNEX(self):
        words = ["WEBANNEx.pdf", "WEBANNEX.pdf", ]
        expected = "WEBANNEx.pdf"
        result = packing.case_insensitive_find("webannex.pdf", words)
        self.assertEqual(expected, result)

    def test_case_insensitive_find_returns_lower_ext(self):
        words = ["v32n1a05_1216_t1.jpg", "v32n1a05_1216_t2.JPG"]
        expected = "v32n1a05_1216_t1.jpg"
        result = packing.case_insensitive_find("v32n1a05_1216_t1.JPG", words)
        self.assertEqual(expected, result)

    def test_case_insensitive_find_returns_none(self):
        words = ["07t03.gif", "07t2.gif"]
        expected = None
        result = packing.case_insensitive_find("07t3.gif", words)
        self.assertEqual(expected, result)


class TestFindFile(unittest.TestCase):

    @patch("documentstore_migracao.processing.packing.os.listdir")
    def test_find_file_a18tab02M(self, mock_listdir):
        mock_listdir.return_value = [
            'a16tab02.gif', 'a18tab02m.gif', 'a18tab01.gif',
        ]
        expected = "/tmp/a18tab02m.gif"
        result = packing.find_file("/tmp/a18tab02M.gif")
        self.assertEqual(expected, result)

    @patch("documentstore_migracao.processing.packing.os.listdir")
    def test_find_file_webannex(self, mock_listdir):
        mock_listdir.return_value = ["WEBANNEX.pdf"]
        expected = "/tmp/WEBANNEX.pdf"
        result = packing.find_file("/tmp/webannex.pdf")
        self.assertEqual(expected, result)

    @patch("documentstore_migracao.processing.packing.os.listdir")
    def test_find_file_en_v32n1a05_1216_t1(self, mock_listdir):
        mock_listdir.return_value = ["en_v32n1a05_1216_t1.jpg"]
        expected = "/tmp/en_v32n1a05_1216_t1.jpg"
        result = packing.find_file("/tmp/en_v32n1a05_1216_t1.JPG")
        self.assertEqual(expected, result)

    @patch("documentstore_migracao.processing.packing.os.listdir")
    def test_find_file_07t3(self, mock_listdir):
        mock_listdir.return_value = ["07t03.gif"]
        expected = None
        result = packing.find_file("/tmp/07t3.gif")
        self.assertEqual(expected, result)

