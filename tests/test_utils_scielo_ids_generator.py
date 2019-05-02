import unittest
from unittest.mock import patch
from uuid import UUID
from documentstore_migracao.utils import scielo_ids_generator


class TestUtilsSciELOIDsGenerator_for_document(unittest.TestCase):
    def test_uuid2str(self):
        uuid = "585b0b68-aa1d-41ab-8f19-aaa37c516337"
        self.assertEqual(
            scielo_ids_generator.uuid2str(UUID(uuid)),
            "FX6F3cbyYmmwvtGmMB7WCgr")

    def test_str2uuid(self):
        self.assertEqual(
            scielo_ids_generator.str2uuid("FX6F3cbyYmmwvtGmMB7WCgr"),
            UUID("585b0b68-aa1d-41ab-8f19-aaa37c516337"),
        )

    @patch("documentstore_migracao.utils.scielo_ids_generator.uuid4")
    def test_generate_scielo_pid(self, mk_uuid4):
        mk_uuid4.return_value = UUID("585b0b68-aa1d-41ab-8f19-aaa37c516337")

        self.assertEqual(
            scielo_ids_generator.generate_scielo_pid(),
            "FX6F3cbyYmmwvtGmMB7WCgr")


class TestUtilsSciELOIDsGenerator_for_documents_bundle(unittest.TestCase):

    def test_issn_year_volume_number_suppl(self):
        self.assertEqual(
            scielo_ids_generator.documents_bundle_id(
                'ISSN', 'YEAR', 'VOLUME', '03', 'SUPPL'
            ),
            'ISSN-YEAR-vVOLUME-n3-sSUPPL'
        )

    def test_issn_year_volume_number(self):
        self.assertEqual(
            scielo_ids_generator.documents_bundle_id(
                'ISSN', 'YEAR', 'VOLUME', '03'
            ),
            'ISSN-YEAR-vVOLUME-n3'
        )

    def test_issn_year_volume_suppl(self):
        self.assertEqual(
            scielo_ids_generator.documents_bundle_id(
                'ISSN', 'YEAR', 'VOLUME', supplement='SUPPL'
            ),
            'ISSN-YEAR-vVOLUME-sSUPPL'
        )

    def test_issn_year_volume(self):
        self.assertEqual(
            scielo_ids_generator.documents_bundle_id(
                'ISSN', 'YEAR', 'VOLUME'
            ),
            'ISSN-YEAR-vVOLUME'
        )

    def test_issn_year_number(self):
        self.assertEqual(
            scielo_ids_generator.documents_bundle_id(
                'ISSN', 'YEAR', number='03'
            ),
            'ISSN-YEAR-n3'
        )

