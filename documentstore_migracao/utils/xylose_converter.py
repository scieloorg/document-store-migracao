import logging
from typing import List
from datetime import datetime
from xylose.scielodocument import Journal

logger = logging.getLogger(__name__)


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
                datetime.strptime(date, "%Y-%m").isoformat(timespec="microseconds") + "Z"
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

    _id = journal.any_issn()

    if not _id:
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
        _metadata["mission"] = set_metadata(_creation_date, _mission)

    if journal.title:
        _metadata["title"] = set_metadata(_creation_date, journal.title)

    if journal.abbreviated_iso_title:
        _metadata["title_iso"] = set_metadata(
            _creation_date, journal.abbreviated_iso_title
        )

    if journal.abbreviated_title:
        _metadata["short_title"] = set_metadata(
            _creation_date, journal.abbreviated_title
        )

    _metadata["acronym"] = set_metadata(_creation_date, journal.acronym)

    if journal.scielo_issn:
        _metadata["scielo_issn"] = set_metadata(_creation_date, journal.scielo_issn)

    if journal.print_issn:
        _metadata["print_issn"] = set_metadata(_creation_date, journal.print_issn)

    if journal.electronic_issn:
        _metadata["electronic_issn"] = set_metadata(
            _creation_date, journal.electronic_issn
        )

    if journal.status_history:
        _metadata["status"] = []

        for status in journal.status_history:
            _status = {"status": status[1]}

            if status[2]:
                _status["reason"] = status[2]

            # TODO: Temos que verificar se as datas são autoritativas
            _metadata["status"].append([parse_date(status[0]), _status])

    if journal.subject_areas:
        _metadata["subject_areas"] = set_metadata(
            _creation_date, [area.upper() for area in journal.subject_areas]
        )

    if journal.sponsors:
        _sponsors = [{"name": sponsor} for sponsor in journal.sponsors]
        _metadata["sponsors"] = set_metadata(_creation_date, _sponsors)

    if journal.wos_subject_areas:
        _metadata["subject_categories"] = set_metadata(
            _creation_date, journal.wos_subject_areas
        )

    if journal.submission_url:
        _metadata["online_submission_url"] = set_metadata(
            _creation_date, journal.submission_url
        )

    if journal.next_title:
        _next_journal = {"name": journal.next_title}
        _metadata["next_journal"] = set_metadata(_creation_date, _next_journal)

    if journal.previous_title:
        _previous_journal = {"name": journal.previous_title}
        _metadata["previous_journal"] = set_metadata(_creation_date, _previous_journal)

    _contact = {}
    if journal.editor_email:
        _contact["email"] = journal.editor_email

    if journal.editor_address:
        _contact["address"] = journal.editor_address

    if _contact:
        _metadata["contact"] = set_metadata(_creation_date, _contact)

    return _bundle
