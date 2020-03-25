import gzip
import logging
import concurrent.futures

from documentstore.domain import utcnow
from documentstore.services import DocumentRenditions


def _add_change(session, instance, entity, id=None):
    session.changes.add(
        {
            "timestamp": utcnow(),
            "entity": entity,
            "id": id or instance.id(),
            "content_gz": gzip.compress(instance.data_bytes()),
            "content_type": instance.data_type,
        }
    )


def add_document(session, document):
    session.documents.add(document)
    _add_change(session, document, "Document")


def add_journal(session, journal):
    session.journals.add(journal)
    _add_change(session, journal, "Journal")


def update_journal(session, journal):
    session.journals.update(journal)
    _add_change(session, journal, "Journal")


def add_bundle(session, bundle):
    session.documents_bundles.add(bundle)
    _add_change(session, bundle, "DocumentsBundle")


def update_bundle(session, bundle):
    session.documents_bundles.update(bundle)
    _add_change(session, bundle, "DocumentsBundle")


def add_renditions(session, document):
    _add_change(
        session, DocumentRenditions(document), "DocumentRendition", document.id()
    )


class PoisonPill:
    """Sinaliza para as threads que devem abortar a execução da rotina e 
    retornar imediatamente.
    """

    def __init__(self):
        self.poisoned = False


def DoJobsConcurrently(
    func: callable,
    jobs: list = [],
    executor: concurrent.futures.Executor = concurrent.futures.ThreadPoolExecutor,
    max_workers: int = 1,
    success_callback: callable = (lambda *k: k),
    exception_callback: callable = (lambda *k: k),
    update_bar: callable = (lambda *k: k),
):
    """Executa uma lista de tarefas concorrentemente.

    Params:
    func (callable): função a ser executada concorrentemente.
    jobs (list[Dict]): Lista com argumentos utilizados pela função a ser executada.
    executor (concurrent.futures.Executor): Classe responsável por executar a
        lista de jobs concorrentemente.
    max_workers (integer)
    success_callback (callable): Função executada ao finalizar a execução de cada job.
    exception_callback (callable): Função executada durante o tratamento de exceções.
    update_bar (callable): Função responsável por atualizar a posição da barra de status.

    Returns:
        None
    """
    poison_pill = PoisonPill()

    with executor(max_workers=max_workers) as _executor:
        futures = {
            _executor.submit(func, **job, poison_pill=poison_pill): job for job in jobs
        }

        try:
            for future in concurrent.futures.as_completed(futures):
                job = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    exception_callback(exc, job)
                else:
                    success_callback(result)
                finally:
                    update_bar()
        except KeyboardInterrupt:
            logging.info(
                "Finalizando as tarefas pendentes antes de encerrar."
                " Isso poderá levar alguns segundos."
            )
            poison_pill.poisoned = True
            raise


def get_nested(node, *path, default=""):
    try:
        for p in path:
            node = node[p]
    except (IndexError, KeyError):
        return default
    return node


__all__ = [
    "add_document",
    "add_journal",
    "update_journal",
    "add_bundle",
    "update_bundle",
    "add_renditions",
    "PoisonPill",
    "DoJobsConcurrently",
    "get_nested",
]
