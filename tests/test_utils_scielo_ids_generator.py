import unittest
from unittest.mock import patch
from uuid import UUID
from documentstore_migracao.utils import scielo_ids_generator


class TestUtilsSciELOIDsGenerator_for_document(unittest.TestCase):
    def test_uuid2str(self):
        uuid = "585b0b68-aa1d-41ab-8f19-aaa37c516337"
        self.assertEqual(
            scielo_ids_generator.uuid2str(UUID(uuid)), "FX6F3cbyYmmwvtGmMB7WCgr"
        )

    def test_str2uuid(self):
        self.assertEqual(
            scielo_ids_generator.str2uuid("FX6F3cbyYmmwvtGmMB7WCgr"),
            UUID("585b0b68-aa1d-41ab-8f19-aaa37c516337"),
        )

    @patch("documentstore_migracao.utils.scielo_ids_generator.uuid4")
    def test_generate_scielo_pid(self, mk_uuid4):
        mk_uuid4.return_value = UUID("585b0b68-aa1d-41ab-8f19-aaa37c516337")

        self.assertEqual(
            scielo_ids_generator.generate_scielo_pid(), "FX6F3cbyYmmwvtGmMB7WCgr"
        )


class TestUtilsSciELOIDsGenerator_for_issue_bundle(unittest.TestCase):
    def test_issn_year_volume_number_suppl(self):
        self.assertEqual(
            scielo_ids_generator.issue_id(
                "ISSN", "YEAR", "VOLUME", "03", "SUPPL"
            ),
            "ISSN-YEAR-vVOLUME-n3-sSUPPL",
        )

    def test_issn_year_volume_number(self):
        self.assertEqual(
            scielo_ids_generator.issue_id("ISSN", "YEAR", "VOLUME", "03"),
            "ISSN-YEAR-vVOLUME-n3",
        )

    def test_issn_year_volume_suppl(self):
        self.assertEqual(
            scielo_ids_generator.issue_id(
                "ISSN", "YEAR", "VOLUME", supplement="SUPPL"
            ),
            "ISSN-YEAR-vVOLUME-sSUPPL",
        )

    def test_issn_year_volume(self):
        self.assertEqual(
            scielo_ids_generator.issue_id("ISSN", "YEAR", "VOLUME"),
            "ISSN-YEAR-vVOLUME",
        )

    def test_issn_year_number(self):
        self.assertEqual(
            scielo_ids_generator.issue_id("ISSN", "YEAR", number="03"),
            "ISSN-YEAR-n3",
        )

    def test_issue_id_returns_ISSN_YEAR_VOL_and_no_number_because_it_is_00(self):
        self.assertEqual(
            scielo_ids_generator.issue_id("ISSN", "YEAR", volume="19", number="00"),
            "ISSN-YEAR-v19",
        )

    def test_issue_id_returns_ISSN_YEAR_NUM_and_no_vol_because_it_is_00(self):
        self.assertEqual(
            scielo_ids_generator.issue_id("ISSN", "YEAR", volume="00", number="19"),
            "ISSN-YEAR-n19",
        )

    def test_issue_id_returns_ISSN_aop_because_vol_00_and_num_00(self):
        self.assertEqual(
            scielo_ids_generator.issue_id(
                "ISSN", "YEAR", volume="00", number="00"),
            "ISSN-aop",
        )


class TestNormalizeVolumeAndNumber(unittest.TestCase):

    def test_normalize_volume_and_number_returns_None_and_None_for_empty_str(self):
        result = scielo_ids_generator.normalize_volume_and_number("", "")
        self.assertEqual(result, (None, None))

    def test_normalize_volume_and_number_returns_None_and_None_for_00(self):
        result = scielo_ids_generator.normalize_volume_and_number("00", "00")
        self.assertEqual(result, (None, None))

    def test_normalize_volume_and_number_returns_None_and_None_for_None(self):
        result = scielo_ids_generator.normalize_volume_and_number(None, None)
        self.assertEqual(result, (None, None))

    def test_normalize_volume_and_number_returns_None_and_None_for_number_ahead(self):
        result = scielo_ids_generator.normalize_volume_and_number(None, "ahead")
        self.assertEqual(result, (None, None))

    def test_normalize_volume_and_number_returns_volume_and_number(self):
        result = scielo_ids_generator.normalize_volume_and_number("vol", "num")
        self.assertEqual(result, ("vol", "num"))

    def test_normalize_volume_and_number_returns_volume_and_number_no_zero_on_the_left(self):
        result = scielo_ids_generator.normalize_volume_and_number("01", "009")
        self.assertEqual(result, ("1", "9"))
