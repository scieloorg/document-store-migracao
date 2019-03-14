import logging
import os
from documentstore_migracao.export import journal, article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def extrated_journal_data(obj_journal):
    list_articles = []
    logger.info("\t coletando dados do periodico '%s'", obj_journal.title)
    identifiers = article.get_article_identifiers(obj_journal.scielo_issn)
    for identifier in identifiers:
        name_article = identifier
        xml_article = article.get_not_xml_article(identifier)
        if xml_article:
            list_articles.append(name_article)
            logger.info("\t Salvando arquivo '%s'", name_article)
            file_path = os.path.join(config.get("SOURCE_PATH"), "%s.xml" % name_article)
            logger.info("\t Salvando arquivo '%s'", file_path)
            files.write_file(
                file_path,
                xml_article,
            )
    logger.info("\t Total de %s artigos", len(list_articles))


def extrated_selected_journal(issn):

    logger.info("Iniciando extração do journal %s" % issn)

    obj_journal = journal.ext_journal(issn)
    extrated_journal_data(obj_journal)


def extrated_all_data():

    logger.info("Iniciando extração")
    list_journais = journal.get_all_journal()
    for obj_journal in list_journais:

        extrated_journal_data(obj_journal)
