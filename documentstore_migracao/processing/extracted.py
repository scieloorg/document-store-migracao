import logging
import os
from typing import List
import concurrent.futures
from tqdm import tqdm
from documentstore_migracao.export import article
from documentstore_migracao.utils import files
from documentstore_migracao import config
from documentstore_migracao.utils import DoJobsConcurrently, PoisonPill


logger = logging.getLogger(__name__)


def get_and_write(pid, stage_path, poison_pill):

    def save_file(stage_path, file_path, documents_pid, article_content):
        logger.debug("\t Salvando arquivo '%s'", file_path)
        files.write_file(file_path, article_content)
        files.register_latest_stage(stage_path, documents_pid)

    if poison_pill.poisoned:
        return

    documents_pid = pid.strip()

    logger.debug("\t coletando dados do Documento '%s'", documents_pid)
    xml_article = article.ext_article_txt(documents_pid)
    if xml_article:
        save_file(
            stage_path,
            os.path.join(config.get("SOURCE_PATH"), "%s.xml" % documents_pid),
            documents_pid,
            xml_article,
        )

    json_article = article.ext_article_json(documents_pid)
    if json_article:
        save_file(
            stage_path,
            os.path.join(config.get("SOURCE_PATH"), "%s.json" % documents_pid),
            documents_pid,
            json_article,
        )


def extract_all_data(list_documents_pids: List[str]):
    """Extrai documentos XML a partir de uma lista de PIDS
    de entrada"""

    pids_to_extract, pids_extracteds, stage_path = files.fetch_stages_info(
        list_documents_pids, __name__
    )

    jobs = [{"pid": pid, "stage_path": stage_path} for pid in pids_to_extract]

    with tqdm(total=len(list_documents_pids)) as pbar:

        def update_bar(pbar=pbar):
            pbar.update(1)

        DoJobsConcurrently(
            get_and_write,
            jobs=jobs,
            max_workers=config.get("THREADPOOL_MAX_WORKERS"),
            update_bar=update_bar,
        )
