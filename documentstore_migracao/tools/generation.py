import os
import logging

from tqdm import tqdm
from lxml import etree
from packtools import HTMLGenerator, XML, catalogs
from documentstore_migracao.utils import files, xml
from documentstore_migracao import config

logger = logging.getLogger(__name__)


def article_html_generator(file_xml_path: str, dest_path: str) -> None:

    logger.debug("file: %s", file_xml_path)

    parsed_xml = XML(file_xml_path, no_network=False)
    html_generator = HTMLGenerator.parse(
        parsed_xml,
        valid_only=False,
        css="https://new.scielo.br/static/css/scielo-article.css",
        print_css="https://new.scielo.br/static/css/scielo-bundle-print.css",
        js="https://new.scielo.br/static/js/scielo-article-min.js",
    )

    for lang, trans_result in html_generator:
        fpath, fname = os.path.split(file_xml_path)
        fname, fext = fname.rsplit(".", 1)
        out_fname = ".".join([fname, lang, "html"])

        new_file_html_path = os.path.join(dest_path, out_fname)

        files.write_file(
            new_file_html_path,
            etree.tostring(
                trans_result,
                doctype=u"<!DOCTYPE html>",
                pretty_print=True,
                encoding="utf-8",
                method="html",
            ).decode("utf-8"),
        )


def article_ALL_html_generator(source_path: str, dest_path: str) -> None:

    logger.info("Iniciando Geração dos HTMLs")
    list_files_xmls = files.xml_files_list(source_path)
    for file_xml in tqdm(list_files_xmls):
        try:
            article_html_generator(os.path.join(source_path, file_xml), dest_path)
        except Exception as ex:
            logger.info("não foi possível gerar o html do Arquivo %s: %s", file_xml, ex)
