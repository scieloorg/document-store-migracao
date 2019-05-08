import logging
import os
from typing import List
from tqdm import tqdm
from documentstore_migracao.export import article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def extract_all_data(list_documents_pids: List):

    logger.info("Iniciando extração dos Documentos")
    for documents_pid in tqdm(list_documents_pids):
        count = 0
        logger.debug("\t coletando dados do Documento '%s'", documents_pid)

        xml_article = article.ext_article_txt(documents_pid)
        if xml_article:
            count += 1

            file_path = os.path.join(
                config.get("SOURCE_PATH"), "%s.xml" % documents_pid
            )
            logger.debug("\t Salvando arquivo '%s'", file_path)
            files.write_file(file_path, xml_article)

    logger.info("\t Total de %s artigos", count)
