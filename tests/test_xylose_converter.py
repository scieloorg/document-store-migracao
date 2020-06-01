from copy import deepcopy
import unittest
import json
from pathlib import Path

from documentstore_migracao.utils.xylose_converter import (
    journal_to_kernel,
    issue_to_kernel,
    parse_date,
    get_journal_issns_from_issue,
    find_documents_bundles,
    json_file_to_xylose_article,
)
from xylose.scielodocument import Journal, Issue
from . import SAMPLE_ISSUES_JSON, SAMPLE_KERNEL_JOURNAL, SAMPLE_ISSUES_KERNEL


def get_metadata_item(bundle, field):
    try:
        return bundle["metadata"][field]
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

    def test_parse_date_should_convert_month_locales_abbreviated_name(self):
        self.assertEqual("2020-06-03T00:00:00.000000Z", parse_date("2020-Jun-03"))

    def test_parse_date_should_convert_month_locales_full_name(self):
        self.assertEqual("2020-07-03T00:00:00.000000Z", parse_date("2020-July-03"))

    def test_parse_date_should_use_the_last_month_when_it_is_a_range_of_months(self):
        self.assertEqual("2020-12-01T00:00:00.000000Z", parse_date("2020-Oct-Dec"))

    def test_date_parse_should_discart_invalid_day(self):
        self.assertEqual("2020-06-01T00:00:00.000000Z", parse_date("2020-06-40"))

    def test_date_parse_should_use_only_the_year_if_month_is_invalid_and_day_is_not(
        self,
    ):
        self.assertEqual("2020-01-01T00:00:00.000000Z", parse_date("2020-30-03"))


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
            "v400": [{"_": "0001-3714"}],
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
            "v480": [{"_": "Sociedade Brasileira de Medicina Tropical - SBMT"}],
            "v310": [{"_": "BR"}],
            "v320": [{"_": "MG"}],
            "v490": [{"_": "Uberaba"}],
        }

        self._journal = Journal(self.json_journal)

    def test_bundle_id_joins_acronym_and_collection(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("0001-3714", journal["id"])
        self.assertEqual("0001-3714", journal["_id"])

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
        self.assertEqual("0001-3714", get_metadata_item(journal, "scielo_issn"))

    def test_journal_has_print_issn(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("0001", get_metadata_item(journal, "print_issn"))

    def test_journal_has_electronic_issn(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual("2448-167X", get_metadata_item(journal, "electronic_issn"))

    def test_journal_has_status_history(self):
        journal = journal_to_kernel(self._journal)
        _status = journal["metadata"]["status_history"]

        self.assertEqual(2, len(_status))
        self.assertEqual("suspended-by-editor", _status[1]["reason"])

    def test_journal_status_timestamps_should_be_different_from_created_date(self):
        journal = journal_to_kernel(self._journal)
        _status = journal["metadata"]["status_history"][-1]
        self.assertNotEqual(journal["created"], _status["date"])

    def test_journal_has_subject_areas(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(
            ["Health Sciences"], get_metadata_item(journal, "subject_areas")
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
        self.assertEqual("editor@email.com", journal["metadata"]["contact"]["email"])

    def test_journal_has_contact_address(self):
        journal = journal_to_kernel(self._journal)
        self.assertEqual(
            "Rua de exemplo, 1, São Paulo, SP, Brasil",
            journal["metadata"]["contact"]["address"],
        )

    def test_journal_has_institution_responsible_for(self):
        journal = journal_to_kernel(self._journal)
        expected = tuple(
            [
                {
                    "name": "Sociedade Brasileira de Medicina Tropical - SBMT",
                    "country_code": "BR",
                    "country": "Brazil",
                    "state": "MG",
                    "city": "Uberaba",
                }
            ]
        )
        self.assertEqual(
            expected, get_metadata_item(journal, "institution_responsible_for")
        )


class TestXyloseIssueConverter(unittest.TestCase):
    def setUp(self):
        self.issue_json = {"v65": [{"_": "20190129"}], "v35": [{"_": "2448-167X"}]}

        self._issue = Issue({"issue": self.issue_json})
        self.issue = issue_to_kernel(self._issue)

    def test_issue_has_issn_in_id(self):
        self.assertIn("2448-167X", self.issue["id"])
        self.assertIn("2448-167X", self.issue["_id"])

    def test_issue_has_year_in_id(self):
        self.assertIn("2019", self.issue["id"])
        self.assertIn("2019", self.issue["_id"])

    def test_issue_should_be_created_date_equals_to_publication_date(self):
        self.assertEqual("2019-01-29T00:00:00.000000Z", self.issue["created"])

    def test_issue_should_be_updated_date_equals_to_publication_date(self):
        self.assertEqual("2019-01-29T00:00:00.000000Z", self.issue["updated"])

    def test_issue_has_volume(self):
        self.issue_json["v31"] = [{"_": "21"}]
        self.issue = issue_to_kernel(self._issue)

        self.assertEqual("21", self.issue["metadata"]["volume"])

        self.assertIn("v21", self.issue["id"])
        self.assertIn("v21", self.issue["_id"])

    def test_issue_has_number(self):
        self.assertIsNone(self.issue["metadata"].get("volume"))
        self.issue_json["v32"] = [{"_": "1"}]
        self.issue = issue_to_kernel(self._issue)

        self.assertEqual("1", self.issue["metadata"]["number"])

        self.assertIn("n1", self.issue["id"])

    def test_issue_has_supplement_when_supplement_volume_is_not_none(self):
        self.issue_json["v131"] = [{"_": "3"}]
        self.issue = issue_to_kernel(self._issue)
        self.assertEqual("3", self.issue["metadata"]["supplement"])

        self.assertIn("s3", self.issue["id"])

    def test_issue_has_supplement_when_supplement_number_is_not_none(self):
        self.issue_json["v132"] = [{"_": "2"}]
        self.issue = issue_to_kernel(self._issue)
        self.assertEqual("2", self.issue["metadata"]["supplement"])

        self.assertIn("s2", self.issue["id"])
        self.assertIn("s2", self.issue["_id"])

    def test_issue_has_titles(self):
        self.issue_json["v33"] = [{"l": "pt", "_": "Algum título"}]
        self.issue = issue_to_kernel(self._issue)
        self.assertEqual(
            [{"language": "pt", "value": "Algum título"}],
            self.issue["metadata"]["titles"],
        )

    def test_issue_has_publication_months(self):
        self.assertEqual({"month": 1}, self.issue["metadata"]["publication_months"])

    def test_publication_months_start_and_end_is_equal(self):
        self.issue_json["v43"] = [{"m": "Feb./Feb."}]
        self.issue = issue_to_kernel(self._issue)
        self.assertEqual(
            {"range": (2, 2)}, self.issue["metadata"]["publication_months"],
        )

    def test_publication_months_range_of_six_months(self):
        self.issue_json["v43"] = [{"m": "Jan./Jun."}]
        self.issue = issue_to_kernel(self._issue)
        self.assertEqual(
            {"range": (1, 6)}, self.issue["metadata"]["publication_months"]
        )


class TestFindDocumentBundles(unittest.TestCase):
    def setUp(self):
        self.issue_json = deepcopy(SAMPLE_ISSUES_JSON[0])
        self.basic_issue = Issue({"issue": self.issue_json})

    def test_should_return_all_journal_issns_from_issue(self):
        issns = get_journal_issns_from_issue(self.basic_issue)
        self.assertEqual(["0001-3714"], issns)

    def test_should_should_include_electronic_issn(self):
        self.issue_json["v435"] = [{"t": "ONLIN", "_": "10000-000A"}]
        issue = Issue({"issue": self.issue_json})
        issns = get_journal_issns_from_issue(issue)
        issns.sort()
        expected = ["0001-3714", "10000-000A"]
        self.assertEqual(expected, issns)

    def test_should_link_journal_and_issues(self):
        issues = [Issue({"issue": self.issue_json})]
        journal_issues = find_documents_bundles(SAMPLE_KERNEL_JOURNAL, issues)
        self.assertEqual([SAMPLE_ISSUES_KERNEL[0]["id"]], journal_issues)

    def test_should_not_find_bundles_for_journal(self):
        self.issue_json["v35"] = [{"_": "0001-3714X"}]
        issues = [Issue({"issue": self.issue_json})]
        journal_issues = find_documents_bundles(SAMPLE_KERNEL_JOURNAL, issues)
        self.assertListEqual([], journal_issues)


class TestJsonFileToXyloseArticle(unittest.TestCase):
    def setUp(self):
        self.json_file_path = Path("./tests/samples/S0036-36341997000100001.json")

    def test_should_return_xylose_article(self):
        article = json_file_to_xylose_article(self.json_file_path)
        with self.json_file_path.open() as json_file:
            article_data = json.load(json_file)
            self.assertEqual(article.data, article_data)
