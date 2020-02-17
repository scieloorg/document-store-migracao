import logging
import json
from typing import List
from datetime import datetime
from documentstore_migracao.utils import scielo_ids_generator
from xylose.scielodocument import Journal, Issue, Article

logger = logging.getLogger(__name__)


def date_to_datetime(date: str) -> datetime:
    """Transforma datas no formato ISO em objetos datetime"""
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")


def parse_date(date: str) -> str:
    """Traduz datas em formato simples ano-mes-dia, ano-mes para
    o formato iso utilizado durantr a persistência do Kernel"""

    _date = None

    try:
        _date = (
            datetime.strptime(date, "%Y-%m-%d").isoformat(timespec="microseconds") + "Z"
        )
    except ValueError:
        try:
            _date = (
                datetime.strptime(date, "%Y-%m").isoformat(timespec="microseconds")
                + "Z"
            )
        except ValueError:
            _date = (
                datetime.strptime(date, "%Y").isoformat(timespec="microseconds") + "Z"
            )

    return _date


def set_metadata(date: str, data: any) -> List[List]:
    """Retorna a estrutura básica de um `campo` de metadata
    no formato do Kernel"""

    return [[date, data]]


def journal_to_kernel(journal):
    """Transforma um objeto Journal (xylose) para o formato
    de dados equivalente ao persistido pelo Kernel em um banco
    mongodb"""

    # TODO: Virá algo do xylose para popular o campo de métricas?

    _id = journal.scielo_issn

    if not _id:
        raise ValueError("É preciso que o periódico possua um id")

    _creation_date = parse_date(journal.creation_date)
    _metadata = {}
    _bundle = {
        "_id": _id,
        "id": _id,
        "created": _creation_date,
        "updated": _creation_date,
        "items": [],
        "metadata": _metadata,
    }

    if journal.mission:
        _mission = [
            {"language": lang, "value": value}
            for lang, value in journal.mission.items()
        ]
        _metadata["mission"] = _mission

    if journal.title:
        _metadata["title"] = journal.title

    if journal.abbreviated_iso_title:
        _metadata["title_iso"] = journal.abbreviated_iso_title

    if journal.abbreviated_title:
        _metadata["short_title"] = journal.abbreviated_title

    _metadata["acronym"] = journal.acronym

    if journal.scielo_issn:
        _metadata["scielo_issn"] = journal.scielo_issn

    if journal.print_issn:
        _metadata["print_issn"] = journal.print_issn

    if journal.electronic_issn:
        _metadata["electronic_issn"] = journal.electronic_issn

    if journal.status_history:
        _metadata["status_history"] = []

        for status in journal.status_history:
            _status = {"status": status[1], "date": parse_date(status[0])}

            if status[2]:
                _status["reason"] = status[2]

            # TODO: Temos que verificar se as datas são autoritativas
            _metadata["status_history"].append(_status)

    if journal.subject_areas:
        _metadata["subject_areas"] = journal.subject_areas

    if journal.sponsors:
        _metadata["sponsors"] = [{"name": sponsor} for sponsor in journal.sponsors]

    if journal.wos_subject_areas:
        _metadata["subject_categories"] = journal.wos_subject_areas

    if journal.submission_url:
        _metadata["online_submission_url"] = journal.submission_url

    if journal.next_title:
        _metadata["next_journal"] = {"name": journal.next_title}

    if journal.previous_title:
        _metadata["previous_journal"] = {"name": journal.previous_title}

    _contact = {}
    if journal.editor_email:
        _contact["email"] = journal.editor_email

    if journal.editor_address:
        _contact["address"] = journal.editor_address

    if _contact:
        _metadata["contact"] = _contact

    if journal.publisher_name:
        institutions = []
        for name in journal.publisher_name:
            item = {"name": name}
            if journal.publisher_city:
                item["city"] = journal.publisher_city
            if journal.publisher_state:
                item["state"] = journal.publisher_state
            if journal.publisher_country:
                country_code, country_name = journal.publisher_country
                item["country_code"] = country_code
                item["country"] = country_name
            institutions.append(item)

        _metadata["institution_responsible_for"] = tuple(institutions)

    return _bundle


def get_journal_issn_in_issue(issue) -> str:
    """Retorna o ISSN ID de um periódico na
    perspectiva da issue"""
    return issue.data.get("issue").get("v35")[0]["_"]


def issue_to_kernel(issue):
    """Transforma um objeto Issue (xylose) para o formato
    de dados equivalente ao persistido pelo Kernel em um banco
    mongodb"""

    issn_id = issue.data["issue"]["v35"][0]["_"]
    _creation_date = parse_date(issue.publication_date)
    _metadata = {}
    _bundle = {
        "created": _creation_date,
        "updated": _creation_date,
        "items": [],
        "metadata": _metadata,
    }

    _year = str(date_to_datetime(_creation_date).year)
    _month = str(date_to_datetime(_creation_date).month)
    _metadata["publication_year"] = _year

    if issue.volume:
        _metadata["volume"] = issue.volume

    if issue.number:
        _metadata["number"] = issue.number

    _supplement = None
    if issue.type is "supplement":
        _supplement = "0"

        if issue.supplement_volume:
            _supplement = issue.supplement_volume
        elif issue.supplement_number:
            _supplement = issue.supplement_number

        _metadata["supplement"] = _supplement

    if issue.titles:
        _titles = [
            {"language": lang, "value": value} for lang, value in issue.titles.items()
        ]
        _metadata["titles"] = _titles

    publication_months = {}
    if issue.start_month and issue.end_month:
        publication_months["range"] = (int(issue.start_month), int(issue.end_month))
    elif _month:
        publication_months["month"] = int(_month)

    _metadata["publication_months"] = publication_months

    _id = scielo_ids_generator.issue_id(
        issn_id, _year, issue.volume, issue.number, _supplement
    )
    _bundle["_id"] = _id
    _bundle["id"] = _id

    return _bundle


def get_journal_issns_from_issue(issue: Issue) -> List[str]:
    """Busca por todos os issns de periódico disponíveis em uma
    issue. Os ISSNs podem estar nos dois campos v35 e v435 com
    ou sem repetição"""

    issns = [get_journal_issn_in_issue(issue)]

    if not "v435" in issue.data["issue"]:
        return issns

    issns.extend([issn["_"] for issn in issue.data["issue"]["v435"]])

    return list(set(issns))


def find_documents_bundles(journal: dict, issues: List[Issue]):
    """Busca o id de todos os fascículos associados ao periódico. Um id
    é encontrado quando pelo menos um ISSN relacionado ao fascículo também
    está presente no periódico.
    """

    issues_ids = []
    journal_issns = []
    journal_issn_fields = ["electronic_issn", "print_issn", "scielo_issn"]
    _metadata = journal["metadata"]

    for field in journal_issn_fields:
        try:
            journal_issns.append(_metadata[field])
        except (KeyError, IndexError):
            pass

    journal_issns = list(set(journal_issns))

    for issue in issues:
        issue_issns = get_journal_issns_from_issue(issue)
        has_matched_issns = list(
            filter(lambda issn: issn in journal_issns, issue_issns)
        )

        if has_matched_issns:
            issues_ids.append(issue_to_kernel(issue).get("id"))

    return issues_ids


def json_file_to_xylose_article(json_file_path):
    with open(json_file_path) as json_file:
        return Article(json.load(json_file))
