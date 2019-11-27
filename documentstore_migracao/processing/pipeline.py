import logging
import sys
import os
import json
import gzip
import re
from typing import List, Generator

from lxml import etree

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
)
from documentstore_migracao.processing import reading, conversion
from documentstore_migracao.utils.xylose_converter import (
    issue_to_kernel,
    parse_date,
    date_to_datetime,
)


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
    source: str, mst_source: str, output_folder: str = None, override: bool = False
):
    """Atualiza os elementos de ``mixed-citations`` em um ou mais XMLs.

    É possível atualizar um ou mais XML a partir de um path `source`. A fonte
    de parágrafos pode ser um arquivo MST ou um diretório no padrão SciELO Brasil.

    Se a fonte MST for um diretório no padrão SciELO os arquivos MST serão
    localizados a partir do PID do XML processado
    (PID: S0301-80591999000100002 -> 0301-8059/1999/0001/00002.mst).

    O resultado da atualização pode ser salvo no próprio arquivo XML ou em
    outro arquivo XML em um diretório diferente utilizando o parâmetro
    ``output_folder``."""
    if not os.path.exists(source):
        raise FileNotFoundError("Source path '%s' does not exists" % source)
    elif not os.path.exists(mst_source):
        raise FileNotFoundError("MST path '%s' does not exists" % mst_source)
    elif output_folder is not None and not os.path.exists(output_folder):
        raise FileNotFoundError("Output folder '%s' does not exists" % output_folder)

    def get_nested(node, *path, default=""):
        try:
            for p in path:
                node = node[p]
        except (IndexError, KeyError):
            return default
        return node

    def get_xml_files_path(path: str) -> List[str]:
        """Retorna uma lista com os XMLs encontrados em um determinado path"""
        if os.path.isfile(path):
            return [path]

        xmls = []
        for root, _, files in os.walk(path):
            xmls.extend(
                [
                    os.path.realpath(os.path.join(root, file))
                    for file in files
                    if ".xml" in file
                ]
            )

        return xmls

    def translate_pid_to_mst_path(pid: str) -> str:
        """Converte o PID de um artigo na estrutura de diretório de parágrafos
        utilizada pela SciELO BR.

        Exemplo:
        PID: S0301-80591999000100002 -> 0301-8059/1999/0001/00002.mst"""
        result = re.split(r"S?([\w-]{9})(.{4})(.{4})(.{5})", pid)
        result = "/".join(result[1:-1]) + ".mst"
        return result

    def get_paragraphs_from_mst(mst_source: str, pid: str = None) -> dict:
        """Ler um arquivo MST e retorna seu conteúdo em formato JSON.

        Se o parâmetro `mst_source` for um arquivo MST, o seu conteúdo será lido
        e transformado em JSON. O parâmetro `pid` será utilizado para inferir
        o path da base MST se o `mst_source` for um diretório.

        O caminho inferido a partir do `pid` segue a regra utilizada pela SciELO
        para segmentar a base Artigo e seus parágrafos (issn/year/order/order_in_issue).
        """
        if os.path.isdir(mst_source) and pid is None:
            raise ValueError("PID param is required if mst source is a directory")
        elif os.path.isdir(mst_source):
            mst_source = os.path.join(mst_source, translate_pid_to_mst_path(pid))

        if not os.path.exists(mst_source):
            raise FileNotFoundError("File '%s' does not exists" % mst_source)

        return json.loads(run_isis2json(mst_source).stdout.decode())

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

        return os.path.join(output_folder, os.path.basename(xml))

    if os.path.isfile(mst_source):
        paragraphs = get_paragraphs_from_mst(mst_source)

    for xml in get_xml_files_path(source):
        try:
            package = SPS_Package(etree.parse(xml))

            if os.path.isdir(mst_source):
                paragraphs = get_paragraphs_from_mst(
                    mst_source, pid=package.scielo_pid_v2
                )

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
