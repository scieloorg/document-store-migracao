import logging
import os
from documentstore_migracao.export import journal, article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def extrated_journal_data(obj_journal):
    count = 0
    logger.info("\t coletando dados do periodico '%s'", obj_journal.title)

    articles = article.get_articles(obj_journal.scielo_issn)
    for _article in articles:
        xml_article = article.get_not_xml_article(_article)
        if xml_article:
            count += 1

            file_path = os.path.join(
                config.get("SOURCE_PATH"), "%s.xml" % _article.data["code"]
            )
            logger.info("\t Salvando arquivo '%s'", file_path)
            files.write_file(file_path, xml_article)

    logger.info("\t Total de %s artigos", count)


def extrated_selected_journal(issn):

    logger.info("Iniciando extração do journal %s" % issn)

    obj_journal = journal.ext_journal(issn)
    extrated_journal_data(obj_journal)


def extrated_all_data():

    logger.info("Iniciando extração")
    list_journais = journal.get_journals()
    for obj_journal in list_journais:

        extrated_journal_data(obj_journal)
