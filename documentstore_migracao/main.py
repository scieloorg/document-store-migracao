""" module to methods to main  """
import pkg_resources
import argparse
import sys
import os, logging


from documentstore_migracao.processing import extrated, reading, conversion

logger = logging.getLogger(__name__)


def main():
    """ method to main process """

    packtools_version = pkg_resources.get_distribution("documentstore-migracao").version
    parser = argparse.ArgumentParser(description="Document Store (Kernel) - Migração")

    parser.add_argument(
        "--extrateFiles",
        "-e",
        action="store_true",
        help="Baixa todos os XML dos periodicos",
    )
    parser.add_argument(
        "--readFiles",
        "-r",
        action="store_true",
        help="Processa somente os arquivos XML baixados",
    )
    parser.add_argument(
        "--conversionFiles",
        "-c",
        action="store_true",
        help="Converte somente os arquivos XML baixados",
    )

    parser.add_argument(
        "--issn-journal", "-j", help="Processa somente o journal informado"
    )
    parser.add_argument(
        "--pathFile", "-p", help="Transformar somente o arquivos XML imformado"
    )

    parser.add_argument("--version", "-v", action="version", version=packtools_version)
    parser.add_argument("--loglevel", default="WARNING")

    args = parser.parse_args()

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

    elif args.pathFile:
        conversion.conversion_article_xml(args.pathFile)

    elif args.issn_journal:
        extrated.extrated_selected_journal(args.issn_journal)


if __name__ == "__main__":
    main()
