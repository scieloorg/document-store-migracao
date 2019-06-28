import logging
import os
from typing import List
import concurrent.futures
from tqdm import tqdm
from documentstore_migracao.export import article
from documentstore_migracao.utils import files
from documentstore_migracao import config


logger = logging.getLogger(__name__)


class PoisonPill:
    """Sinaliza para as threads que devem abortar a execução da rotina e 
    retornar imediatamente.
    """
    def __init__(self):
        self.poisoned = False


def get_and_write(pid, stage_path, poison_pill):
    if poison_pill.poisoned:
        return

    documents_pid = pid.strip()

    logger.debug("\t coletando dados do Documento '%s'", documents_pid)
    xml_article = article.ext_article_txt(documents_pid)

    if xml_article:
        file_path = os.path.join(config.get("SOURCE_PATH"), "%s.xml" % documents_pid)
        logger.debug("\t Salvando arquivo '%s'", file_path)
        files.write_file(file_path, xml_article)
        files.register_latest_stage(stage_path, documents_pid)


def extract_all_data(list_documents_pids: List[str]):
    """Extrai documentos XML a partir de uma lista de PIDS
    de entrada"""

    pids_to_extract, pids_extracteds, stage_path = files.fetch_stages_info(
        list_documents_pids, __name__
    )

    logger.info("Iniciando extração dos Documentos")
    count = 0
    poison_pill = PoisonPill()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=config.get("THREADPOOL_MAX_WORKERS")
    ) as executor:
        futures = {
            executor.submit(get_and_write, pid, stage_path, poison_pill): pid
            for pid in pids_to_extract
        }

        with tqdm(total=len(list_documents_pids), initial=len(pids_extracteds)) as pbar:
            try:
                for future in concurrent.futures.as_completed(futures):
                    pid = futures[future]
                    pbar.update(1)
                    try:
                        result = future.result()
                    except Exception as exc:
                        logger.info("%r gerou uma exceção: %s" % (pid, exc))
                    else:
                        count += 1

            except KeyboardInterrupt:
                logger.info(
                    "Finalizando as tarefas pendentes antes de encerrar."
                    " Isso poderá levar alguns segundos."
                )
                poison_pill.poisoned = True
                raise

    logger.info("\t Total de %s artigos", count)
