""" module to export article data """

import requests

from documentstore_migracao import config


def ext_identifiers(issn_journal):
    articles_id = requests.get(
        "%s/article/identifiers/" % config.AM_URL_API,
        params={"collection": config.SCIELO_COLLECTION, "issn": issn_journal},
    ).json()
    return articles_id


def ext_article(code, **ext_params):
    params = ext_params
    params.update({"collection": config.SCIELO_COLLECTION, "code": code})

    article = requests.get("%s/article" % config.AM_URL_API, params=params)
    return article


def ext_article_json(code, **ext_params):
    article = ext_article(code).json()
    return article


def ext_article_txt(code, **ext_params):
    article = ext_article(code, body=True, format="xmlrsps").text
    return article


def get_all_articles_notXML(issn):

    articles = []
    articles_id = ext_identifiers(issn)
    for d_articles in articles_id["objects"]:
        article = ext_article_json(d_articles["code"])
        if article["version"] != "xml":

            articles.append((d_articles["code"], ext_article_txt(d_articles["code"])))

    return articles
