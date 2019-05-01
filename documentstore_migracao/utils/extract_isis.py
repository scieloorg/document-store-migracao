import os
import logging
import shlex
import subprocess
from documentstore_migracao import config, exceptions

logger = logging.getLogger(__name__)


ISIS2JSON_PATH = "%s/documentstore_migracao/utils/isis2json/isis2json.py" % (
    config.BASE_PATH
)


def create_output_dir(path):
    output_dir = "/".join(path.split("/")[:-1])

    if not os.path.exists(output_dir):
        logger.debug("Creating folder: %s", output_dir)
        os.makedirs(output_dir)


def run(path: str, output_file: str):
    """Roda um subprocesso com o isis2json de target para extrair dados
    de uma base ISIS em formato MST. O resultado da extração
    é armazenado em formato JSON em arquivo determinado pelo
    parâmetro output_file.
    """

    command = "java -cp %s org.python.util.jython %s -t 3 -p 'v' -o %s %s" % (
        config.get("CLASSPATH"),
        ISIS2JSON_PATH,
        output_file,
        path,
    )

    try:
        logger.debug("Extracting database file: %s" % path)
        subprocess.run(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        logger.debug("Writing extracted result as JSON file in: %s" % output_file)
    except Exception as exc:
        raise exceptions.ExtractError(str(exc)) from None
