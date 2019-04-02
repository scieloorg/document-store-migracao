import logging
import sys
import os
from documentstore_migracao import exceptions, config
from documentstore_migracao.export import journal as export_journal
from documentstore_migracao.processing import reading, conversion

logger = logging.getLogger(__name__)


def process_isis_journal(extract=False):
    """Fachada com passo a passo do processamento que extrai e converte
    os periódicos de uma base ISIS para a base Kernel"""

    if extract:
        try:
            if not "Bruma" in os.environ.get(
                "CLASSPATH", ""
            ) or not "jyson" in os.environ.get("CLASSPATH", ""):
                raise exceptions.ExtractError(
                    "As bibliotecas Bruma e Jyson precisam estar no CLASSPATH"
                )

            export_journal.extract_journals_from_isis()
        except (exceptions.ExtractError, exceptions.FetchEnvVariableError) as exc:
            logger.error(str(exc))
            sys.exit(1)

    try:
        journals_as_json = reading.read_journals_from_json()
        journals_as_kernel = conversion.conversion_journals_to_kernel(
            journals=journals_as_json
        )

    except (FileNotFoundError, ValueError) as exc:
        logger.error(str(exc))
