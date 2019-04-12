import logging
import sys
import os
from documentstore_migracao import exceptions, config
from documentstore_migracao.utils import extract_isis
from documentstore_migracao.processing import reading, conversion
from documentstore.interfaces import Session
from documentstore.domain import utcnow
from documentstore.exceptions import AlreadyExists


logger = logging.getLogger(__name__)


class ManifestDomainAdapter:
    """Complementa o manifesto produzido na fase de transformação
    para o formato exigido pelos adapters do Kernel para
    realizar a inserção no MongoDB"""

    def __init__(self, manifest):
        self._manifest = manifest

    def id(self) -> str:
        return self.manifest["id"]

    @property
    def manifest(self) -> dict:
        return self._manifest


def import_journals(json_file: str, session: Session):
    """Fachada com passo a passo de processamento e carga de periódicos
    em formato JSON para a base Kernel"""

    try:
        journals_as_json = reading.read_json_file(json_file)
        journals_as_kernel = conversion.conversion_journals_to_kernel(
            journals=journals_as_json
        )

        for journal in journals_as_kernel:
            manifest = ManifestDomainAdapter(manifest=journal)

            try:
                session.journals.add(data=manifest)
                session.changes.add(
                    {"timestamp": utcnow(), "entity": "Journal", "id": manifest.id()}
                )
            except AlreadyExists as exc:
                logger.info(str(exc))
    except (FileNotFoundError, ValueError) as exc:
        logger.debug(str(exc))
