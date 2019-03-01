import logging
import os
from documentstore_migracao.export import journal, article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def extrated_journal_data(obj_journal):

    logger.info("\t coletando dados do periodico '%s'", obj_journal.title)
    list_articles = article.get_all_articles_notXML(obj_journal.scielo_issn)
    for name_article, xml_article in list_articles:

        logger.info("\t Salvando arquivo '%s'", name_article)
        files.write_file(
            os.path.join(config.SOURCE_PATH, "%s.xml" % name_article), xml_article
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
