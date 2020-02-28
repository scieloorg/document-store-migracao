import tempfile
import shutil
import os
from unittest import TestCase, mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from documentstore_migracao import exceptions
from documentstore_migracao.utils import request
from documentstore_migracao.website import migrate_to_website
from documentstore_migracao.website.migrate_to_website import Base, Image


class TestMigrateLogosToWebsite(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.bind = cls.engine
        Base.metadata.create_all()

    def setUp(self):
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.website_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.website_dir)

    @mock.patch("documentstore_migracao.website.migrate_to_website.Journal")
    def test_raises_error_if_no_journals(self, MockJournal):
        MockJournal.objects.all.return_value = []
        self.assertRaises(
            exceptions.NoJournalInWebsiteError,
            migrate_to_website.migrate_logos_to_website,
            self.session,
            self.website_dir
        )

    @mock.patch("documentstore_migracao.website.migrate_to_website.logger")
    @mock.patch("documentstore_migracao.website.migrate_to_website.request.get")
    @mock.patch("documentstore_migracao.website.migrate_to_website.Journal")
    def test_logs_error_if_logo_url_in_curent_website_not_found(
        self, MockJournal, mk_request_get, MockLogger
    ):
        MockJournal.objects.all.return_value = [mock.MagicMock()]
        mk_request_get.side_effect = request.HTTPGetError("HTTP Get Error")
        migrate_to_website.migrate_logos_to_website(self.session, self.website_dir)
        MockLogger.error.assert_any_call("HTTP Get Error")

    @mock.patch("documentstore_migracao.website.migrate_to_website.request.get")
    @mock.patch("documentstore_migracao.website.migrate_to_website.Journal")
    def test_no_updates_if_logo_url_in_curent_website_not_found(
        self, MockJournal, mk_request_get
    ):
        MockedJournal = mock.MagicMock()
        MockJournal.objects.all.return_value = [MockedJournal]
        mk_request_get.side_effect = request.HTTPGetError("HTTP Get Error")
        migrate_to_website.migrate_logos_to_website(self.session, self.website_dir)
        MockedJournal.save.assert_not_called()

    @mock.patch("documentstore_migracao.website.migrate_to_website.request.get")
    @mock.patch("documentstore_migracao.website.migrate_to_website.Journal")
    def test_saves_image_file_in_website_dir(self, MockJournal, mk_request_get):
        MockedJournal = mock.MagicMock(acronym="test")
        MockJournal.objects.all.return_value = [MockedJournal]
        MockedResponse = mock.MagicMock(content=b"123Image")
        mk_request_get.return_value = MockedResponse
        migrate_to_website.migrate_logos_to_website(self.session, self.website_dir)
        self.assertTrue(
            os.path.isfile(os.path.join(self.website_dir, "test_glogo.gif"))
        )

    @mock.patch("documentstore_migracao.website.migrate_to_website.request.get")
    @mock.patch("documentstore_migracao.website.migrate_to_website.Journal")
    def test_adds_image_record_in_sqlite_db(self, MockJournal, mk_request_get):
        MockedJournal = mock.MagicMock(acronym="test")
        MockJournal.objects.all.return_value = [MockedJournal]
        MockedResponse = mock.MagicMock(content=b"123Image")
        mk_request_get.return_value = MockedResponse
        migrate_to_website.migrate_logos_to_website(self.session, self.website_dir)
        q = self.session.query(Image).filter_by(name="test_glogo.gif").\
            filter_by(path="images/test_glogo.gif").first()
        self.assertIsNotNone(q)

    @mock.patch("documentstore_migracao.website.migrate_to_website.request.get")
    @mock.patch("documentstore_migracao.website.migrate_to_website.Journal")
    def test_updates_journal_with_logo_url(self, MockJournal, mk_request_get):
        MockedJournal = mock.MagicMock(acronym="test")
        MockJournal.objects.all.return_value = [MockedJournal]
        MockedResponse = mock.MagicMock(content=b"123Image")
        mk_request_get.return_value = MockedResponse
        migrate_to_website.migrate_logos_to_website(self.session, self.website_dir)
        self.assertEqual(MockedJournal.logo_url, "/media/images/test_glogo.gif")
        MockedJournal.save.assert_called_once()
