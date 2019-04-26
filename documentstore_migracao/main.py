""" module to methods to main  """
import pkg_resources
import argparse
import sys
import logging

from documentstore import adapters as ds_adapters
from documentstore_migracao.processing import (
    extrated,
    reading,
    conversion,
    validation,
    packing,
    generation,
    pipeline,
    constructor,
    inserting,
)
from documentstore_migracao.object_store import minio
from documentstore_migracao.utils import extract_isis

logger = logging.getLogger(__name__)


def process(args):
    """ method to main process """

    packtools_version = pkg_resources.get_distribution("documentstore-migracao").version
    parser = argparse.ArgumentParser(description="Document Store (Kernel) - Migração")

    parser.add_argument(
        "--extrateFiles",
        "-E",
        action="store_true",
        help="Baixa todos os XML dos periodicos",
    )
    parser.add_argument(
        "--readFiles",
        "-R",
        action="store_true",
        help="Processa todos os arquivos XML baixados",
    )
    parser.add_argument(
        "--conversionFiles",
        "-C",
        action="store_true",
        help="Converte todos os arquivos XML de 'source'",
    )
    parser.add_argument(
        "--validationFiles",
        "-V",
        action="store_true",
        help="Valida todos os arquivos XML de 'source'",
    )
    parser.add_argument(
        "--move_to_processed_source",
        "-MS",
        action="store_true",
        help="Move os arquivos válidos de 'source' para 'processed_source'",
    )
    parser.add_argument(
        "--move_to_valid_xml",
        "-MC",
        action="store_true",
        help="Move os arquivos válidos de 'conversion' para 'valid_xml'",
    )
    parser.add_argument(
        "--packFiles",
        "-P",
        action="store_true",
        help="Processa todos os arquivos XML baixados",
    )
    parser.add_argument(
        "--generationFiles",
        "-G",
        action="store_true",
        help="Gera os html de todos os arquivos XML convertidos",
    )
    parser.add_argument(
        "--constructionFiles",
        "-CT",
        action="store_true",
        help="Altera os xmls ja convertidos ou validados",
    )

    parser.add_argument(
        "--issn-journal", "-j", help="Processa somente o journal informado"
    )
    parser.add_argument(
        "--convetFile", "-c", help="Transformar somente o arquivos XML imformado"
    )
    parser.add_argument("--readFile", "-r", help="Ler somente o arquivos XML imformado")
    parser.add_argument(
        "--packFile", "-p", help="Empacotar somente o documento XML imformado"
    )
    parser.add_argument(
        "--valideFile", "-v", help="Valida somente o arquivos XML imformado"
    )

    parser.add_argument("--version", action="version", version=packtools_version)
    parser.add_argument("--loglevel", default="WARNING")

    args = parser.parse_args(args)

    # CHANGE LOGGER
    level = getattr(logging, args.loglevel.upper())
    logger = logging.getLogger()
    logger.setLevel(level)

    if args.readFiles:
        reading.reading_article_ALLxml()

    elif args.conversionFiles:
        conversion.conversion_article_ALLxml()

    elif args.extrateFiles:
        extrated.extrated_all_data()

    elif args.validationFiles:
        validation.validator_article_ALLxml(
            args.move_to_processed_source, args.move_to_valid_xml
        )
    elif args.packFiles:
        packing.packing_article_ALLxml()

    elif args.generationFiles:
        generation.article_ALL_html_generator()

    elif args.constructionFiles:
        constructor.article_ALL_constructor()

    elif args.convetFile:
        conversion.conversion_article_xml(args.convetFile)

    elif args.valideFile:
        validation.validator_article_xml(args.valideFile)

    elif args.readFile:
        reading.reading_article_xml(args.readFile, False)

    elif args.packFile:
        packing.packing_article_xml(args.packFile)

    elif args.issn_journal:
        extrated.extrated_selected_journal(args.issn_journal)

    else:
        raise SystemExit("Vc deve escolher algum parametro")

    return 0


def mongodb_parser(args):
    """Parser utilizado para capturar informações sobre conexão
    com o MongoDB"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--uri",
        required=True,
        help="""URI to connect at MongoDB where the import
        will be done, e.g: "mongodb://user:password@mongodb-host/?authSource=admin" """,
    )

    parser.add_argument("--db", required=True, help="Database name to import registers")

    return parser


def migrate_isis(sargs):
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


def import_documents(sargs):
    parser = argparse.ArgumentParser(
        description="Document Store (Kernel) database migration tool"
    )
    subparsers = parser.add_subparsers(title="Commands", metavar="", dest="command")

    import_parser = subparsers.add_parser(
        "import",
        help="Process XML files then import into Kernel database",
        parents=[mongodb_parser(sargs)],
    )

    # MINION OPTION
    import_parser.add_argument(
        "--minio_host",
        required=True,
        help="""Host to connect to Min.io ObjectStorage, e.g: "play.min.io:9000" """,
    )
    import_parser.add_argument(
        "--minio_access_key", required=True, help="Access key to Min.io, e.g: minion"
    )
    import_parser.add_argument(
        "--minio_secret_key", required=True, help="Secure key to Min.io, e.g: minion123"
    )
    import_parser.add_argument(
        "--minio_is_secure",
        default=False,
        help="if connection wich to Min.io is secure, default False",
        action="store_true",
    )

    args = parser.parse_args(sargs)
    if args.command == "import":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db)
        DB_Session = ds_adapters.Session.partial(mongo)

        storage = minio.MinioStorage(
            minio_host=args.minio_host,
            minio_access_key=args.minio_access_key,
            minio_secret_key=args.minio_secret_key,
            minio_secure=args.minio_is_secure,
        )

        inserting.inserting_document_store(session_db=DB_Session(), storage=storage)

    else:
        parser.print_help()


def main():
    """ method main to script setup.py """
    sys.exit(process(sys.argv[1:]))


def main_migrate_isis():
    sys.exit(migrate_isis(sys.argv[1:]))


def main_import_documents():
    sys.exit(import_documents(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(process(sys.argv[1:]))
