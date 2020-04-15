import io
import csv
import pathlib
import tempfile
import shutil
from unittest import TestCase, mock

from lxml import etree
from PIL import Image

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
        self.xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink"><body>
        <sec>
          <p>The Eh measurements... <xref ref-type="disp-formula" rid="e01">equation 1</xref>(in mV):</p>
          <disp-formula id="e01">
            {graphic_01}
          </disp-formula>
          <p>We also used an... {graphic_02}.</p>
        </sec>
        <fig id="f03">
            <label>Fig. 3</label>
            <caption>
                <title>titulo da imagem</title>
            </caption>
            <alternatives>
                <graphic xlink:href="1234-5678-rctb-45-05-0110-gf03.tiff"/>
                <graphic xlink:href="1234-5678-rctb-45-05-0110-gf03.png" specific-use="scielo-web"/>
                <graphic xlink:href="1234-5678-rctb-45-05-0110-gf03.thumbnail.jpg" specific-use="scielo-web" content-type="scielo-267x140"/>
            </alternatives>
        </fig>
        <p>We also used an ... based on the equation:<inline-graphic xlink:href="1234-5678-rctb-45-05-0110-e04.tif"/>.</p>
        </body></article>"""


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


class TestBuildSPSPackageUpdateXMLWithAlternatives_WithExtension(TestBuildSPSPackageBase):
    def setUp(self):
        super().setUp()
        self.target_path = tempfile.mkdtemp()
        self.xml_target_path = pathlib.Path(self.target_path, "xml_file_name.xml")
        graphic_01 = '<graphic xlink:href="1234-5678-rctb-45-05-0110-gf01.tiff"/>'
        graphic_02 = '<inline-graphic xlink:href="1234-5678-rctb-45-05-0110-e02.tif"/>'
        xml = self.xml.format(graphic_01=graphic_01, graphic_02=graphic_02)
        self.sps_package = SPS_Package(
            etree.fromstring(
                xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
            )
        )

    def tearDown(self):
        shutil.rmtree(self.target_path)

    def test_no_alternative_for_asset(self):
        self.assets_alternatives = {
            "1234-5678-rctb-45-05-0110-gf01.tiff": [
                "1234-5678-rctb-45-05-0110-gf01.jpg",
            ],
            "1234-5678-rctb-45-05-0110-e02.tif": [],
        }

        self.builder.update_xml_with_alternatives(
            self.assets_alternatives, self.sps_package, self.xml_target_path
        )
        with self.xml_target_path.open() as xmlfile:
            xml_result = etree.parse(
                xmlfile, etree.XMLParser(remove_blank_text=True, no_network=True)
            )
            graphic_01_node = xml_result.find(
                '//alternatives/graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.tiff"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_01_node)
            self.assertIsNotNone(
                graphic_01_node.getparent().find(
                    'graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.jpg"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            self.assertIsNotNone(
                xml_result.find(
                    '//inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.tif"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )

    def test_one_alternative_each_asset(self):
        self.assets_alternatives = {
            "1234-5678-rctb-45-05-0110-gf01.tiff": [
                "1234-5678-rctb-45-05-0110-gf01.jpg",
            ],
            "1234-5678-rctb-45-05-0110-e02.tif": [
                "1234-5678-rctb-45-05-0110-e02.gif"
            ],
        }

        self.builder.update_xml_with_alternatives(
            self.assets_alternatives, self.sps_package, self.xml_target_path
        )
        with self.xml_target_path.open() as xmlfile:
            xml_result = etree.parse(
                xmlfile, etree.XMLParser(remove_blank_text=True, no_network=True)
            )
            graphic_01_node = xml_result.find(
                '//alternatives/graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.tiff"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_01_node)
            self.assertIsNotNone(
                graphic_01_node.getparent().find(
                    'graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.jpg"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            graphic_02_node = xml_result.find(
                '//alternatives/inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.tif"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_02_node)
            self.assertIsNotNone(
                graphic_02_node.getparent().find(
                    'inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.gif"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )

    def test_alternatives_each_asset(self):
        self.assets_alternatives = {
            "1234-5678-rctb-45-05-0110-gf01.tiff": [
                "1234-5678-rctb-45-05-0110-gf01.gif",
                "1234-5678-rctb-45-05-0110-gf01.png",
                "1234-5678-rctb-45-05-0110-gf01.jpg",
            ],
            "1234-5678-rctb-45-05-0110-e02.tif": [
                "1234-5678-rctb-45-05-0110-e02.png",
                "1234-5678-rctb-45-05-0110-e02.gif",
            ],
        }

        self.builder.update_xml_with_alternatives(
            self.assets_alternatives, self.sps_package, self.xml_target_path
        )
        with self.xml_target_path.open() as xmlfile:
            xml_result = etree.parse(
                xmlfile, etree.XMLParser(remove_blank_text=True, no_network=True)
            )
            graphic_01_node = xml_result.find(
                '//alternatives/graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.tiff"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_01_node)
            self.assertIsNotNone(
                graphic_01_node.getparent().find(
                    'graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.gif"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            self.assertIsNotNone(
                graphic_01_node.getparent().find(
                    'graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.png"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            self.assertIsNotNone(
                graphic_01_node.getparent().find(
                    'graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.jpg"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            graphic_02_node = xml_result.find(
                '//alternatives/inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.tif"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_02_node)
            self.assertIsNotNone(
                graphic_02_node.getparent().find(
                    'inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.png"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            self.assertIsNotNone(
                graphic_02_node.getparent().find(
                    'inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.gif"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )


class TestBuildSPSPackageUpdateXMLWithAlternatives_NoExtension(TestBuildSPSPackageBase):
    def setUp(self):
        super().setUp()
        self.target_path = tempfile.mkdtemp()
        self.xml_target_path = pathlib.Path(self.target_path, "xml_file_name.xml")
        graphic_01 = '<graphic xlink:href="1234-5678-rctb-45-05-0110-gf01"/>'
        graphic_02 = '<inline-graphic xlink:href="1234-5678-rctb-45-05-0110-e02"/>'
        xml = self.xml.format(graphic_01=graphic_01, graphic_02=graphic_02)
        self.sps_package = SPS_Package(
            etree.fromstring(
                xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
            )
        )

    def tearDown(self):
        shutil.rmtree(self.target_path)

    def test_one_alternative_each_asset(self):
        self.assets_alternatives = {
            "1234-5678-rctb-45-05-0110-gf01": [
                "1234-5678-rctb-45-05-0110-gf01.png",
            ],
            "1234-5678-rctb-45-05-0110-e02": [
                "1234-5678-rctb-45-05-0110-e02.tif"
            ],
        }

        self.builder.update_xml_with_alternatives(
            self.assets_alternatives, self.sps_package, self.xml_target_path
        )
        with self.xml_target_path.open() as xmlfile:
            xml_result = etree.parse(
                xmlfile, etree.XMLParser(remove_blank_text=True, no_network=True)
            )
            graphic_01_node = xml_result.find(
                '//alternatives/graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_01_node)
            self.assertIsNotNone(
                graphic_01_node.getparent().find(
                    'graphic[@xlink:href="1234-5678-rctb-45-05-0110-gf01.png"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )
            graphic_02_node = xml_result.find(
                '//alternatives/inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02"]',
                namespaces={"xlink": "http://www.w3.org/1999/xlink"},
            )
            self.assertIsNotNone(graphic_02_node)
            self.assertIsNotNone(
                graphic_02_node.getparent().find(
                    'inline-graphic[@xlink:href="1234-5678-rctb-45-05-0110-e02.tif"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
            )


def create_image_file(filename, format):
    new_image = Image.new("RGB", (50, 50))
    new_image.save(filename, format)


class TestBuildSPSPackageCollectAssetAlternatives(TestBuildSPSPackageBase):
    def setUp(self):
        super().setUp()
        self.source_path = tempfile.mkdtemp()
        self.target_path = tempfile.mkdtemp()
        self.image_files = (
            ("1234-5678-rctb-45-05-0110-gf01.tiff", "TIFF"),
            ("1234-5678-rctb-45-05-0110-gf01.png", "PNG"),
            ("1234-5678-rctb-45-05-0110-gf01.jpg", "JPEG"),
        )
        for image_filename, format in self.image_files:
            image_file_path = pathlib.Path(self.source_path, image_filename)
            create_image_file(image_file_path, format)

    def tearDown(self):
        shutil.rmtree(self.source_path)
        shutil.rmtree(self.target_path)

    def test_no_alternatives(self):
        result = self.builder.collect_asset_alternatives(
            "1234-5678-rctb-45-05-0110-gf02.tiff", self.source_path, self.target_path
        )
        self.assertEqual(type(result), list)
        self.assertEqual(len(result), 0)

    def test_saves_alternatives_into_target_path(self):
        self.builder.collect_asset_alternatives(
            "1234-5678-rctb-45-05-0110-gf01.gif", self.source_path, self.target_path
        )
        for image_file, __ in self.image_files:
            with self.subTest(image_file=image_file):
                self.assertTrue(pathlib.Path(self.target_path, image_file).exists())

    def test_returns_dict_with_alternatives(self):
        result = self.builder.collect_asset_alternatives(
            "1234-5678-rctb-45-05-0110-gf01.gif", self.source_path, self.target_path
        )
        self.assertEqual(result, [image_file for image_file, __ in self.image_files])


class TestBuildSPSPackageXMLWEBOptimiser(TestBuildSPSPackageBase):

    def setUp(self):
        super().setUp()
        self.target_path = tempfile.mkdtemp()
        self.xml_target_path = pathlib.Path(self.target_path, "xml_file_name.xml")
        image_files = (
            ("1234-5678-rctb-45-05-0110-gf03.tiff", "TIFF"),
            ("1234-5678-rctb-45-05-0110-gf03.png", "PNG"),
            ("1234-5678-rctb-45-05-0110-gf03.thumbnail.jpg", "JPEG"),
        )
        for image_filename, format in image_files:
            image_file_path = pathlib.Path(self.target_path, image_filename)
            create_image_file(image_file_path, format)

    def tearDown(self):
        shutil.rmtree(self.target_path)

    def test_preserve_graphic_in_xml_if_image_file_does_not_exist(self):
        image_files = (
            ("1234-5678-rctb-45-05-0110-e01.tif", "TIFF"),
            ("1234-5678-rctb-45-05-0110-e04.tif", "TIFF"),
        )
        for image_filename, format in image_files:
            image_file_path = pathlib.Path(self.target_path, image_filename)
            create_image_file(image_file_path, format)
        graphic_01 = '<graphic xlink:href="1234-5678-rctb-45-05-0110-e01.tif"/>'
        graphic_02 = '<inline-graphic xlink:href="1234-5678-rctb-45-05-0110-e02.tiff"/>'
        xml = self.xml.format(graphic_01=graphic_01, graphic_02=graphic_02)
        sps_package = SPS_Package(
            etree.fromstring(
                xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
            )
        )
        with self.xml_target_path.open("w") as xml_file:
            xml_file.write(xml)

        self.builder.optimise_xml_to_web(self.target_path, str(self.xml_target_path))

        target_path_files = [
            filename.name for filename in pathlib.Path(self.target_path).iterdir()
        ]
        self.assertNotIn("1234-5678-rctb-45-05-0110-e02.png", target_path_files)
        with open(self.xml_target_path) as xmlfile:
            xml_result = etree.parse(
                xmlfile, etree.XMLParser(remove_blank_text=True, no_network=True)
            )
            img_filenames = [
                elem.attrib.get("{http://www.w3.org/1999/xlink}href")
                for elem in xml_result.xpath('//inline-graphic')
            ]
            self.assertIn("1234-5678-rctb-45-05-0110-e02.tiff", img_filenames)
            self.assertNotIn("1234-5678-rctb-45-05-0110-e02.png", img_filenames)

    def test_creates_optimised_files(self):
        image_files = (
            ("1234-5678-rctb-45-05-0110-e01.tif", "TIFF"),
            ("1234-5678-rctb-45-05-0110-e02.tiff", "TIFF"),
            ("1234-5678-rctb-45-05-0110-e04.tif", "TIFF"),
        )
        for image_filename, format in image_files:
            image_file_path = pathlib.Path(self.target_path, image_filename)
            create_image_file(image_file_path, format)
        graphic_01 = '<graphic xlink:href="1234-5678-rctb-45-05-0110-e01.tif"/>'
        graphic_02 = '<inline-graphic xlink:href="1234-5678-rctb-45-05-0110-e02.tiff"/>'
        xml = self.xml.format(graphic_01=graphic_01, graphic_02=graphic_02)
        sps_package = SPS_Package(
            etree.fromstring(
                xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
            )
        )
        with self.xml_target_path.open("w") as xml_file:
            xml_file.write(xml)

        self.builder.optimise_xml_to_web(self.target_path, str(self.xml_target_path))

        target_path_files = [
            filename.name for filename in pathlib.Path(self.target_path).iterdir()
        ]
        self.assertIn("1234-5678-rctb-45-05-0110-e01.png", target_path_files)
        self.assertIn("1234-5678-rctb-45-05-0110-e01.thumbnail.jpg", target_path_files)
        self.assertIn("1234-5678-rctb-45-05-0110-e02.png", target_path_files)
        self.assertIn("1234-5678-rctb-45-05-0110-e04.png", target_path_files)

    def test_optimises_xml_with_new_images(self):
        image_files = (
            ("1234-5678-rctb-45-05-0110-e01.tif", "TIFF"),
            ("1234-5678-rctb-45-05-0110-e02.tiff", "TIFF"),
            ("1234-5678-rctb-45-05-0110-e04.tif", "TIFF"),
        )
        for image_filename, format in image_files:
            image_file_path = pathlib.Path(self.target_path, image_filename)
            create_image_file(image_file_path, format)
        graphic_01 = '<graphic xlink:href="1234-5678-rctb-45-05-0110-e01.tif"/>'
        graphic_02 = '<inline-graphic xlink:href="1234-5678-rctb-45-05-0110-e02.tiff"/>'
        xml = self.xml.format(graphic_01=graphic_01, graphic_02=graphic_02)
        sps_package = SPS_Package(
            etree.fromstring(
                xml, parser=etree.XMLParser(remove_blank_text=True, no_network=True)
            )
        )
        with self.xml_target_path.open("w") as xml_file:
            xml_file.write(xml)

        self.builder.optimise_xml_to_web(self.target_path, str(self.xml_target_path))

        target_path_files = [
            filename for filename in pathlib.Path(self.target_path).iterdir()
        ]
        with open(self.xml_target_path) as xmlfile:
            xml_result = etree.parse(
                xmlfile, etree.XMLParser(remove_blank_text=True, no_network=True)
            )
            img_filenames = [
                elem.attrib.get("{http://www.w3.org/1999/xlink}href")
                for elem in xml_result.xpath('//alternatives/graphic')
            ]
            self.assertIn("1234-5678-rctb-45-05-0110-e01.tif", img_filenames)
            self.assertIn("1234-5678-rctb-45-05-0110-e01.png", img_filenames)
            self.assertIn("1234-5678-rctb-45-05-0110-e01.thumbnail.jpg", img_filenames)
            img_filenames = [
                elem.attrib.get("{http://www.w3.org/1999/xlink}href")
                for elem in xml_result.xpath('//alternatives/inline-graphic')
            ]
            self.assertIn("1234-5678-rctb-45-05-0110-e02.tiff", img_filenames)
            self.assertIn("1234-5678-rctb-45-05-0110-e02.png", img_filenames)
            self.assertIn("1234-5678-rctb-45-05-0110-e04.tif", img_filenames)
            self.assertIn("1234-5678-rctb-45-05-0110-e04.png", img_filenames)
