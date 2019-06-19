""" module to methods to main  """

import sys
import logging

from .migrate_isis import migrate_isis_parser
from .migrate_articlemeta import migrate_articlemeta_parser
from .tools import tools_parser


logger = logging.getLogger(__name__)


def main_migrate_articlemeta():
    """ method main to script setup.py """
    try:
        sys.exit(migrate_articlemeta_parser(sys.argv[1:]))
    except KeyboardInterrupt:
        # É convencionado no shell que o programa finalizado pelo signal de
        # código N deve retornar o código N + 128.
        sys.exit(130)
    except Exception as exc:
        logger.exception(
            "erro durante a execução da função "
            "'migrate_articlemeta_parser' com os args %s",
            sys.argv[1:],
        )
        sys.exit("Um erro inexperado ocorreu: %s" % exc)


def main_migrate_isis():
    sys.exit(migrate_isis_parser(sys.argv[1:]))


def tools():
    sys.exit(tools_parser(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(migrate_articlemeta_parser(sys.argv[1:]))
