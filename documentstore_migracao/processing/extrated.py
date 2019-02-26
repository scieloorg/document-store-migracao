import logging
import os
from documentstore_migracao.export import journal, article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def extrated_all_data():

    logger.info("Iniciando extração")
    list_journais = journal.get_all_journal()
    for obj_journal in list_journais:

        logger.info("\t colotando dados do periodico %s", obj_journal.title)
        list_articles = article.get_all_articles_notXML(obj_journal.scielo_issn)
        for name_article, xml_article in list_articles:

            logger.info("\t Salvando arquivo %s", name_article)
            files.write_file(
                os.path.join(config.SOURCE_PATH, name_article), xml_article
            )


def extrated_jornal_data(issn):

    obj_journal = journal.ext_journal(issn)

    logger.info("\t colotando dados do periodico %s", obj_journal.title)
    list_articles = article.get_all_articles_notXML(obj_journal.scielo_issn)
    logger.info("\t Total de %s artigos", len(list_articles))
    for name_article, xml_article in list_articles:

        logger.info("\t Salvando arquivo %s", name_article)
        files.write_file(
            os.path.join(config.SOURCE_PATH, "%s.xml" % name_article), xml_article
        )

