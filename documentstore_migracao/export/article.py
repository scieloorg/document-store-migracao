""" module to export article data """
import logging
from documentstore_migracao import config
from documentstore_migracao.utils import request

logger = logging.getLogger(__name__)


def ext_identifiers(issn_journal):
    articles_id = request.get(
        "%s/article/identifiers/" % config.get("AM_URL_API"),
        params={"collection": config.get("SCIELO_COLLECTION"), "issn": issn_journal},
    ).json()
    return articles_id


def ext_article(code, **ext_params):
    params = ext_params
    params.update({"collection": config.get("SCIELO_COLLECTION"), "code": code})

    article = request.get("%s/article" % config.get("AM_URL_API"), params=params)
    return article


def ext_article_json(code, **ext_params):
    article = ext_article(code, **ext_params).json()
    return article


def ext_article_txt(code, **ext_params):
    logger.info("\t Arquivo XML '%s' extraido", code)
    article = ext_article(code, body="true", format="xmlrsps", **ext_params).text
    return article


def get_all_articles_notXML(issn):
    articles = []
    articles_id = ext_identifiers(issn)
    for d_articles in articles_id["objects"]:
        article = ext_article_json(d_articles["code"])
        if article["version"] != "xml":
            logger.info("\t Arquivo XML '%s' extraido", d_articles["code"])
            articles.append((d_articles["code"], ext_article_txt(d_articles["code"])))

    return articles


def get_article_identifiers(issn):
    identifiers = ext_identifiers(issn)
    if identifiers:
        return [document["code"] for document in identifiers["objects"]]


def get_not_xml_article(identifier):
    article = ext_article_json(identifier)
    if article["version"] != "xml":
        return ext_article_txt(identifier)
