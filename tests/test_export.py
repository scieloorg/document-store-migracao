import os
import unittest
from unittest.mock import patch, ANY
from xylose.scielodocument import Journal, Article
from documentstore_migracao.export import journal, article
from documentstore_migracao import exceptions, config
from documentstore_migracao.export.journal import extract_journals_from_isis
from . import SAMPLES_JOURNAL, SAMPLES_ARTICLE, SAMPLES_PATH, utils


@patch("documentstore_migracao.export.journal.request.get")
class TestExportJournal(unittest.TestCase):
    def test_ext_journal(self, mk_request_get):

        mk_request_get.return_value.json.return_value = [SAMPLES_JOURNAL]

        result = journal.ext_journal("1234-5678")
        mk_request_get.assert_called_once_with(
            ANY, params={"collection": ANY, "issn": "1234-5678"}
        )

        self.assertEqual(result.title, SAMPLES_JOURNAL["v100"][0]["_"])

    def test_ext_identifiers(self, mk_request_get):

        journal.ext_identifiers()
        mk_request_get.assert_called_once_with(ANY, params={"collection": ANY})

    @patch("documentstore_migracao.export.journal.ext_identifiers")
    @patch("documentstore_migracao.export.journal.ext_journal")
    def test_get_all_journal(self, mk_ext_journal, mk_ext_identifiers, mk_r):

        obj_journal = Journal(SAMPLES_JOURNAL)
        mk_ext_identifiers.return_value = {
            "objects": ["ANY", "ANY", {"code": "36341997000100001"}]
        }
        mk_ext_journal.return_value = obj_journal

        result = journal.get_all_journal()
        self.assertEqual(result[0], obj_journal)


class TestExportArticle(unittest.TestCase):
    @patch("documentstore_migracao.export.article.request.get")
    def test_ext_identifiers(self, mk_request_get):

        article.ext_identifiers("1234-5678")
        mk_request_get.assert_called_once_with(
            ANY, params={"collection": ANY, "issn": "1234-5678"}
        )

    @patch("documentstore_migracao.export.article.request.get")
    def test_ext_article(self, mk_request_get):

        result = article.ext_article("S0036-36341997000100001")
        mk_request_get.assert_called_once_with(
            ANY, params={"collection": ANY, "code": "S0036-36341997000100001"}
        )

    @patch("documentstore_migracao.export.article.ext_article")
    def test_ext_article_json(self, mk_ext_article):

        result = article.ext_article_json("S0036-36341997000100001")
        mk_ext_article.assert_called_once_with("S0036-36341997000100001")

    @patch("documentstore_migracao.export.article.ext_article")
    def test_ext_article_txt(self, mk_ext_article):

        result = article.ext_article_txt("S0036-36341997000100001")
        mk_ext_article.assert_called_once_with(
            "S0036-36341997000100001", body="true", format="xmlrsps"
        )

    @patch("documentstore_migracao.export.article.get_articles")
    def test_get_all_articles_notXML(self, mk_get_articles):

        obj_journal = Journal(SAMPLES_JOURNAL)
        mk_get_articles.return_value = [Article(SAMPLES_ARTICLE)]
        result = article.get_all_articles_notXML("0036-3634")
        self.assertEqual(result[0][0], "S0036-36341997000100001")


class ExportJournalFromIsisTest(unittest.TestCase):
    def setUp(self):
        self.journal_sample_mst = os.path.join(
            SAMPLES_PATH, "base-isis-sample", "title", "title.mst"
        )
        self.journal_sample = os.path.join(
            SAMPLES_PATH, "base-isis-sample", "title", "title.json"
        )
        self.source_path = config.get("SOURCE_PATH")

    def test_raise_extract_exception_if_jython_is_not_in_path(self):
        with utils.environ(PATH=""):
            self.assertRaises(exceptions.ExtractError, extract_journals_from_isis)

    def test_raise_extract_exception_if_base_not_found(self):
        with utils.environ(ISIS_BASE_PATH="", SOURCE_PATH=self.source_path):
            self.assertRaises(exceptions.ExtractError, extract_journals_from_isis)

    def test_raise_extract_exception_if_source_folder_is_not_accessible(self):
        with utils.environ(ISIS_BASE_PATH=self.journal_sample_mst, SOURCE_PATH=""):
            self.assertRaises(exceptions.ExtractError, extract_journals_from_isis)
