""" module to export journal data """
import logging
from xylose.scielodocument import Journal
from articlemeta.client import RestfulClient

from documentstore_migracao import config
from documentstore_migracao.utils import request, extract_isis

logger = logging.getLogger(__name__)


def ext_identifiers():

    journals_id = request.get(
        "%s/journal/identifiers/" % config.get("AM_URL_API"),
        params={"collection": config.get("SCIELO_COLLECTION")},
    ).json()
    return journals_id


def ext_journal(issn):

    journal = request.get(
        "%s/journal" % config.get("AM_URL_API"),
        params={"collection": config.get("SCIELO_COLLECTION"), "issn": issn},
    ).json()
    if journal:
        return Journal(journal[0])
    else:
        raise Exception(
            "Journal nao encontrado: %s: %s" % (config.get("SCIELO_COLLECTION"), issn)
        )


def get_all_journal():

    journals = []
    journals_id = ext_identifiers()
    for d_journal in journals_id["objects"][2:]:
        journals.append(ext_journal(d_journal["code"]))

    return journals


def get_journals():

    cl = RestfulClient()
    return cl.journals(collection=config.get("SCIELO_COLLECTION"))
