""" module to export article data """
import logging
from articlemeta.client import RestfulClient
from documentstore_migracao import config
from documentstore_migracao.utils import request

logger = logging.getLogger(__name__)
client = RestfulClient()


def ext_identifiers(issn_journal):
    articles_id = request.get(
        "%s/article/identifiers/" % config.get("AM_URL_API"),
        params={"collection": config.get("SCIELO_COLLECTION"), "issn": issn_journal},
    ).json()
    return articles_id


def get_articles(issn_journal):
    return client.documents(
        collection=config.get("SCIELO_COLLECTION"), issn=issn_journal
    )


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
    articles_id = get_articles(issn)
    for article in articles_id:
        if article.data["version"] != "xml":
            logger.info("\t Arquivo XML '%s' extraido", article.data["code"])
            articles.append(
                (article.data["code"], ext_article_txt(article.data["code"]))
            )

    return articles


def get_not_xml_article(article):
    if article.data["version"] != "xml":
        return ext_article_txt(article.data["code"])
