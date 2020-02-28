import logging
from argparse import ArgumentParser

from documentstore_migracao.website.migrate_to_website import (
    connect_to_databases,
    migrate_logos_to_website,
)
from .base import base_parser, mongodb_parser


logger = logging.getLogger(__name__)


def migrate_logos_parser(args):
    parser = ArgumentParser(
        description="Journal Logos migration tool",
        parents=[base_parser(args), mongodb_parser(args)]
    )
    parser.add_argument(
        "--websitedb",
        help='URI to connect at SQLite database of new website. e.g: "sqlite:////path/to/database.db"',
        required=True,
    )
    parser.add_argument(
        "--website_img_dir",
        help='Path to website images media directory',
        required=True,
    )
    args = parser.parse_args(args)

    # Set log level
    level = getattr(logging, args.loglevel.upper())
    logger.setLevel(level)

    # Create MongoDB and SQLite connections
    sqlite_session = connect_to_databases(args.uri, args.db, args.websitedb)

    migrate_logos_to_website(sqlite_session, args.website_img_dir)
    logger.info("Logo migration complete successfully!")
