""" module to export issue data """

from xylose.scielodocument import Issue
from documentstore_migracao import config
from documentstore_migracao.utils import request


def ext_identifiers(issn_journal):
    issues_id = request.get(
        "%s/issue/identifiers/" % config.AM_URL_API,
        params={"collection": config.SCIELO_COLLECTION, "issn": issn_journal},
    ).json()


def ext_issue(code, **ext_params):

    issue = request.get(
        "%s/issue" % config.AM_URL_API,
        params={"collection": config.SCIELO_COLLECTION, "code": code},
    ).json()
    obj_issue = Issue(issue)
