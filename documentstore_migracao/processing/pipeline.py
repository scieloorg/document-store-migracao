import logging
import sys
import os
import json
import gzip
import re
from typing import List, Generator

from lxml import etree
from tqdm import tqdm

from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao.utils.extract_isis import run as run_isis2json
from documentstore_migracao.utils import xml as XMLUtils

from documentstore.interfaces import Session
from documentstore.domain import utcnow, Journal, DocumentsBundle
from documentstore.exceptions import AlreadyExists, DoesNotExist

from documentstore_migracao import exceptions, config
from documentstore_migracao.utils import (
    extract_isis,
    add_document,
    add_journal,
    update_journal,
    add_bundle,
    update_bundle,
    get_nested,
)
from documentstore_migracao.processing import reading, conversion
from documentstore_migracao.utils.xylose_converter import (
    issue_to_kernel,
    parse_date,
    date_to_datetime,
)
from documentstore_migracao.utils.files import get_files_in_path

logger = logging.getLogger(__name__)


__all__ = [
    "import_journals",
    "import_issues",
    "import_documents_bundles_link_with_journal",
    "link_documents_bundles_with_journals",
]


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
        manifests = conversion.conversion_journals_to_kernel(journals=journals_as_json)

        for manifest in manifests:
            journal = Journal(manifest=manifest)
            try:
                add_journal(session, journal)
            except AlreadyExists as exc:
                logger.info(exc)
    except (FileNotFoundError, ValueError) as exc:
        logger.debug(exc)


def import_issues(json_file: str, session: Session):
    """Fachada com passo a passo de processamento e carga de fascículo
    em formato JSON para a base Kernel"""

    issues_as_json = reading.read_json_file(json_file)
    issues_as_xylose = conversion.conversion_issues_to_xylose(issues_as_json)
    issues_as_xylose = filter_issues(issues_as_xylose)
    manifests = conversion.conversion_issues_to_kernel(issues_as_xylose)

    for manifest in manifests:
        issue = DocumentsBundle(manifest=manifest)
        try:
            add_bundle(session, issue)
        except AlreadyExists as exc:
            logger.info(exc)


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
    for journal_id, bundles_entries in links.items():
        try:
            journal = session.journals.fetch(journal_id)
        except DoesNotExist:
            logger.debug(
                'Journal "%s" does not exists, cannot link bundles.', journal_id
            )
        else:
            for bundle_entry in bundles_entries:
                # `bundle_entry` é um dict armazenado no Journal que o relaciona
                # com determinado bundle.
                try:
                    journal.add_issue(bundle_entry)
                except AlreadyExists:
                    logger.debug(
                        'Bundle "%s" already exists in journal "%s"',
                        bundle_entry["id"],
                        journal_id,
                    )
            update_journal(session, journal)


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


def update_articles_mixed_citations(
    source: str,
    output_folder: str = None,
    override: bool = False,
    disable_bar: bool = False,
):
    """Atualiza os elementos de ``mixed-citations`` em um ou mais XMLs.

    O resultado da atualização pode ser salvo no próprio arquivo XML ou em
    outro arquivo XML em um diretório diferente utilizando o parâmetro
    ``output_folder``.
    
    Marque o `override` como `True` para sobrescrever todas as mixed citations
    das referências, caso contrário, apenas as referências sem mixed citations
    serão atualizadas (padrão)."""

    CACHE_DIR = config.get("PARAGRAPH_CACHE_PATH")

    if not os.path.exists(source):
        raise FileNotFoundError("Source path '%s' does not exist" % source)
    elif output_folder is not None and not os.path.exists(output_folder):
        raise FileNotFoundError("Output folder '%s' does not exist" % output_folder)

    def get_references_text_from_paragraphs(paragraphs: list, pid: str) -> dict:
        """Filtra as referências a partir dos paragráfos.

        As referências possuem a mesma estrutura dos parágrafos na base MST
        exceto pelo índice (v888). Considera-se uma referência os registros que
        possuem o índice/order (v888) e a chave de `PID` para o artigo (v880).

        Params:
            paragraphs (List[dict]): Lista de parágrafos extraídos da base MST
            pid (str): Identificador do documento no formato `scielo-v2`

        Returns:
            references (Dict[str, str]): Dicionário com referências filtradas,
            e.g: {"order": "text"}
        """
        references = {}

        for paragraph in paragraphs:
            article_pid = get_nested(paragraph, "v880", 0, "_", default=None)
            index = get_nested(paragraph, "v888", 0, "_", default=-1)

            if index != -1 and article_pid == pid:
                references[index] = XMLUtils.cleanup_mixed_citation_text(
                    get_nested(paragraph, "v704", 0, "_")
                )

        return references

    def get_output_file_path(original_file, output_folder=None):
        """Retorna o path completo para um arquivo de saída"""
        if output_folder is None:
            return original_file

        return os.path.join(output_folder, os.path.basename(original_file))

    def get_paragraphs_from_cache(file) -> list:
        """Retorna uma lista de paragráfos a partir de um arquivo JSON"""
        paragraphs = []

        with open(file, "r") as f:
            for line in f.readlines():
                paragraphs.append(json.loads(line))

        return paragraphs

    xmls = get_files_in_path(source, extension=".xml")

    with tqdm(total=len(xmls), disable=disable_bar) as pbar:
        for xml in xmls:
            try:
                package = SPS_Package(etree.parse(xml))

                if package.scielo_pid_v2 is None:
                    logger.error("Could not update file '%s' because its PID is unknown.", xml)
                    continue

                paragraph_file = f"{CACHE_DIR}/{package.scielo_pid_v2}.json"
                paragraphs = get_paragraphs_from_cache(paragraph_file)
                references = get_references_text_from_paragraphs(
                    paragraphs, pid=package.scielo_pid_v2
                )
                updated = package.update_mixed_citations(references, override=override)
                output_file = get_output_file_path(xml, output_folder)
                XMLUtils.objXML2file(output_file, package.xmltree, pretty=True)

                if len(updated) > 0:
                    logger.debug(
                        "Updated %0.3d references from '%s' file.", len(updated), xml
                    )

            except etree.XMLSyntaxError as e:
                logger.error(e)
            except FileNotFoundError as e:
                logger.error(
                    "Could not update file '%s' " "the exception '%s' occurred.", xml, e
                )
            pbar.update(1)

