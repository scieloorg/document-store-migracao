""" module to methods to main  """
import pkg_resources
import argparse
import sys
import os, logging


from documentstore_migracao.processing import extrated, reading

logger = logging.getLogger(__name__)


def main():
    """ method to main process """

    packtools_version = pkg_resources.get_distribution("documentstore-migracao").version
    parser = argparse.ArgumentParser(description="Document Store (Kernel) - Migração")

    parser.add_argument(
        "--all", "-a", default="True", help="Processa todos os periodicos"
    )

    parser.add_argument(
        "--issn-journal", "-j", help="Processa somente o journal informado"
    )

    parser.add_argument("--version", "-v", action="version", version=packtools_version)
    parser.add_argument("--loglevel", default="WARNING")

    args = parser.parse_args()

    # CHANGE LOGGER
    level = getattr(logging, args.loglevel.upper())
    logger = logging.getLogger()
    logger.setLevel(level)


    reading.reading_article_xml()


#    if args.issn_journal:
#        extrated.extrated_jornal_data(args.issn_journal)
#        return

#    if args.all:
#        extrated.extrated_all_data()
#        return




if __name__ == "__main__":
    main()
