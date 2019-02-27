""" module to export journal data """

from xylose.scielodocument import Journal
from documentstore_migracao import config
from documentstore_migracao.utils import request


def ext_identifiers():

    journals_id = request.get(
        "%s/journal/identifiers/" % config.AM_URL_API,
        params={"collection": config.SCIELO_COLLECTION},
    ).json()

    return journals_id


def ext_journal(issn):

    journal = request.get(
        "%s/journal" % config.AM_URL_API,
        params={"collection": config.SCIELO_COLLECTION, "issn": issn},
    ).json()

    return Journal(journal[0])


def get_all_journal():

    journals = []

    journals_id = ext_identifiers()
    for d_journal in journals_id["objects"][2:]:
        journals.append(ext_journal(d_journal["code"]))

    return journals
