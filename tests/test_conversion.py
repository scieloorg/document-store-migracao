import tempfile
import json
import shutil
from unittest import TestCase, mock
from pathlib import Path

from lxml import etree
from xylose.scielodocument import Article

from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao.processing import conversion


def save_json_file(source_path, document_pid, article_metadata):
    json_file_path = Path(source_path).joinpath(Path(document_pid + ".json"))
    metadata = {
        "article": article_metadata,
    }
    with json_file_path.open("w") as json_file:
        json.dump(metadata, json_file)


class TestGetArticleDates(TestCase):
    def test_should_return_issue_publication_date_if_it_is_presente(self):
        metadata = {
            "article": {"v65": [{"_": "19970300"}], "v223": [{"_": "20200124"}],},
        }
        article = Article(metadata)
        __, issue_pubdate = conversion.get_article_dates(article)
        self.assertEqual(issue_pubdate, ("1997", "03", ""))

    def test_should_return_document_publication_date_if_it_is_presente(self):
        metadata = {
            "article": {"v65": [{"_": "19970300"}], "v223": [{"_": "20200124"}],},
        }
        article = Article(metadata)
        document_pubdate, __ = conversion.get_article_dates(article)
        self.assertEqual(document_pubdate, ("2020", "01", "24"))

    def test_should_return_creation_date_if_no_document_publication_date(self):
        metadata = {
            "article": {"v65": [{"_": "19970300"}], "v93": [{"_": "20000401"}],},
        }
        article = Article(metadata)
        document_pubdate, __ = conversion.get_article_dates(article)
        self.assertEqual(document_pubdate, ("2000", "04", "01"))

    def test_should_return_update_date_if_no_document_publication_date_nor_creation_date(
        self,
    ):
        metadata = {
            "article": {"v65": [{"_": "19970300"}], "v91": [{"_": "19990319"}],},
        }
        article = Article(metadata)
        document_pubdate, __ = conversion.get_article_dates(article)
        self.assertEqual(document_pubdate, ("1999", "03", "19"))

    def test_should_return_none_if_no_document_dates(self):
        metadata = {
            "article": {"v65": [{"_": "19970300"}],},
        }
        article = Article(metadata)
        document_pubdate, __ = conversion.get_article_dates(article)
        self.assertIsNone(document_pubdate)
