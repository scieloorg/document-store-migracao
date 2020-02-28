from unittest import TestCase, mock

from documentstore_migracao.main.migrate_logos import migrate_logos_parser

"""
migrate_logos --uri mongodb://0.0.0.0:27017/ --db document-store --websitedb ../data-webapp

usage: migrate_logos [-h] --uri URI --db DB --websitedb path

optional arguments:
  -h, --help            show this help message and exit
  --uri URI             URI to connect at MongoDB where the import will be
                        done, e.g: "mongodb://user:password@mongodb-
                        host/?authSource=admin"
  --db DB               Database name to import registers
  --websitedb path
                        Path to SQLite Database from new website
"""


class TestMigrateLogosParser(TestCase):
    @mock.patch("documentstore_migracao.main.migrate_logos.connect_to_databases")
    @mock.patch("documentstore_migracao.main.migrate_logos.migrate_logos_to_website")
    @mock.patch("documentstore_migracao.main.migrate_logos.base_parser")
    @mock.patch("documentstore_migracao.main.migrate_logos.mongodb_parser")
    @mock.patch("documentstore_migracao.main.migrate_logos.ArgumentParser")
    def test_argument_parser_description_and_mongodb_parser(
        self,
        MockArgumentParser,
        mk_mongodb_parser,
        mk_base_parser,
        mk_migrate_logos_to_website,
        mk_connect_to_databases,
    ):
        command_args = "--uri mongodb://0.0.0.0:27017/ --db opac --websitedb ../data-webapp --website_img_dir ../data-webapp/images".split()
        MockArgumentParser.return_value.parse_args.return_value.loglevel = "INFO"
        migrate_logos_parser(command_args)
        mk_mongodb_parser.assert_called_once_with(command_args)
        MockArgumentParser.assert_called_once_with(
            description="Journal Logos migration tool",
            parents=[mk_base_parser.return_value, mk_mongodb_parser.return_value]
        )

    @mock.patch("documentstore_migracao.main.migrate_logos.connect_to_databases")
    @mock.patch("documentstore_migracao.main.migrate_logos.migrate_logos_to_website")
    @mock.patch("documentstore_migracao.main.migrate_logos.ArgumentParser")
    def test_calls_parser_parse_args_with_command_args(
        self, MockArgumentParser, migrate_logos_to_website, mk_connect_to_databases
    ):
        mk_parser = mock.MagicMock(name="MockArgParser")
        mk_parser.parse_args.return_value.loglevel = "INFO"
        MockArgumentParser.return_value = mk_parser
        command_args = "--uri mongodb://0.0.0.0:27017/ --db opac --websitedb ../data-webapp --website_img_dir ../data-webapp/images".split()
        migrate_logos_parser(command_args)
        mk_parser.parse_args.assert_called_once_with(command_args)

    @mock.patch("documentstore_migracao.main.migrate_logos.connect_to_databases")
    @mock.patch("documentstore_migracao.main.migrate_logos.migrate_logos_to_website")
    @mock.patch("documentstore_migracao.main.migrate_logos.ArgumentParser")
    def test_adds_website_db_argument(
        self, MockArgumentParser, mk_migrate_logos_to_website, mk_connect_to_databases
    ):
        mk_parser = mock.MagicMock(name="MockArgParser")
        mk_parser.parse_args.return_value.loglevel = "INFO"
        MockArgumentParser.return_value = mk_parser
        command_args = "--uri mongodb://0.0.0.0:27017/ --db opac --websitedb ../data-webapp --website_img_dir ../data-webapp/images".split()
        migrate_logos_parser(command_args)
        mk_parser.add_argument.assert_any_call(
            "--websitedb",
            help='URI to connect at SQLite database of new website. e.g: "sqlite:////path/to/database.db"',
            required=True,
        )

    @mock.patch("documentstore_migracao.main.migrate_logos.connect_to_databases")
    @mock.patch("documentstore_migracao.main.migrate_logos.migrate_logos_to_website")
    @mock.patch("documentstore_migracao.main.migrate_logos.ArgumentParser")
    def test_adds_website_img_dir_argument(
        self, MockArgumentParser, mk_migrate_logos_to_website, mk_connect_to_databases
    ):
        mk_parser = mock.MagicMock(name="MockArgParser")
        mk_parser.parse_args.return_value.loglevel = "INFO"
        MockArgumentParser.return_value = mk_parser
        command_args = "--uri mongodb://0.0.0.0:27017/ --db opac --websitedb ../data-webapp --website_img_dir ../data-webapp/images".split()
        migrate_logos_parser(command_args)
        mk_parser.add_argument.assert_any_call(
            "--website_img_dir",
            help='Path to website images media directory',
            required=True,
        )

    @mock.patch("documentstore_migracao.main.migrate_logos.connect_to_databases")
    @mock.patch("documentstore_migracao.main.migrate_logos.migrate_logos_to_website")
    @mock.patch("documentstore_migracao.main.migrate_logos.ArgumentParser.error")
    def test_no_mongodb_parser_args(
        self, mk_parser_error, mk_migrate_logos_to_website, mk_connect_to_databases
    ):
        command_args = "--websitedb ../data-webapp --website_img_dir ../data-webapp/images".split()
        migrate_logos_parser(command_args)
        mk_parser_error.assert_any_call(
            "the following arguments are required: --uri, --db"
        )

    @mock.patch("documentstore_migracao.main.migrate_logos.connect_to_databases")
    @mock.patch("documentstore_migracao.main.migrate_logos.migrate_logos_to_website")
    @mock.patch("documentstore_migracao.main.migrate_logos.ArgumentParser.error")
    def test_no_website_args(
        self, mk_parser_error, mk_migrate_logos_to_website, mk_connect_to_databases
    ):
        command_args = "--uri mongodb://0.0.0.0:27017/ --db opac".split()
        migrate_logos_parser(command_args)
        mk_parser_error.assert_any_call(
            "the following arguments are required: --websitedb, --website_img_dir"
        )
