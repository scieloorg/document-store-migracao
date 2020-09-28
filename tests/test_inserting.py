import unittest
from unittest.mock import patch, Mock, MagicMock, ANY, call
from copy import deepcopy
import os
import shutil
import json

from documentstore.domain import DocumentsBundle, Journal
from documentstore.exceptions import DoesNotExist

from documentstore_migracao.utils.xml import loadToXML
from documentstore_migracao.utils import manifest
from documentstore_migracao.processing import inserting
from documentstore_migracao import config
from documentstore_migracao.processing.inserting import (
    get_document_assets_path,
    put_static_assets_into_storage,
)
from .apptesting import Session
from . import (
    SAMPLE_ISSUES_KERNEL,
    SAMPLE_AOPS_KERNEL,
    SAMPLE_KERNEL_JOURNAL,
    SAMPLES_PATH,
    SAMPLES_JOURNAL,
)


class TestLinkDocumentsBundleWithDocuments(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.documents_bundle = DocumentsBundle(SAMPLE_ISSUES_KERNEL[0])
        self.session.documents_bundles.add(self.documents_bundle)

    def fetch_documents_bundle(self):
        return self.session.documents_bundles.fetch(self.documents_bundle.id())

    def test_should_link_documents_bundle_with_documents(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle,
            [{"id": "doc-1", "order": "0001"}, {"id": "doc-2", "order": "0002"}],
            self.session,
        )

        self.assertEqual(
            [{"id": "doc-1", "order": "0001"}, {"id": "doc-2", "order": "0002"}],
            self.fetch_documents_bundle().documents,
        )

    def test_should_not_insert_duplicated_documents(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle,
            [{"id": "doc-1", "order": "0001"}, {"id": "doc-1", "order": "0001"}],
            self.session,
        )

        self.assertEqual(
            [{"id": "doc-1", "order": "0001"}], self.fetch_documents_bundle().documents
        )

    def test_should_register_changes(self):
        inserting.link_documents_bundles_with_documents(
            self.documents_bundle,
            [{"id": "doc-1", "order": "0001"}, {"id": "doc-2", "order": "0002"}],
            self.session,
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
        bundle = DocumentsBundle(manifest=SAMPLE_ISSUES_KERNEL[0])
        session_db.documents_bundles.add(bundle)
        result = inserting.get_documents_bundle(
            session_db, bundle.id(), True, "0987-0987"
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

    @patch("documentstore_migracao.utils.gzip")
    def test_create_aop_bundle_gets_journal(self, mock_gzip):
        mock_gzip.compress.return_value = "bla".encode("ascii")
        issn = "1234-0001"
        session_db = MagicMock()
        inserting.create_aop_bundle(session_db, issn)
        session_db.journals.fetch.assert_called_once_with(issn)

    def test_create_aop_bundle_raises_exception_if_journal_not_found(self):
        issn = "1234-0001"
        session_db = MagicMock()
        session_db.journals.fetch.side_effect = DoesNotExist
        self.assertRaises(DoesNotExist, inserting.create_aop_bundle, session_db, issn)

    @patch("documentstore_migracao.utils.gzip")
    @patch(
        "documentstore_migracao.processing.inserting.scielo_ids_generator.aops_bundle_id"
    )
    def test_create_aop_bundle_uses_scielo_ids_generator_aops_bundle_id(
        self, mk_aops_bundle_id, mock_gzip
    ):
        mock_gzip.compress.return_value = "bla".encode("ascii")
        mk_aops_bundle_id.return_value = "bundle-01"
        session_db = MagicMock()
        session_db.journals.fetch.return_value = Journal(manifest=SAMPLE_KERNEL_JOURNAL)
        inserting.create_aop_bundle(session_db, "0001-3714")
        mk_aops_bundle_id.assert_called_once_with("0001-3714")

    def test_create_aop_bundle_links_aop_bundle_to_journal(self):
        session = Session()
        journal = Journal(manifest=SAMPLE_KERNEL_JOURNAL)
        session.journals.add(journal)

        inserting.create_aop_bundle(session, journal.id())
        self.assertEqual(
            session.journals.fetch(journal.id()).ahead_of_print_bundle, "0001-3714-aop"
        )

    def test_create_aop_bundle_returns_bundle(self):
        session_db = Session()
        session_db.journals.add(Journal(manifest=SAMPLE_KERNEL_JOURNAL))
        result = inserting.create_aop_bundle(session_db, SAMPLE_KERNEL_JOURNAL["id"])
        self.assertIsInstance(result, DocumentsBundle)
        self.assertEqual(result.id(), "0001-3714-aop")

    @patch("documentstore_migracao.processing.inserting.open")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    def test_register_documents_in_documents_bundle_no_bundle_found(
        self, mk_read_json_file, mk_open
    ):
        documents = [
            {
                "pid_v3": "JwqGdMDrdcV3Z7MFHgtKvVk",
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "4",
                "order": "00349",
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
        ]
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.return_value = journals
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            json.dumps(document) for document in documents
        ]
        mk_open.return_value.__enter__.return_value = mock_file
        mk_open.return_value.__exit__.return_value = Mock(return_value=False)

        session_db = Session()
        manifest = DocumentsBundle(SAMPLE_ISSUES_KERNEL[0])
        session_db.documents_bundles.add(manifest)

        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )

        err_filename = os.path.join(
            config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
        )
        self.assertEqual(os.path.isfile(err_filename), True)
        with open(err_filename) as fp:
            content = fp.read()
            self.assertEqual(content, "0036-3634-2009-v45-n4\n")

    @patch("documentstore_migracao.processing.inserting.open")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    def test_register_documents_in_documents_bundle_issn_with_spaces(
        self, mk_read_json_file, mk_open
    ):
        documents = [
            {
                "pid_v3": "JwqGdMDrdcV3Z7MFHgtKvVk",
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634  ",
                "number": "4",
                "order": "00349",
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
        ]
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.return_value = journals
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            json.dumps(document) for document in documents
        ]
        mk_open.return_value.__enter__.return_value = mock_file
        mk_open.return_value.__exit__.return_value = Mock(return_value=False)

        session_db = Session()
        manifest = DocumentsBundle(SAMPLE_ISSUES_KERNEL[0])
        session_db.documents_bundles.add(manifest)

        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )

        err_filename = os.path.join(
            config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
        )
        self.assertEqual(os.path.isfile(err_filename), True)
        with open(err_filename) as fp:
            content = fp.read()
            self.assertEqual(content, "0036-3634-2009-v45-n4\n")

    @patch("documentstore_migracao.processing.inserting.open")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    def test_register_documents_in_documents_bundle_no_issn_in_document(
        self, mk_read_json_file, mk_open
    ):
        documents = [
            {
                "pid_v3": "JwqGdMDrdcV3Z7MFHgtKvVk",
                "acron": "aiss",
                "eissn": None,
                "issn": None,
                "number": "4",
                "order": "00349",
                "pid": "S0021-25712009000400001",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
        ]
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.return_value = journals
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            json.dumps(document) for document in documents
        ]
        mk_open.return_value.__enter__.return_value = mock_file
        mk_open.return_value.__exit__.return_value = Mock(return_value=False)

        inserting.register_documents_in_documents_bundle(
            Session(), "/tmp/documents.json", "/tmp/journals.json"
        )

        err_filename = os.path.join(
            config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
        )
        self.assertEqual(os.path.isfile(err_filename), True)
        with open(err_filename) as fp:
            content = fp.read()
            self.assertEqual(content, "JwqGdMDrdcV3Z7MFHgtKvVk\n")

    @patch(
        "documentstore_migracao.processing.inserting.link_documents_bundles_with_documents"
    )
    @patch("documentstore_migracao.processing.inserting.open")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    @patch("documentstore_migracao.processing.inserting.get_documents_bundle")
    def test_register_documents_in_documents_bundle_get_documents_bundle(
        self,
        mk_get_documents_bundle,
        mk_read_json_file,
        mk_open,
        mk_link_documents_bundles_with_documents,
    ):
        documents = [
            {
                "pid_v3": "JwqGdMDrdcV3Z7MFHgtKvVk",
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "04",
                "order": "00349",
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
            {
                "pid_v3": "WCDX9F8pMhHDzy3fDYvth9x",
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "order": "00349",
                "pid": "S0021-25712009000400007",
                "pissn": "0036-3634",
                "supplement": None,
                "year": "2009",
            },
        ]
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.return_value = journals
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            json.dumps(document) for document in documents
        ]
        mk_open.return_value.__enter__.return_value = mock_file
        mk_open.return_value.__exit__.return_value = Mock(return_value=False)
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

    @patch(
        "documentstore_migracao.processing.inserting.link_documents_bundles_with_documents"
    )
    @patch("documentstore_migracao.processing.inserting.open")
    @patch("documentstore_migracao.processing.inserting.reading.read_json_file")
    @patch("documentstore_migracao.processing.inserting.get_documents_bundle")
    def test_register_documents_in_documents_bundle_link_documents_bundles_with_documents(
        self,
        mk_get_documents_bundle,
        mk_read_json_file,
        mk_open,
        mk_link_documents_bundles_with_documents,
    ):
        documents = [
            {
                "pid_v3": "JwqGdMDrdcV3Z7MFHgtKvVk",
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "number": "04",
                "order": "00349",
                "pid": "S0021-25712009000400001",
                "pissn": "0036-3634",
                "supplement": None,
                "volume": "45",
                "year": "2009",
            },
            {
                "pid_v3": "WCDX9F8pMhHDzy3fDYvth9x",
                "acron": "aiss",
                "eissn": None,
                "issn": "0036-3634",
                "order": "00350",
                "pid": "S0021-25712009000400007",
                "pissn": "0036-3634",
                "supplement": None,
                "year": "2009",
            },
        ]
        journals = [SAMPLES_JOURNAL]
        mk_read_json_file.return_value = journals
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            json.dumps(document) for document in documents
        ]
        mk_open.return_value.__enter__.return_value = mock_file
        mk_open.return_value.__exit__.return_value = Mock(return_value=False)
        documents_bundle = Mock()
        mk_get_documents_bundle.return_value = documents_bundle
        session_db = Session()

        inserting.register_documents_in_documents_bundle(
            session_db, "/tmp/documents.json", "/tmp/journals.json"
        )
        mk_link_documents_bundles_with_documents.assert_any_call(
            documents_bundle,
            [{"id": "JwqGdMDrdcV3Z7MFHgtKvVk", "order": "00349"}],
            session_db,
        )


class TestDocumentManifest(unittest.TestCase):
    @patch("documentstore_migracao.object_store.minio.MinioStorage")
    def setUp(self, mock_minio_storage):
        self.package_path = os.path.join(SAMPLES_PATH, "0034-8910-rsp-47-02-0231")
        self.renditions_urls_mock = [
            "prefix/0034-8910-rsp-47-02-0231.pdf.pdf",
            "prefix/0034-8910-rsp-47-02-0231.pdf-en.pdf",
        ]

        mock_minio_storage.register.side_effect = self.renditions_urls_mock
        self.json_manifest = os.path.join(self.package_path, "manifest.json")
        with open(self.json_manifest, "w") as json_file:
            json_file.write(
                json.dumps(
                    {
                        "pt": "rsp/v47n2/0034-8910-rsp-47-02-0231.pdf",
                        "en": "rsp/v47n2/0034-8910-rsp-47-02-0231-en.pdf",
                    }
                )
            )

        self.renditions = inserting.get_document_renditions(
            self.package_path, "prefix", mock_minio_storage
        )

    def tearDown(self):
        os.remove(self.json_manifest)

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

    def test_rendition_should_not_contains_language(self):
        self.assertEqual("pt", self.renditions[0]["lang"])

    def test_when_manifest_file_does_not_exist_it_should_return_an_empty_list(self):
        os.unlink(self.json_manifest)
        self.renditions = inserting.get_document_renditions(
            self.package_path, "prefix", MagicMock()
        )
        self.assertEqual(0, len(self.renditions))

        with open(self.json_manifest, "w") as f:
            pass

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

