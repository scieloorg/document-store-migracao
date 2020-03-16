import io
import csv
import pathlib
from unittest import TestCase, mock

from lxml import etree

from . import utils
from documentstore_migracao.utils import build_ps_package
from documentstore_migracao.export.sps_package import SPS_Package


CSV_FIELDNAMES = (
    "PID",
    "PID AOP",
    "FILE",
    "DATA (COLLECTION)",
    "DATA PRIMEIRO PROCESSAMENTO",
    "DATA DO ULTIMO PROCESSAMENTO",
)


def create_xml(xml_file_path, article_meta_xml, sps_version="sps-1.9"):
    xml_string = utils.build_xml(article_meta_xml, "10.1590/S0074-02761962000200006")
    with pathlib.Path(xml_file_path).open(mode="wb", encoding="utf-8") as xmlfile:
        xmlfile.write(
            etree.tostring(
                etree.fromstring(xml_string),
                xml_declaration=True,
                method="xml",
                encoding="utf-8",
                pretty_print=True,
            )
        )


def fake_csv():
    return io.StringIO(
        "S0101-01012019000100001,,test/v1n1/1806-0013-test-01-01-0001.xml,,,\n"
        "S0101-01012019000100002,S0101-01012019005000001,test/v1n1/1806-0013-test-01-01-0002.xml,20190200,20190115,20190507\n"
        "S0101-01012019000100003,,test/v1n1/1806-0013-test-01-01-0003.xml,,,\n"
    )


class TestBuildSPSPackageBase(TestCase):
    def setUp(self):
        self.builder = build_ps_package.BuildPSPackage(
            "/data/xmls",
            "/data/imgs",
            "/data/pdfs",
            "/data/output",
            "/data/article_data_file.csv",
        )
        self.article_data_reader = csv.DictReader(fake_csv(), fieldnames=CSV_FIELDNAMES)
        self.rows = [
            ['S0101-01012019000100001',
             '',
             'test/v1n1/1806-0013-test-01-01-0001.xml',
             '',
             '',
             ''],
            ['S0101-01012019000100002',
             'S0101-01012019005000001',
             'test/v1n1/1806-0013-test-01-01-0002.xml',
             '20190200',
             '20190115',
             '20190507'],
            ['S0101-01012019000100003',
             '',
             'test/v1n1/1806-0013-test-01-01-0003.xml',
             '',
             '',
             '']
        ]


class TestBuildSPSPackage(TestBuildSPSPackageBase):

    @mock.patch("documentstore_migracao.utils.build_ps_package.os.path.isdir")
    @mock.patch("documentstore_migracao.utils.build_ps_package.os.makedirs", return_value=None)
    def test_get_target_path_returns_target_path(self, mock_makedirs, mock_isdir):
        mock_isdir.return_value = False
        result = self.builder.get_target_path("abc/v1n1/bla.xml")
        mock_isdir.assert_called_once_with("/data/output/abc/v1n1/bla")
        mock_makedirs.assert_called_once_with("/data/output/abc/v1n1/bla")
        self.assertEqual(
            result,
            "/data/output/abc/v1n1/bla"
        )

    @mock.patch("documentstore_migracao.utils.build_ps_package.shutil.copy")
    @mock.patch("documentstore_migracao.utils.build_ps_package.os.path.isfile", return_value=True)
    def test_collection_xml_path_returns_xml_target_path(self, mock_isfile, mock_copy):
        result = self.builder.collect_xml("abc/v1n1/bla.xml", "/data/output/abc/v1n1/bla")
        mock_copy.assert_called_once_with(
            "/data/xmls/abc/v1n1/bla.xml", "/data/output/abc/v1n1/bla")

    def test_get_acron_issuefolder_packname_path_returns_acron_issuefolder_packname(self):
        acron, issue_folder, pack_name = self.builder.get_acron_issuefolder_packname("abc/v1n1/bla.xml")
        self.assertEqual(acron, "abc")
        self.assertEqual(issue_folder, "v1n1")
        self.assertEqual(pack_name, "bla")

    @mock.patch("documentstore_migracao.utils.build_ps_package.shutil.copy")
    def test_collect_renditions_for_document_without_translations(self, mock_copy):
        result = self.builder.collect_renditions(
            "/data/output/abc/v1n1/bla", "abc", "v1n1", "bla", ["pt"])
        mock_copy.assert_called_once_with(
            "/data/pdfs/abc/v1n1/bla.pdf", "/data/output/abc/v1n1/bla"
        )
        self.assertEqual(result, [("pt", "bla.pdf")])

    @mock.patch("documentstore_migracao.utils.build_ps_package.shutil.copy")
    def test_collect_renditions_for_document_with_translations_in_en_and_es(self, mock_copy):
        result = self.builder.collect_renditions(
            "/data/output/abc/v1n1/bla", "abc", "v1n1", "bla",
            ["pt", "en", "es"])
        assert mock_copy.call_args_list == [
            mock.call(
                "/data/pdfs/abc/v1n1/bla.pdf", "/data/output/abc/v1n1/bla"
            ),
            mock.call(
                "/data/pdfs/abc/v1n1/en_bla.pdf", "/data/output/abc/v1n1/bla"
            ),
            mock.call(
                "/data/pdfs/abc/v1n1/es_bla.pdf", "/data/output/abc/v1n1/bla"
            ),
        ]
        self.assertEqual(
            result,
            [
                ("pt", "bla.pdf"),
                ("en", "bla-en.pdf"),
                ("es", "bla-es.pdf"),
            ]
        )

    @mock.patch("documentstore_migracao.utils.build_ps_package.open")
    def test_save_renditions_manifest_creates_manifest_in_target_path(self, mock_open):
        self.builder.save_renditions_manifest(
            "/data/output/abc/v1n1/bla", "{'pt': 'bla'}")
        mock_open.assert_called_once_with("/data/output/abc/v1n1/bla/manifest.json", "w")

    @mock.patch("documentstore_migracao.utils.build_ps_package.shutil.copy")
    def test_collect_assets_creates_files_in_target_path(self, mock_copy):
        images = ["bla1.jpg", "bla2.jpg", "bla3.jpg"]
        self.builder.collect_assets(
            "/data/output/abc/v1n1/bla", "abc", "v1n1", "bla", images)
        calls = [
            mock.call(
                "/data/imgs/abc/v1n1/bla1.jpg", "/data/output/abc/v1n1/bla"
            ),
            mock.call(
                "/data/imgs/abc/v1n1/bla2.jpg", "/data/output/abc/v1n1/bla"
            ),
            mock.call(
                "/data/imgs/abc/v1n1/bla3.jpg", "/data/output/abc/v1n1/bla"
            ),
        ]
        mock_copy.assert_has_calls(calls, any_order=True)

    @mock.patch("documentstore_migracao.utils.build_ps_package.shutil.copy")
    def test_collect_assets_creates_one_file_in_target_path(self, mock_copy):
        images = ["bla.jpg", "bla.jpg", "bla.jpg"]
        self.builder.collect_assets(
            "/data/output/abc/v1n1/bla", "abc", "v1n1", "bla", images)
        mock_copy.assert_called_once_with(
            "/data/imgs/abc/v1n1/bla.jpg", "/data/output/abc/v1n1/bla"
        )


class TestBuildSPSPackagePIDUpdade(TestBuildSPSPackageBase):

    @mock.patch("documentstore_migracao.utils.build_ps_package.getattr")
    def test__update_sps_package_obj_updates_pid_if_it_is_none(self, mock_getattr):
        mk_sps_package = mock.Mock(spec=SPS_Package)
        mock_getattr.side_effect = [None, None]
        pack_name = "1806-0013-test-01-01-0001"
        row = "S0101-01012019000100001,,test/v1n1/1806-0013-test-01-01-0001.xml,,,".split(",")
        result = self.builder._update_sps_package_obj(
            mk_sps_package, pack_name, row
        )
        self.assertEqual(result.scielo_pid_v2, "S0101-01012019000100001")

    @mock.patch("documentstore_migracao.utils.build_ps_package.getattr")
    def test__update_sps_package_obj_does_not_update_pid_if_it_is_not_none(self, mock_getattr):
        mk_sps_package = mock.Mock(
            spec=SPS_Package, scielo_pid_v2="S0101-01012019000100999")
        mock_getattr.side_effect = ["S0101-01012019000100999", None]

        row = "S0101-01012019000100001,,test/v1n1/1806-0013-test-01-01-0001.xml,,,".split(",")
        pack_name = "1806-0013-test-01-01-0001"
        result = self.builder._update_sps_package_obj(
            mk_sps_package, pack_name, row
        )
        self.assertEqual(result.scielo_pid_v2, "S0101-01012019000100999")


class TestBuildSPSPackageAOPPIDUpdade(TestBuildSPSPackageBase):

    @mock.patch("documentstore_migracao.utils.build_ps_package.getattr")
    def test__update_sps_package_obj_updates_aop_pid_if_pid_is_none(self, mock_getattr):
        mk_sps_package = mock.Mock(spec=SPS_Package, aop_pid=None, scielo_pid_v2=None)
        pack_name = "1806-0013-test-01-01-0002"
        mock_getattr.side_effect = [None, None]
        result = self.builder._update_sps_package_obj(
            mk_sps_package, pack_name, self.rows[1]
        )
        self.assertEqual(result.aop_pid, "S0101-01012019005000001")

    @mock.patch("documentstore_migracao.utils.build_ps_package.getattr")
    def test__update_sps_package_obj_updates_aop_pid_if_pid_is_found(self, mock_getattr):
        mock_getattr.side_effect = ["S0101-01012019000100002", None]
        mk_sps_package = mock.Mock(
            spec=SPS_Package, aop_pid=None, scielo_pid_v2="S0101-01012019000100002"
        )
        pack_name = "1806-0013-test-01-01-0002"
        result = self.builder._update_sps_package_obj(
            mk_sps_package, pack_name, self.rows[1]
        )
        self.assertEqual(result.aop_pid, "S0101-01012019005000001")

    @mock.patch("documentstore_migracao.utils.build_ps_package.getattr")
    def test__update_sps_package_obj_does_not_update_aop_pid_if_it_is_not_aop(self, mock_getattr):
        mock_getattr.side_effect = ["S0101-01012019000100002", None]
        mk_sps_package = mock.Mock(
            spec=SPS_Package, aop_pid=None, scielo_pid_v2="S0101-01012019000100002"
        )
        pack_name = "1806-0013-test-01-01-0001"
        result = self.builder._update_sps_package_obj(
            mk_sps_package, pack_name, self.rows[0]
        )
        self.assertIsNone(result.aop_pid)


class TestBuildSPSPackageAOPPubDate(TestBuildSPSPackageBase):

    @mock.patch("documentstore_migracao.utils.build_ps_package.getattr")
    def test__update_sps_package_obj_does_not_update_pubdate_if_it_is_aop(self, mock_getattr):
        mock_getattr.side_effect = ["S0101-01012019000100003", None]
        mk_sps_package = mock.Mock(
            spec=SPS_Package,
            aop_pid=None,
            scielo_pid_v2="S0101-01012019000100003",
            is_ahead_of_print=True,
        )
        pack_name = "1806-0013-test-01-01-0003"
        result = self.builder._update_sps_package_obj(
            mk_sps_package, pack_name, self.rows[2]
        )
        mk_sps_package.document_pubdate.assert_not_called()
        mk_sps_package.documents_bundle_pubdate.assert_not_called()


class TestBuildSPSPackageRollingPassDocumentPubDate(TestBuildSPSPackageBase):

    def setUp(self):
        super().setUp()
        self.pack_name = "1806-0013-test-01-01-0002"
        self.mk_sps_package = mock.Mock(
            spec=SPS_Package,
            aop_pid=None,
            scielo_pid_v2="S0101-01012019000100002",
            is_ahead_of_print=False,
            document_pubdate=("2012", "01", "15",)
        )

    def test__update_sps_package_obj_completes_documents_bundle_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("", "", "",)
        result = self.builder._update_sps_package_obj(
            self.mk_sps_package, self.pack_name, self.rows[1]
        )
        self.assertEqual(result.documents_bundle_pubdate, ("2019", "02", "",))

    def test__update_sps_package_obj_does_not_change_documents_bundle_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("2012", "", "",)
        result = self.builder._update_sps_package_obj(
            self.mk_sps_package, self.pack_name, self.rows[1]
        )
        self.assertEqual(result.documents_bundle_pubdate, ("2012", "", "",))


class TestBuildSPSPackageDocumentInRegularIssuePubDate(TestBuildSPSPackageBase):

    def setUp(self):
        super().setUp()
        self.pack_name = "1806-0013-test-01-01-0002"
        self.mk_sps_package = mock.Mock(
            spec=SPS_Package,
            aop_pid=None,
            scielo_pid_v2="S0101-01012019000100002",
            is_ahead_of_print=False,
        )

    def test__update_sps_package_obj_completes_document_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("2012", "02", "03",)
        self.mk_sps_package.document_pubdate = ("", "", "",)
        result = self.builder._update_sps_package_obj(
            self.mk_sps_package, self.pack_name, self.rows[1]
        )
        self.assertEqual(result.document_pubdate, ("2019", "01", "15",))

    def test__update_sps_package_obj_does_not_change_document_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("2012", "02", "",)
        self.mk_sps_package.document_pubdate = ("2012", "01", "15",)
        result = self.builder._update_sps_package_obj(
            self.mk_sps_package, self.pack_name, self.rows[1]
        )
        self.assertEqual(result.document_pubdate, ("2012", "01", "15",))
