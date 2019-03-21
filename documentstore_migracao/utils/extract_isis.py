import logging
import shlex
import subprocess
from documentstore_migracao import config, exceptions

logger = logging.getLogger(__name__)

ISIS2JSON_PATH = "%s/documentstore_migracao/utils/isis2json/isis2json.py" % (
    config.BASE_PATH
)


def run(base, base_format="mst"):
    """Roda um subprocesso com o isis2json de target para extrair dados
    de uma base ISIS em formato MST ou ISO. O resultado da extração
    é armazenado em formato JSON em uma pasta determinada pela variável
    de ambiente `SOURCE_PATH`.
    """
    BASE_FILE = "%s/%s/%s.%s" % (config.get("ISIS_BASE_PATH"), base, base, base_format)
    OUTPUT_FILE = "%s/%s.json" % (config.get("SOURCE_PATH"), base)

    if config.get("ISIS_FILE_PATH"):
        BASE_FILE = config.get("ISIS_FILE_PATH")

    command = "jython %s -t 3 -p 'v' -o %s %s" % (
        ISIS2JSON_PATH,
        OUTPUT_FILE,
        BASE_FILE,
    )

    try:
        logger.info("Extraindo arquivo %s" % BASE_FILE)
        subprocess.run(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        logger.info("Salvando arquivo %s" % OUTPUT_FILE)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise exceptions.ExtractError(str(exc))
    except (FileNotFoundError, IOError) as exc:
        raise exceptions.ExtractError(str(exc))
