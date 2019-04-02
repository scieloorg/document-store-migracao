""" module to export issue data """
import logging
from xylose.scielodocument import Issue
from documentstore_migracao import config
from documentstore_migracao.utils import request, extract_isis

logger = logging.getLogger(__name__)

def ext_identifiers(issn_journal):
    issues_id = request.get(
        "%s/issue/identifiers/" % config.get("AM_URL_API"),
        params={"collection": config.get("SCIELO_COLLECTION"), "issn": issn_journal},
    ).json()


def ext_issue(code, **ext_params):

    issue = request.get(
        "%s/issue" % config.AM_URL_API,
        params={"collection": config.get("SCIELO_COLLECTION"), "code": code},
    ).json()
    obj_issue = Issue(issue)


def extract_issues_from_isis():
    """Inicia a extração de dados a partir de uma base ISIS
    """
    logger.info("Iniciando extração de issues")
    extract_isis.run(base="issue")