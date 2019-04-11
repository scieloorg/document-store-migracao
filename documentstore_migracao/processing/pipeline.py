import logging
import sys
import os
from documentstore_migracao import exceptions, config
from documentstore_migracao.utils import extract_isis
from documentstore_migracao.processing import reading, conversion


logger = logging.getLogger(__name__)


def import_journals(json_file: str):
    """Fachada com passo a passo de processamento e carga de periódicos
    em formato JSON para a base Kernel"""

    try:
        journals_as_json = reading.read_json_file(json_file)
        journals_as_kernel = conversion.conversion_journals_to_kernel(
            journals=journals_as_json
        )

        # TODO: LOAD journals into Kernel DB
    except (FileNotFoundError, ValueError) as exc:
        logger.debug(str(exc))
