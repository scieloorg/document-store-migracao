import logging
import json
from typing import List


from documentstore_migracao.utils import files

logger = logging.getLogger(__name__)


def read_json_file(file_path: str) -> List[dict]:
    """Ler um arquivo JSON e retorna o resultado
    em formato de estruturas Python"""

    return json.loads(files.read_file(file_path))
