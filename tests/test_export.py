import os
import unittest
import requests
from copy import deepcopy
from unittest.mock import patch, ANY
from xylose.scielodocument import Journal, Article
from documentstore_migracao.export import journal, article
from documentstore_migracao.utils import request
from documentstore_migracao import exceptions, config
from . import SAMPLES_JOURNAL, SAMPLES_ARTICLE, SAMPLES_PATH, utils


class TestExportJournal(unittest.TestCase):
    @patch("documentstore_migracao.export.journal.request.get")
    def test_ext_journal(self, mk_request_get):

        mk_request_get.return_value.json.return_value = [SAMPLES_JOURNAL]

        result = journal.ext_journal("1234-5678")
        mk_request_get.assert_called_once_with(
            ANY, params={"collection": ANY, "issn": "1234-5678"}
        )

        self.assertEqual(result.title, SAMPLES_JOURNAL["v100"][0]["_"])

    @patch("documentstore_migracao.export.journal.request.get")
    @patch("documentstore_migracao.export.journal.logger.error")
    def test_ext_journal_catch_request_get_exception(
        self, mk_logger_error, mk_request_get
    ):
        mk_request_get.side_effect = request.HTTPGetError
        result = journal.ext_journal("1234-5678")
        mk_logger_error.assert_called_once_with(
            "Journal nao encontrado: scl: 1234-5678"
        )
        self.assertIsNone(result)

    @patch("documentstore_migracao.export.journal.request.get")
    def test_ext_identifiers(self, mk_request_get):

        journal.ext_identifiers()
        mk_request_get.assert_called_once_with(ANY, params={"collection": ANY})

    @patch("documentstore_migracao.export.journal.request.get")
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

    @patch("documentstore_migracao.export.journal.request.get")
    @patch("documentstore_migracao.export.article.RestfulClient.journals")
    def test_get_journals(self, mk_journals, mk_r):

        journal.get_journals()
        mk_journals.assert_called_once_with(collection=ANY)


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

    @patch("documentstore_migracao.export.article.logger.error")
    @patch("documentstore_migracao.export.article.request.get")
    def test_ext_article_log_error_if_request_raises_exception(
        self, mk_request_get, mk_logger_error
    ):
        article_pid = "S0036-36341997000100001"
        mk_request_get.side_effect = request.HTTPGetError
        result = article.ext_article(article_pid)
        self.assertIsNone(result)
        mk_logger_error.assert_called_once_with(
            "Erro coletando dados do artigo PID %s" % article_pid
        )

    @patch("documentstore_migracao.export.article.ext_article")
    def test_ext_article_json(self, mk_ext_article):

        result = article.ext_article_json("S0036-36341997000100001")
        mk_ext_article.assert_called_once_with("S0036-36341997000100001")

    @patch("documentstore_migracao.export.article.ext_article")
    def test_ext_article_json_returns_none_if_no_ext_article(self, mk_ext_article):
        mk_ext_article.return_value = None
        result = article.ext_article_json("S0036-36341997000100001")
        self.assertIsNone(result)

    @patch("documentstore_migracao.export.article.ext_article")
    def test_ext_article_txt(self, mk_ext_article):

        result = article.ext_article_txt("S0036-36341997000100001")
        mk_ext_article.assert_called_once_with(
            "S0036-36341997000100001", body="true", format="xmlrsps"
        )

    @patch("documentstore_migracao.export.article.ext_article")
    def test_ext_article_txt_returns_none_if_no_ext_article(self, mk_ext_article):
        mk_ext_article.return_value = None
        result = article.ext_article_txt("S0036-36341997000100001")
        self.assertIsNone(result)

    @patch("documentstore_migracao.export.article.get_articles")
    def test_get_all_articles_notXML(self, mk_get_articles):

        mk_get_articles.return_value = [Article(SAMPLES_ARTICLE)]
        result = article.get_all_articles_notXML("0036-3634")
        self.assertEqual(result[0][0], "S0036-36341997000100001")

    @patch("documentstore_migracao.export.article.get_articles")
    def test_get_all_articles_notXML_not_xml(self, mk_get_articles):

        copy_SAMPLES_ARTICLE = deepcopy(SAMPLES_ARTICLE)
        copy_SAMPLES_ARTICLE["version"] = "xml"

        mk_get_articles.return_value = [Article(copy_SAMPLES_ARTICLE)]
        result = article.get_all_articles_notXML("0036-3634")
        self.assertEqual(result, [])

    @patch("documentstore_migracao.export.article.RestfulClient.documents")
    def test_ext_article(self, mk_documents):

        result = article.get_articles("1234-5678")
        mk_documents.assert_called_once_with(collection=ANY, issn="1234-5678")

    @patch("documentstore_migracao.export.article.ext_article_txt")
    def test_get_not_xml_article(self, mk_ext_article_txt):

        obj = Article(SAMPLES_ARTICLE)
        article.get_not_xml_article(obj)
        mk_ext_article_txt.assert_called_once_with("S0036-36341997000100001")

    @patch("documentstore_migracao.export.article.ext_article_txt")
    def test_get_not_xml_article_xml(self, mk_ext_article_txt):

        copy_SAMPLES_ARTICLE = deepcopy(SAMPLES_ARTICLE)
        copy_SAMPLES_ARTICLE["version"] = "xml"

        obj = Article(copy_SAMPLES_ARTICLE)
        article.get_not_xml_article(obj)
        mk_ext_article_txt.assert_not_called()
