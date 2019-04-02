import logging
import sys
import os
from documentstore_migracao import exceptions, config
from documentstore_migracao.export import journal as export_journal
from documentstore_migracao.export import issue as export_issue
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


def process_isis_issue(extract=False):
    """Fachada com passo a passo do processamento que extrai e converte
    os fascículos de uma base ISIS para a base Kernel"""

    if extract:
        try:
            export_issue.extract_issues_from_isis()
        except (exceptions.ExtractError, exceptions.FetchEnvVariableError) as exc:
            logger.error(str(exc))
            sys.exit(1)
    try:
        issues_as_json = reading.read_issues_from_json()
        issues_as_xylose = conversion.conversion_issues_to_xylose(issues_as_json)
        filtered_issues = conversion.filter_issues(issues_as_xylose)
        issues_as_kernel = conversion.conversion_issues_to_kernel(filtered_issues)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(str(exc))
