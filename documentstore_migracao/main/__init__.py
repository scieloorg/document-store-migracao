""" module to methods to main  """

import sys

from .migrate_isis import migrate_isis_parser
from .migrate_articlemeta import migrate_articlemeta_parser
from .tools import tools_parser


def main():
    """ method main to script setup.py """
    sys.exit(migrate_articlemeta_parser(sys.argv[1:]))


def main_migrate_isis():
    sys.exit(migrate_isis_parser(sys.argv[1:]))


def tools():
    sys.exit(tools_parser(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(migrate_articlemeta_parser(sys.argv[1:]))
