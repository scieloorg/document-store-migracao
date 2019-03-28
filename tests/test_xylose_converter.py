import unittest
from documentstore_migracao.utils.xylose_converter import journal_to_kernel, parse_date
from xylose.scielodocument import Journal


def get_metadata_item(bundle, field):
    try:
        return bundle["metadata"][field][0][1]
    except KeyError:
        return None
    except IndexError:
        return None


class TestXyloseDateConverter(unittest.TestCase):
    def test_full_date_case(self):
        self.assertEqual("2019-01-02T00:00:00.000000Z", parse_date("2019-01-02"))

    def test_year_month_case(self):
        self.assertEqual("2019-12-01T00:00:00.000000Z", parse_date("2019-12"))

    def test_only_year_case(self):
        self.assertEqual("2019-01-01T00:00:00.000000Z", parse_date("2019"))


class TestXyloseJournalConverter(unittest.TestCase):
    def setUp(self):
        self.json_journal = {
            "v100": [{"_": "sample"}],
            "v68": [{"_": "spl"}],
            "v940": [{"_": "20190128"}],
            "v50": [{"_": "C"}],
            "v901": [
                {"l": "es", "_": "Publicar artículos"},
                {"l": "pt", "_": "Publicar artigos"},
                {"l": "en", "_": "To publish articles"},
            ],
            "v151": [{"_": "sample."}],
            "v150": [{"_": "sample"}],
            "v400": [{"_": "0001"}],
            "v435": [{"t": "PRINT", "_": "0001"}, {"t": "ONLIN", "_": "2448-167X"}],
            "v51": [
                {
                    "a": "20190128",
                    "b": "C",
                    "c": "20190129",
                    "d": "S",
                    "e": "suspended-by-editor",
                }
            ],
            "v441": [{"_": "Health Sciences"}],
            "v140": [{"_": "SCIELO"}],
            "v854": [{"_": "AREA"}],
            "v692": [{"_": "test.com"}],
            "v710": [{"_": "next journal"}],
            "v610": [{"_": "previous journal"}],
            "v64": [{"_": "editor@email.com"}],
            "v63": [{"_": "Rua de exemplo, 1, São Paulo, SP, Brasil"}],
        }

        self._journal = Journal(self.json_journal)

    def test_bundle_id_joins_acronym_and_collection(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("2448-167X", journal["id"])
        self.assertEqual("2448-167X", journal["_id"])

    def test_bundle_metadata_fields_timestamps_and_created_date_should_be_equals(self):
        journal = journal_to_kernel(self._journal)

        for field, value in journal.get("metadata").items():
            if field == "status":
                continue

            date = value[0][0]
            with self.subTest(date=date):
                self.assertEqual(journal.get("created"), date)

    def test_raise_exception_if_journal_hasnt_id(self):
        with self.assertRaises(ValueError):
            del self.json_journal["v435"]
            del self.json_journal["v400"]
            journal_to_kernel(Journal(self.json_journal))

    def test_journal_has_title(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("sample", get_metadata_item(journal, "title"))

    def test_journal_hasnt_title(self):
        del self.json_journal["v100"]
        journal = journal_to_kernel(self._journal)
        self.assertIsNone(get_metadata_item(journal, "title"))

    def test_journal_has_mission(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(3, len(get_metadata_item(journal, "mission")))

    def test_journal_has_title_iso(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("sample.", get_metadata_item(journal, "title_iso"))

    def test_journal_has_short_title(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("sample", get_metadata_item(journal, "short_title"))

    def test_journal_has_scielo_issn(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("0001", get_metadata_item(journal, "scielo_issn"))

    def test_journal_has_print_issn(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("0001", get_metadata_item(journal, "print_issn"))

    def test_journal_has_electronic_issn(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("2448-167X", get_metadata_item(journal, "electronic_issn"))

    def test_journal_has_status(self):
        journal = journal_to_kernel(self._journal)
        _status = journal["metadata"]["status"]

        self.assertEqual(2, len(_status))
        self.assertEqual("suspended-by-editor", _status[1][1]["reason"])

    def test_journal_status_timestamps_should_be_different_from_created_date(self):
        journal = journal_to_kernel(self._journal)
        _status = journal["metadata"]["status"]

        self.assertNotEqual(journal["created"], _status[1][0])

    def test_journal_has_subject_areas(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(
            ["HEALTH SCIENCES"], get_metadata_item(journal, "subject_areas")
        )

    def test_journal_has_sponsors(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual([{"name": "SCIELO"}], get_metadata_item(journal, "sponsors"))

    def test_journal_has_subject_categories(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(["AREA"], get_metadata_item(journal, "subject_categories"))

    def test_journal_has_online_submission_url(self):
        journal = journal_to_kernel(self._journal)
        self.assertIsNotNone(get_metadata_item(journal, "online_submission_url"))

    def test_journal_has_next_journal(self):
        journal = journal_to_kernel(self._journal)
        self.assertIsNotNone(get_metadata_item(journal, "next_journal"))

    def test_journal_has_previous_journal(self):
        journal = journal_to_kernel(self._journal)
        self.assertIsNotNone(get_metadata_item(journal, "previous_journal"))

    def test_journal_has_contact_email(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(
            "editor@email.com", get_metadata_item(journal, "contact")["email"]
        )

    def test_journal_has_contact_address(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(
            "Rua de exemplo, 1, São Paulo, SP, Brasil",
            get_metadata_item(journal, "contact")["address"],
        )
