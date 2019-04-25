""" module to methods to main  """
import pkg_resources
import argparse
import sys
import logging

from documentstore import adapters
from documentstore_migracao.processing import (
    extrated,
    reading,
    conversion,
    validation,
    packing,
    generation,
    pipeline,
)
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
        "--issn-journal", "-j", help="Processa somente o journal informado"
    )
    parser.add_argument(
        "--convetFile", "-c", help="Transformar somente o arquivos XML imformado"
    )
    parser.add_argument("--readFile", "-r", help="Ler somente o arquivos XML imformado")
    parser.add_argument("--packFile", "-p", help="Empacotar somente o documento XML imformado")
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
        choices=["journal", "issue"],
        required=True,
    )

    args = parser.parse_args(sargs)

    if args.command == "extract":
        extract_isis.create_output_dir(args.output)
        extract_isis.run(args.mst_file_path, args.output)
    elif args.command == "import":
        mongo = adapters.MongoDB(uri=args.uri, dbname=args.db)
        Session = adapters.Session.partial(mongo)

        if args.type == "journal":
            pipeline.import_journals(args.import_file, session=Session())
        elif args.type == "issue":
            pipeline.import_issues(args.import_file, session=Session())
    else:
        parser.print_help()


def main():
    """ method main to script setup.py """
    sys.exit(process(sys.argv[1:]))


def main_migrate_isis():
    sys.exit(migrate_isis(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(process(sys.argv[1:]))
