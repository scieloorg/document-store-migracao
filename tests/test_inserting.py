import unittest
from unittest.mock import patch, Mock, MagicMock, ANY, call
from copy import deepcopy
from .apptesting import Session
from . import (
    SAMPLE_ISSUES_KERNEL,
    SAMPLE_AOPS_KERNEL,
    SAMPLE_KERNEL_JOURNAL,
    SAMPLES_PATH,
    SAMPLES_JOURNAL,
)

import os
import shutil

from documentstore_migracao.processing import inserting
from documentstore_migracao.utils import manifest
from documentstore_migracao import config
from documentstore.domain import DocumentsBundle
from documentstore.exceptions import DoesNotExist
from documentstore_migracao.processing.inserting import (
    get_document_assets_path,
    put_static_assets_into_storage,
)
from documentstore_migracao.utils.xml import loadToXML


class TestLinkDocumentsBundleWithDocuments(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        manifest = inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        self.session.documents_bundles.add(manifest)
        self.documents_bundle = self.session.documents_bundles.fetch(manifest.id())

    def test_should_link_documents_bundle_with_documents(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle, ["doc-1", "doc-2"], self.session
        )

        self.assertEqual(["doc-1", "doc-2"], self.documents_bundle.documents)

    def test_should_not_insert_duplicated_documents(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle, ["doc-1", "doc-1"], self.session
        )

        self.assertEqual(["doc-1"], self.documents_bundle.documents)

    def test_should_register_changes(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle, ["doc-1", "doc-2"], self.session
        )

        _changes = self.session.changes.filter()

        self.assertEqual(1, len(_changes))
        self.assertEqual(self.documents_bundle.id(), _changes[0]["id"])
        self.assertEqual("DocumentsBundle", _changes[0]["entity"])


class TestProcessingInserting(unittest.TestCase):
    def setUp(self):
        self.data = dict(
            [
                ("eissn", "1234-5678"),
                ("pissn", "0001-3714"),
                ("issn", "0987-0987"),
                ("year", "1998"),
                ("volume", "29"),
                ("number", "3"),
                ("supplement", None),
            ]
        )
        self.aop_data = dict(
            [("eissn", "0001-3714"), ("issn", "0001-3714"), ("year", "2019")]
        )
        self.bundle_id = "0001-3714-1998-v29-n3"
        self.issn = "0987-0987"

        if not os.path.isdir(config.get("ERRORS_PATH")):
            os.makedirs(config.get("ERRORS_PATH"))

    def tearDown(self):
        shutil.rmtree(config.get("ERRORS_PATH"))

    def test_get_documents_bundle_success(self):
        session_db = Session()
        session_db.documents_bundles.add(
            inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        )
        result = inserting.get_documents_bundle(
            session_db, self.bundle_id, True, self.issn
        )
        self.assertIsInstance(result, DocumentsBundle)
        self.assertEqual(result.id(), "0001-3714-1998-v29-n3")

    def test_get_documents_bundle_raises_exception_if_issue_and_not_found(self):
        session_db = MagicMock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        self.assertRaises(
            ValueError,
            inserting.get_documents_bundle,
            session_db,
            self.bundle_id,
            True,
            self.issn,
        )

    @patch("documentstore_migracao.processing.inserting.create_aop_bundle")
    def test_get_documents_bundle_creates_aop_bundle_is_aop_and_not_found(
        self, mk_create_aop_bundle
    ):
        session_db = MagicMock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        mk_create_aop_bundle.side_effect = DoesNotExist
        self.assertRaises(
            ValueError,
            inserting.get_documents_bundle,
            session_db,
            self.bundle_id,
            False,
            self.issn,
        )
        mk_create_aop_bundle.assert_any_call(session_db, self.issn)

    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.aops_bundle_id"
    )
    @patch("documentstore_migracao.processing.inserting.create_aop_bundle")
    def test_get_documents_bundle_raises_exception_if_creates_aop_bundle_none(
        self, mk_create_aop_bundle, mk_aops_bundle_id
    ):
        session_db = MagicMock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        mk_create_aop_bundle.side_effect = DoesNotExist
        self.assertRaises(
            ValueError,
            inserting.get_documents_bundle,
            session_db,
            self.bundle_id,
            False,
            self.issn,
        )

    @patch("documentstore_migracao.processing.inserting.create_aop_bundle")
    def test_get_documents_bundle_returns_created_aop_bundle(
        self, mk_create_aop_bundle
    ):
        session_db = MagicMock()
        mocked_aop_bundle = Mock()
        session_db.documents_bundles.fetch.side_effect = DoesNotExist
        mk_create_aop_bundle.return_value = mocked_aop_bundle
        result = inserting.get_documents_bundle(
            session_db, self.bundle_id, False, self.issn
        )
        self.assertEqual(result, mocked_aop_bundle)

    def test_create_aop_bundle_gets_journal(self):
        issn = "1234-0001"
        session_db = MagicMock()
        inserting.create_aop_bundle(session_db, issn)
        session_db.journals.fetch.assert_called_once_with(issn)

    def test_create_aop_bundle_raises_exception_if_journal_not_found(self):
        issn = "1234-0001"
        session_db = MagicMock()
        session_db.journals.fetch.side_effect = DoesNotExist
        self.assertRaises(DoesNotExist, inserting.create_aop_bundle, session_db, issn)

    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.aops_bundle_id"
    )
    def test_create_aop_bundle_uses_scielo_ids_generator_aops_bundle_id(
        self, mk_aops_bundle_id
    ):
        session_db = MagicMock()
        session_db.journals.fetch.return_value = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        inserting.create_aop_bundle(session_db, "0001-3714")
        mk_aops_bundle_id.assert_called_once_with("0001-3714")

    @patch("documentstore_migracao.processing.inserting.utcnow")
    @patch("documentstore_migracao.processing.inserting.ManifestDomainAdapter")
    def test_create_aop_bundle_registers_aop_bundle(
        self, MockManifestDomainAdapter, mk_utcnow
    ):
        mk_utcnow.return_value = "2019-01-02T05:00:00.000000Z"
        expected = {
            "_id": "0001-3714-aop",
            "created": "2019-01-02T05:00:00.000000Z",
            "updated": "2019-01-02T05:00:00.000000Z",
            "items": [],
            "metadata": {},
            "id": "0001-3714-aop",
        }
        mk_bundle_manifest = Mock()
        MockManifestDomainAdapter.return_value = mk_bundle_manifest
        session_db = MagicMock()
        session_db.journals.fetch.return_value = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        MockManifestDomainAdapter.assert_any_call(manifest=expected)
        session_db.documents_bundles.add.assert_called_once_with(
            data=mk_bundle_manifest
        )
        session_db.changes.add.assert_any_call(
            {
                "timestamp": "2019-01-02T05:00:00.000000Z",
                "entity": "DocumentsBundle",
                "id": "0001-3714-aop",
            }
        )

    @patch("documentstore_migracao.processing.inserting.utcnow")
    def test_create_aop_bundle_links_aop_bundle_to_journal(self, mk_utcnow):
        mk_utcnow.return_value = "2019-01-02T05:00:00.000000Z"
        mocked_journal_data = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        mk_bundle_manifest = Mock()
        session_db = MagicMock()
        session_db.journals.fetch.return_value = mocked_journal_data
        inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        session_db.journals.update.assert_called()
        session_db.changes.add.assert_any_call(
            {
                "timestamp": "2019-01-02T05:00:00.000000Z",
                "entity": "Journal",
                "id": SAMPLE_KERNEL_JOURNAL["id"],
            }
        )
        self.assertEqual(mocked_journal_data.ahead_of_print_bundle, "0001-3714-aop")

    def test_create_aop_bundle_returns_bundle(self):
        session_db = Session()
        mocked_journal_data = inserting.ManifestDomainAdapter(
            manifest=SAMPLE_KERNEL_JOURNAL
        )
        session_db.journals.add(mocked_journal_data)
        result = inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        self.assertIsInstance(result, DocumentsBundle)
        self.assertEqual(result.id(), "0001-3714-aop")

    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    @patch(
        "documentstore_migracao.processing.inserting.link_documents_bundles_with_documents"
    )
    def test_register_documents_in_documents_bundle(
        self, mk_link_documents_bundle_with_documents, mk_read_json_file
    ):
        documents = {
            "JwqGdMDrdcV3Z7MFHgtKvVk": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "04",
                "order": [
                    ["other", ""],
                    ["fpage", "00349"],
                    ["lpage", "00352"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            }
        }
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.side_effect = [journals, documents]

        err_filename = os.path.join(
            config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
        )

        session_db = Session()
        manifest = inserting.ManifestDomainAdapter(SAMPLE_ISSUES_KERNEL[0])
        session_db.documents_bundles.add(manifest)

        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )

        self.assertEqual(os.path.isfile(err_filename), True)
        with open(err_filename) as fp:
            content = fp.read()

            self.assertEqual(content, "0036-3634-2009-v45-n4\n")

    @patch("documentstore_migracao.processing.inserting.get_documents_bundle")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    @patch("documentstore_migracao.processing.inserting.scielo_ids_generator")
    def test_register_documents_in_documents_bundle_scielo_ids_generator(
        self, mk_scielo_ids_generator, mk_read_json_file, mk_get_documents_bundle
    ):
        documents = {
            "JwqGdMDrdcV3Z7MFHgtKvVk": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "04",
                "order": [
                    ["other", ""],
                    ["fpage", "00349"],
                    ["lpage", "00352"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
            "WCDX9F8pMhHDzy3fDYvth9x": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "order": [
                    ["other", ""],
                    ["fpage", "00392"],
                    ["lpage", "00397"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400007",
                "pissn": "0036-3634",
                "supplement": None,
                "year": "2009",
            },
        }
        journals = [SAMPLES_JOURNAL]

        mk_read_json_file.side_effect = [journals, documents]

        session_db = Session()
        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )
        mk_scielo_ids_generator.issue_id.assert_any_call(
            "0036-3634", "2009", "45", "04", None
        )
        mk_scielo_ids_generator.aops_bundle_id.assert_any_call("0036-3634")

    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    @patch("documentstore_migracao.processing.inserting.get_documents_bundle")
    def test_register_documents_in_documents_bundle_get_documents_bundle(
        self, mk_get_documents_bundle, mk_read_json_file
    ):
        documents = {
            "JwqGdMDrdcV3Z7MFHgtKvVk": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "04",
                "order": [
                    ["other", ""],
                    ["fpage", "00349"],
                    ["lpage", "00352"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
            "WCDX9F8pMhHDzy3fDYvth9x": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "order": [
                    ["other", ""],
                    ["fpage", "00392"],
                    ["lpage", "00397"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400007",
                "pissn": "0036-3634",
                "supplement": None,
                "year": "2009",
            },
        }
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.side_effect = [journals, documents]
        session_db = Session()
        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )
        mk_get_documents_bundle.assert_any_call(
            session_db, "0036-3634-2009-v45-n4", True, "0036-3634"
        )
        mk_get_documents_bundle.assert_any_call(
            session_db, "0036-3634-aop", False, "0036-3634"
        )

    @patch("documentstore_migracao.processing.inserting.link_documents_bundles_with_documents")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    @patch("documentstore_migracao.processing.inserting.get_documents_bundle")
    def test_register_documents_in_documents_bundle_link_documents_bundles_with_documents(
        self, mk_get_documents_bundle, mk_read_json_file, mk_link_documents_bundles_with_documents
    ):
        documents = {
            "JwqGdMDrdcV3Z7MFHgtKvVk": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "04",
                "order": [
                    ["other", ""],
                    ["fpage", "00349"],
                    ["lpage", "00352"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
                "scielo_id": "JwqGdMDrdcV3Z7MFHgtKvVk"
            },
            "WCDX9F8pMhHDzy3fDYvth9x": {
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "order": [
                    ["other", ""],
                    ["fpage", "00392"],
                    ["lpage", "00397"],
                    ["documents_bundle_pubdate", ["2009", "12", ""]],
                    ["document_pubdate", ["2009", "12", ""]],
                    ["elocation-id", ""],
                ],
                "pid": "S0021-25712009000400007",
                "pissn": "0036-3634",
                "supplement": None,
                "year": "2009",
                "scielo_id": "WCDX9F8pMhHDzy3fDYvth9x"
            },
        }
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.side_effect = [journals, documents]
        documents_bundle = Mock()
        mk_get_documents_bundle.return_value = documents_bundle
        session_db = Session()

        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )
        mk_link_documents_bundles_with_documents.assert_any_call(
            documents_bundle, ["JwqGdMDrdcV3Z7MFHgtKvVk"], session_db
        )

class TestDocumentManifest(unittest.TestCase):
    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def setUp(self, mock_minio_storage):
        self.package_path = os.path.join(SAMPLES_PATH, "0034-8910-rsp-47-02-0231")
        self.renditions_names = [
            "0034-8910-rsp-47-02-0231.pdf",
            "0034-8910-rsp-47-02-0231-en.pdf",
        ]
        self.renditions_urls_mock = [
            "prefix/0034-8910-rsp-47-02-0231.pdf.pdf",
            "prefix/0034-8910-rsp-47-02-0231.pdf-en.pdf",
        ]

        mock_minio_storage.register.side_effect = self.renditions_urls_mock
        self.renditions = inserting.get_document_renditions(
            self.package_path, self.renditions_names, "prefix", mock_minio_storage
        )

    def test_rendition_should_contains_file_name(self):
        self.assertEqual("0034-8910-rsp-47-02-0231.pdf", self.renditions[0]["filename"])
        self.assertEqual(
            "0034-8910-rsp-47-02-0231-en.pdf", self.renditions[1]["filename"]
        )

    def test_rendition_should_contains_url_link(self):
        self.assertEqual(self.renditions_urls_mock[0], self.renditions[0]["url"])
        self.assertEqual(self.renditions_urls_mock[1], self.renditions[1]["url"])

    def test_rendition_should_contains_size_bytes(self):
        self.assertEqual(110104, self.renditions[0]["size_bytes"])
        self.assertEqual(106379, self.renditions[1]["size_bytes"])

    def test_rendition_should_contains_mimetype(self):
        self.assertEqual("application/pdf", self.renditions[0]["mimetype"])
        self.assertEqual("application/pdf", self.renditions[1]["mimetype"])

    def test_renditon_should_contains_language(self):
        self.assertEqual("en", self.renditions[1]["lang"])

    def test_rendtion_should_not_contains_language(self):
        self.assertIsNone(self.renditions[0].get("lang"))


class TestDocumentRegister(unittest.TestCase):
    def setUp(self):
        self.package_path = os.path.join(SAMPLES_PATH, "0034-8910-rsp-47-02-0231")
        self.xml_path = os.path.join(self.package_path, "0034-8910-rsp-47-02-0231.xml")
        self.xml_etree = loadToXML(self.xml_path)
        self.package_files = [
            "0034-8910-rsp-47-02-0231-en.pdf",
            "0034-8910-rsp-47-02-0231-gf01-en.jpg",
            "0034-8910-rsp-47-02-0231-gf01-en.tif",
            "0034-8910-rsp-47-02-0231-gf01.jpg",
            "0034-8910-rsp-47-02-0231-gf01.tif",
            "0034-8910-rsp-47-02-0231.pdf",
            "0034-8910-rsp-47-02-0231.xml",
        ]

        self.second_package_path = os.path.join(
            SAMPLES_PATH, "0034-8910-rsp-47-02-0403"
        )

        self.second_xml_path = os.path.join(
            self.second_package_path, "0034-8910-rsp-47-02-0403.xml"
        )

        self.second_xml_etree = loadToXML(self.second_xml_path)

        self.second_package_files = [
            "0034-8910-rsp-47-02-0403-gf01.jpg",
            "0034-8910-rsp-47-02-0403-gf01.tif",
            "0034-8910-rsp-47-02-0403.pdf",
            "0034-8910-rsp-47-02-0403.xml",
        ]

        self.session = Session()

    def test_get_documents_assets_should_return_assets_and_additionals(self):
        assets, additionals = get_document_assets_path(
            self.xml_etree, self.package_files, self.package_path
        )

        self.assertEqual(
            ["0034-8910-rsp-47-02-0231-gf01", "0034-8910-rsp-47-02-0231-gf01-en"],
            list(assets.keys()),
        )

        for additional in additionals.values():
            with self.subTest(additional=additional):
                self.assertNotIn(".tif", additional)

    def test_get_documents_must_prefers_tif_files_instead_jpeg(self):
        assets, _ = get_document_assets_path(
            self.xml_etree, self.package_files, self.package_path
        )

        self.assertIn(
            "0034-8910-rsp-47-02-0231-gf01.tif", assets["0034-8910-rsp-47-02-0231-gf01"]
        )

    def test_get_documents_assets_must_contain_additional_files_with_no_prefered_files(
        self
    ):
        _, additionals = get_document_assets_path(
            self.xml_etree, self.package_files, self.package_path
        )

        self.assertIn(
            "0034-8910-rsp-47-02-0231-gf01.jpg",
            additionals["0034-8910-rsp-47-02-0231-gf01"],
        )

    def test_get_documents_assets_must_contain_additional_files_when_references_is_not_complete(
        self
    ):
        _, additionals = get_document_assets_path(
            self.second_xml_etree, self.second_package_files, self.second_package_path
        )

        self.assertIn(
            "0034-8910-rsp-47-02-0403-gf01.jpg",
            additionals["0034-8910-rsp-47-02-0403-gf01"],
        )

    def test_get_documents_assets_should_not_return_assets_path(self):
        assets, additionals = get_document_assets_path(
            self.xml_etree, [], self.package_path
        )

        self.assertEqual({}, additionals)
        self.assertEqual([None, None], list(assets.values()))

    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def test_put_assets_into_storage_should_ignore_missing_assets(self, mk_store):
        mk_store.register.side_effect = ["http://storage.io/mock-url.pdf"]

        assets = {"first-asset": "path-to.pdf", "second-asset": None}
        results = put_static_assets_into_storage(assets, "some-prefix", mk_store)

        for result in results:
            with self.subTest(result=result):
                self.assertNotEqual("second-asset", result["asset_id"])

    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def test_put_assets_should_raise_exception_when_ignore_missing_is_turned_off(
        self, mk_store
    ):
        mk_store.register.side_effect = ["http://storage.io/mock-url.pdf", TypeError]

        assets = {"first-asset": "path-to.pdf", "second-asset": None}

        with self.assertRaises(TypeError):
            put_static_assets_into_storage(
                assets, "some-prefix", mk_store, ignore_missing_assets=False
            )

    @patch("documentstore_migracao.tools.constructor.article_xml_constructor")
    @patch("documentstore_migracao.processing.inserting.register_document")
    @patch("documentstore_migracao.processing.inserting.os")
    @patch("documentstore_migracao.processing.inserting.DocumentsSorter")
    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def test_register_documents_should_import_sps_package(
        self,
        mk_store,
        mk_documents_sorter,
        mk_os,
        mk_register_document,
        mk_article_xml_constructor,
    ):
        mk_article_xml_constructor.side_effect = None
        mk_os.walk.side_effect = [
            [("/root/path/to/folder", "", ["file1", "file2", "file3.xml"])]
        ]
        mk_register_document.side_effect = [["/root/path/to/folder/file3.xml", None]]

        inserting.register_documents(
            self.session, mk_store, mk_documents_sorter, "/root"
        )

        mk_article_xml_constructor.assert_called()
        mk_register_document.assert_called_with(
            "/root/path/to/folder", self.session, mk_store
        )
        mk_documents_sorter.insert_document.assert_called()

    @patch("documentstore_migracao.utils.files.write_file")
    @patch("documentstore_migracao.processing.inserting.os")
    @patch("documentstore_migracao.processing.inserting.DocumentsSorter")
    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def test_register_documents_should_not_find_xml_file(
        self, mk_store, mk_documents_sorter, mk_os, mk_write_file
    ):

        mk_os.walk.side_effect = [[("/root/path/to/folder", "", ["file1", "file2"])]]

        with self.assertLogs(level="ERROR") as log:
            inserting.register_documents(
                self.session, mk_store, mk_documents_sorter, "/root"
            )

            self.assertIn("list index out of range", log[1][0])

            mk_write_file.assert_called()

    @patch("documentstore_migracao.processing.inserting.register_document")
    @patch("documentstore_migracao.processing.inserting.os")
    @patch("documentstore_migracao.processing.inserting.DocumentsSorter")
    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def test_register_documents_should_not_register_package_if_files_is_not_found(
        self, mk_store, mk_documents_sorter, mk_os, mk_register_document
    ):

        mk_os.walk.side_effect = [[("/root/path/to/folder", "", [])]]

        inserting.register_documents(
            self.session, mk_store, mk_documents_sorter, "/root"
        )

        mk_register_document.assert_not_called()
