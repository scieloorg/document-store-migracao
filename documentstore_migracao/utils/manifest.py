from lxml import etree
from .xylose_converter import parse_date

from documentstore_migracao.utils import xml


def get_document_bundle_manifest(
    document: etree.ElementTree, document_url: str, assets: list
) -> dict:
    """Cria um manifesto no formato do Kernel a partir de um
    documento xml"""

    try:
        _id = document.find(".//article-id[@pub-id-type='scielo-id']").text
    except AttributeError:
        raise ValueError("Document requires an scielo-id") from None

    date = xml.get_document_publication_date_for_migration(document)

    if not date:
        raise ValueError("A creation date is required") from None

    _creation_date = parse_date(date)

    _version = {"data": document_url, "assets": {}, "timestamp": _creation_date}
    _document = {"id": _id, "versions": [_version]}

    for asset in assets:
        _version["assets"][asset.get("asset_id")] = [
            [_creation_date, asset.get("asset_url")]
        ]

    return _document
