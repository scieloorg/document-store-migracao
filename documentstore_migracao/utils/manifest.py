from lxml import etree
from .xylose_converter import parse_date

from documentstore_migracao.export.sps_package import SPS_Package


def get_document_manifest(
    document: etree.ElementTree, document_url: str, assets: list
) -> dict:
    """Cria um manifesto no formato do Kernel a partir de um
    documento xml"""

    obj_sps = SPS_Package(document)
    _id = obj_sps.scielo_id
    date = obj_sps.document_pubdate

    if not _id:
        raise ValueError("Document requires an scielo-id") from None

    if not date:
        raise ValueError("A creation date is required") from None

    _creation_date = parse_date(
        "-".join([date_part for date_part in date if date_part])
    )

    _version = {"data": document_url, "assets": {}, "timestamp": _creation_date}
    _document = {"id": _id, "versions": [_version]}

    for asset in assets:
        _version["assets"][asset.get("asset_id")] = [
            [_creation_date, asset.get("asset_url")]
        ]

    return _document


def get_document_bundle_manifest(bundle_id: str, date: str) -> dict:
    return {
        "_id" : bundle_id,
        "created" : date,
        "updated" : date,
        "items" : [],
        "metadata" : {},
        "id" : bundle_id,
    }