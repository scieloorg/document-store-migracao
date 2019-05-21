import logging
import os
from typing import List
from tqdm import tqdm
from documentstore_migracao.export import article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


def extract_all_data(list_documents_pids: List[str]):
    """Extrai documentos XML a partir de uma lista de PIDS
    de entrada"""

    pids_to_extract, pids_extracteds, stage_path = files.fetch_stages_info(
        list_documents_pids, __name__
    )

    logger.info("Iniciando extração dos Documentos")
    count = 0

    try:
        for documents_pid in tqdm(
            iterable=pids_to_extract,
            initial=len(pids_extracteds),
            total=len(list_documents_pids),
        ):
            documents_pid = documents_pid.strip()

            logger.debug("\t coletando dados do Documento '%s'", documents_pid)
            xml_article = article.ext_article_txt(documents_pid)
            if xml_article:
                count += 1

                file_path = os.path.join(
                    config.get("SOURCE_PATH"), "%s.xml" % documents_pid
                )
                logger.debug("\t Salvando arquivo '%s'", file_path)
                files.write_file(file_path, xml_article)
                files.register_latest_stage(stage_path, documents_pid)
    except KeyboardInterrupt:
        ...

    logger.info("\t Total de %s artigos", count)
