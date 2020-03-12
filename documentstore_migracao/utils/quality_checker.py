import logging
import string
from typing import IO, List

import requests
from tqdm import tqdm

from documentstore_migracao import config
from documentstore_migracao.utils import DoJobsConcurrently

logger = logging.getLogger(__name__)


def check_documents_availability_in_website(
    pids: List[str], target_string: str, output: IO = None
) -> None:

    """ Dada uma lista de pids, esta função verifica no site informado quais
    pids não estão disponíveis.
    
    Params:
        pids (List[str]): Lista de pids para verificar.
        target_string (str): Endereço da página de artigo no site algo.
        output (IO): Arquivo onde as URLs não disponíveis serão registradas.

    Return:
        None
    """

    template = string.Template(target_string)

    if "$id" not in target_string:
        return logger.error(
            "The target string must contain a $id variable. If you are facing"
            "troubles try to scape the variable e.g '\$id'."
        )

    def access_website_and_report(url, output, poison_pill):
        """Acessa uma URL e reporta o seu status de resposta"""

        if poison_pill.poisoned:
            return

        response = requests.head(url)

        if response.status_code not in (200, 301, 302):
            logger.error(
                "The URL '%s' is not available. Returned the status code '%s'.",
                url,
                response.status_code,
            )

            if output is not None:
                try:
                    output.write(url + "\n")
                except IOError as exc:
                    logger.error(
                        "Cannot write in the file. The exception '%s' was raided ", exc
                    )

    jobs = [
        {"url": template.substitute({"id": pid.strip()}), "output": output}
        for pid in pids
    ]

    with tqdm(total=len(jobs)) as pbar:

        def update_bar(pbar=pbar):
            pbar.update(1)

        def exception_callback(exception, job, logger=logger, output=output):
            logger.error(
                "Could not check availability for URL '%s'. The following exception "
                "was raised: '%s'.",
                job["url"],
                exception,
            )

            logger.exception(exception)

        DoJobsConcurrently(
            access_website_and_report,
            jobs,
            max_workers=int(config.get("THREADPOOL_MAX_WORKERS")),
            exception_callback=exception_callback,
            update_bar=update_bar,
        )
