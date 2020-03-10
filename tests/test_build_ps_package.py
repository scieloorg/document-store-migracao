import io
import shutil
import csv
import tempfile
import pathlib
from unittest import TestCase, mock

from lxml import etree

from . import utils
from documentstore_migracao.utils import build_ps_package, xml
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
            "test",
            "/data/xmls",
            "/data/imgs",
            "/data/pdfs",
            "/data/output",
            "/data/article_data_file.csv",
        )
        self.article_data_reader = csv.DictReader(fake_csv(), fieldnames=CSV_FIELDNAMES)


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


class TestBuildSPSPackagePIDUpdade(TestBuildSPSPackageBase):

    def test__update_sps_package_object_updates_pid_if_it_is_none(self):
        mk_sps_package = mock.Mock(spec=SPS_Package, aop_pid=None, scielo_pid_v2=None)
        pack_name = "1806-0013-test-01-01-0001"
        result = self.builder._update_sps_package_object(
            self.article_data_reader, mk_sps_package, pack_name
        )
        self.assertEqual(result.scielo_pid_v2, "S0101-01012019000100001")

    def test__update_sps_package_object_does_not_update_pid_if_it_is_not_none(self):
        mk_sps_package = mock.Mock(
            spec=SPS_Package, scielo_pid_v2="S0101-01012019000100999"
        )
        pack_name = "1806-0013-test-01-01-0001"
        result = self.builder._update_sps_package_object(
            self.article_data_reader, mk_sps_package, pack_name
        )
        self.assertEqual(result.scielo_pid_v2, "S0101-01012019000100999")


class TestBuildSPSPackageAOPPIDUpdade(TestBuildSPSPackageBase):

    def test__update_sps_package_object_updates_aop_pid_if_pid_is_none(self):
        mk_sps_package = mock.Mock(spec=SPS_Package, aop_pid=None, scielo_pid_v2=None)
        pack_name = "1806-0013-test-01-01-0002"
        result = self.builder._update_sps_package_object(
            self.article_data_reader, mk_sps_package, pack_name
        )
        self.assertEqual(result.aop_pid, "S0101-01012019005000001")

    def test__update_sps_package_object_updates_aop_pid_if_pid_is_found(self):
        mk_sps_package = mock.Mock(
            spec=SPS_Package, aop_pid=None, scielo_pid_v2="S0101-01012019000100002"
        )
        pack_name = "1806-0013-test-01-01-0002"
        result = self.builder._update_sps_package_object(
            self.article_data_reader, mk_sps_package, pack_name
        )
        self.assertEqual(result.aop_pid, "S0101-01012019005000001")

    def test__update_sps_package_object_does_not_update_aop_pid_if_it_is_not_aop(self):
        article_data = (
            ("S0101-01012019000100001", "1806-0013-test-01-01-0001"),
            (None, "1806-0013-test-01-01-0003"),
        )
        for scielo_pid_v2, pack_name in article_data:
            with self.subTest(scielo_pid_v2=scielo_pid_v2, pack_name=pack_name):
                mk_sps_package = mock.Mock(
                    spec=SPS_Package, aop_pid=None, scielo_pid_v2=scielo_pid_v2
                )
                result = self.builder._update_sps_package_object(
                    self.article_data_reader, mk_sps_package, pack_name
                )
                self.assertIsNone(result.aop_pid)


class TestBuildSPSPackageAOPPubDate(TestBuildSPSPackageBase):

    def test__update_sps_package_object_does_not_update_pubdate_if_it_is_aop(self):
        mk_sps_package = mock.Mock(
            spec=SPS_Package,
            aop_pid=None,
            scielo_pid_v2="S0101-01012019000100003",
            is_ahead_of_print=True,
        )
        pack_name = "1806-0013-test-01-01-0003"
        result = self.builder._update_sps_package_object(
            self.article_data_reader, mk_sps_package, pack_name
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

    def test__update_sps_package_object_completes_documents_bundle_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("", "", "",)
        result = self.builder._update_sps_package_object(
            self.article_data_reader, self.mk_sps_package, self.pack_name
        )
        self.assertEqual(result.documents_bundle_pubdate, ("2019", "02", "",))

    def test__update_sps_package_object_does_not_change_documents_bundle_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("2012", "", "",)
        result = self.builder._update_sps_package_object(
            self.article_data_reader, self.mk_sps_package, self.pack_name
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

    def test__update_sps_package_object_completes_document_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("2012", "02", "03",)
        self.mk_sps_package.document_pubdate = ("", "", "",)
        result = self.builder._update_sps_package_object(
            self.article_data_reader, self.mk_sps_package, self.pack_name
        )
        self.assertEqual(result.document_pubdate, ("2019", "01", "15",))

    def test__update_sps_package_object_does_not_change_document_pubdate(self):
        self.mk_sps_package.documents_bundle_pubdate = ("2012", "02", "",)
        self.mk_sps_package.document_pubdate = ("2012", "01", "15",)
        result = self.builder._update_sps_package_object(
            self.article_data_reader, self.mk_sps_package, self.pack_name
        )
        self.assertEqual(result.document_pubdate, ("2012", "01", "15",))
