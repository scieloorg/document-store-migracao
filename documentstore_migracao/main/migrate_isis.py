import argparse

from .base import mongodb_parser
from documentstore import adapters as ds_adapters
from documentstore_migracao.processing import pipeline
from documentstore_migracao.utils import extract_isis


def migrate_isis_parser(sargs):
    parser = argparse.ArgumentParser(description="ISIS database migration tool")
    subparsers = parser.add_subparsers(title="Commands", metavar="", dest="command")

    extract_parser = subparsers.add_parser("extract", help="Extract mst files to json")
    extract_parser.add_argument(
        "mst_file_path", metavar="file", help="Path to MST file that will be extracted"
    )
    extract_parser.add_argument("--output", required=True, help="The output file path")

    import_parser = subparsers.add_parser(
        "import",
        parents=[mongodb_parser(sargs)],
        help="Process JSON files then import into Kernel database",
    )
    import_parser.add_argument(
        "import_file",
        metavar="file",
        help="JSON file path that contains mst extraction result, e.g: collection-title.json",
    )
    import_parser.add_argument(
        "--type",
        help="Type of JSON file that will load into Kernel database",
        choices=["journal", "issue", "documents-bundles-link"],
        required=True,
    )

    link_parser = subparsers.add_parser(
        "link",
        help="Generate JSON file of journals' ids and their issues linked by ISSN",
    )
    link_parser.add_argument(
        "journals",
        help="JSON file path that contains mst extraction result, e.g: ~/json/collection-title.json",
    )
    link_parser.add_argument(
        "issues",
        help="JSON file path that contains mst extraction result, e.g: ~/json/collection-issues.json",
    )
    link_parser.add_argument("--output", required=True, help="The output file path")

    args = parser.parse_args(sargs)

    if args.command == "extract":
        extract_isis.create_output_dir(args.output)
        extract_isis.run(args.mst_file_path, args.output)
    elif args.command == "import":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db)
        Session = ds_adapters.Session.partial(mongo)

        if args.type == "journal":
            pipeline.import_journals(args.import_file, session=Session())
        elif args.type == "issue":
            pipeline.import_issues(args.import_file, session=Session())
        elif args.type == "documents-bundles-link":
            pipeline.import_documents_bundles_link_with_journal(
                args.import_file, session=Session()
            )
    elif args.command == "link":
        pipeline.link_documents_bundles_with_journals(
            args.journals, args.issues, args.output
        )
    else:
        parser.print_help()
