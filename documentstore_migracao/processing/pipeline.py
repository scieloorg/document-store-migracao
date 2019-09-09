import logging
import sys
import os
import json
from documentstore_migracao import exceptions, config
from documentstore_migracao.utils import extract_isis
from documentstore_migracao.processing import reading, conversion
from documentstore.interfaces import Session
from documentstore.domain import utcnow
from documentstore.exceptions import AlreadyExists, DoesNotExist
from documentstore_migracao.utils.xylose_converter import (
    issue_to_kernel,
    parse_date,
    date_to_datetime,
)

logger = logging.getLogger(__name__)


class ManifestDomainAdapter:
    """Complementa o manifesto produzido na fase de transformação
    para o formato exigido pelos adapters do Kernel para
    realizar a inserção no MongoDB"""

    def __init__(self, manifest):
        self._manifest = manifest

    def id(self) -> str:
        return self.manifest["id"]

    @property
    def manifest(self) -> dict:
        return self._manifest


def filter_issues(issues: list) -> list:
    """Filtra as issues em formato xylose sempre removendo
    os press releases e possibilitando a aplicação do filtro
    para as issues do tipo ahead of print"""

    filters = [
        lambda issue: not issue.type == "pressrelease",
        lambda issue: not issue.type == "ahead",
    ]

    for f in filters:
        issues = list(filter(f, issues))

    return issues


def import_journals(json_file: str, session: Session):
    """Fachada com passo a passo de processamento e carga de periódicos
    em formato JSON para a base Kernel"""

    try:
        journals_as_json = reading.read_json_file(json_file)
        journals_as_kernel = conversion.conversion_journals_to_kernel(
            journals=journals_as_json
        )

        for journal in journals_as_kernel:
            manifest = ManifestDomainAdapter(manifest=journal)

            try:
                session.journals.add(data=manifest)
                session.changes.add(
                    {"timestamp": utcnow(), "entity": "Journal", "id": manifest.id()}
                )
            except AlreadyExists as exc:
                logger.info(str(exc))
    except (FileNotFoundError, ValueError) as exc:
        logger.debug(str(exc))


def import_issues(json_file: str, session: Session):
    """Fachada com passo a passo de processamento e carga de fascículo
    em formato JSON para a base Kernel"""

    issues_as_json = reading.read_json_file(json_file)
    issues_as_xylose = conversion.conversion_issues_to_xylose(issues_as_json)
    issues_as_xylose = filter_issues(issues_as_xylose)
    issues_as_kernel = conversion.conversion_issues_to_kernel(issues_as_xylose)

    for issue in issues_as_kernel:
        manifest = ManifestDomainAdapter(manifest=issue)

        try:
            session.documents_bundles.add(manifest)
            session.changes.add(
                {
                    "timestamp": utcnow(),
                    "entity": "DocumentsBundle",
                    "id": manifest.id(),
                }
            )
        except AlreadyExists as exc:
            logger.info(str(exc))


def import_documents_bundles_link_with_journal(file_path: str, session: Session):
    """Fachada responsável por ler o arquivo de link entre
    journals e documents bundles e atualizar os journals com os
    identificadores dos bundles

    O formato esperado para o arquivo de link é:
    ```
    {
        "journal_id": [
            {
                "id": "issue-2",
                "order": "0002",
                "number": "02",
                "volume": "02",
                "year": "2019",
                "supplement": "supplement",
            },
            {
                "id": "issue-2",
                "order": "0002",
                "number": "02",
                "volume": "02",
                "year": "2019",
                "supplement": "supplement",
            },

        ]
    }
    ```
    """

    links = reading.read_json_file(file_path)

    for journal_id, bundles in links.items():
        try:
            _journal = session.journals.fetch(journal_id)

            for bundle_id in bundles:
                try:
                    _journal.add_issue(bundle_id)
                except AlreadyExists:
                    logger.debug(
                        "Bundle %s already exists in journal %s"
                        % (bundle_id["id"], journal_id)
                    )

            session.journals.update(_journal)
            session.changes.add(
                {"timestamp": utcnow(), "entity": "Journal", "id": _journal.id()}
            )
        except DoesNotExist:
            logger.debug(
                "Journal %s does not exists, cannot link bundles." % journal_id
            )


def link_documents_bundles_with_journals(issue_path: str, output_path: str):
    """Busca pelo relacionamento entre periódicos e fascículos a partir
    de arquivos JSON extraídos de uma base MST. O resultado é escrito
    em um arquivo JSON contendo um objeto (dict) com identificadores de
    periócios como chaves e arrays de ids das issues que compõe o
    periódico"""

    journals_bundles = {}
    extract_isis.create_output_dir(output_path)
    issues_as_json = reading.read_json_file(issue_path)
    issues = conversion.conversion_issues_to_xylose(issues_as_json)
    issues = filter_issues(issues)

    for issue in issues:
        journal_id = issue.data["issue"]["v35"][0]["_"]
        journals_bundles.setdefault(journal_id, [])
        _issue_id = issue_to_kernel(issue)["_id"]

        exist_item = len(
            list(filter(lambda d: d["id"] == _issue_id, journals_bundles[journal_id]))
        )

        if not exist_item:
            _creation_date = parse_date(issue.publication_date)

            _supplement = ""
            if issue.type is "supplement":
                _supplement = "0"

                if issue.supplement_volume:
                    _supplement = issue.supplement_volume
                elif issue.supplement_number:
                    _supplement = issue.supplement_number

            journals_bundles[journal_id].append(
                {
                    "id": _issue_id,
                    "order": issue.order,
                    "number": issue.number,
                    "volume": issue.volume,
                    "year": str(date_to_datetime(_creation_date).year),
                    "supplement": _supplement,
                }
            )

    with open(output_path, "w") as output:
        output.write(json.dumps(journals_bundles, indent=4, sort_keys=True))
