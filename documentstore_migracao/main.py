""" module to methods to main  """
import pkg_resources
import argparse
import sys
import os, logging


from documentstore_migracao.processing import extrated, reading, conversion, validation

logger = logging.getLogger(__name__)


def process(args):
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
        help="Processa todos os arquivos XML baixados",
    )
    parser.add_argument(
        "--conversionFiles",
        "-c",
        action="store_true",
        help="Converte todos os arquivos XML baixados",
    )
    parser.add_argument(
        "--validationFiles",
        "-V",
        action="store_true",
        help="Converte todos os arquivos XML baixados",
    )

    parser.add_argument(
        "--issn-journal", "-j", help="Processa somente o journal informado"
    )
    parser.add_argument(
        "--pathFile", "-p", help="Transformar somente o arquivos XML imformado"
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
        validation.validator_article_ALLxml()

    elif args.pathFile:
        conversion.conversion_article_xml(args.pathFile)

    elif args.valideFile:
        validation.validator_article_xml(args.valideFile)

    elif args.issn_journal:
        extrated.extrated_selected_journal(args.issn_journal)

    return 0


def migrate_journals():
    """
    JSON -> Kernel
    - Ler Dados
    - Normalizar dados para o Kernel
        - Isis2Json -> Xylose
        - SciELO Manager -> JSON
    - Inserir no MongoDB do Kernel
    """
    parser = argparse.ArgumentParser(description="Document Store (Kernel) - Journal Migration")
    parser.add_argument(
        "--data_origin",
        "-d",
        help="Data origin: ISIS Bases (i) or SciELO Manager (m)",
        choices=['i', 'm'],
    )
    parser.add_argument(
        "--extract",
        "-e",
        action='store_true',
        help="Extract data from ISIS Bases (default: don't extract)",
    )
    parser.add_argument(
        '--logging_file',
        '-o',
        help='Full path to the log file'
    )
    parser.add_argument(
        '--logging_level',
        '-l',
        default="INFO",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Loggin level'
    )
    args = parser.parse_args()
    # args2 = parser.parse_args()

    # CHANGE LOGGER
    level = getattr(logging, args.logging_level.upper())
    logger = logging.getLogger()
    logger.setLevel(level)

    if args.data_origin == 'i':
        # import pdb; pdb.set_trace()
        if args.extract:
            print("Extract ISIS Data")
            print("Save ISIS Data to JSON")
        print("Reading JSON")
        print("Load Xylose")
        print("Normalize data to Kernel")
    elif args.data_origin == 'm':
        print("Connect to Manager Database")
        print("Reading Database")
        print("Normalize data to Kernel")
    else:
        parser.error("Choose (i)SIS Bases or SciELO (m)anager\n")

    print("Saving data to Kernel")


def main():
    """ method main to script setup.py """
    sys.exit(process(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(process(sys.argv[1:]))
