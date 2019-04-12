import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from documentstore_migracao.utils import logger, files
from documentstore_migracao import config
from documentstore import adapters


# SET LOGGER
logger.configure_logger()

# SET FOLDER PROCESSOR
files.setup_processing_folder()

# SET DATABASE CONNECTION
mongo = adapters.MongoDB(
    uri=config.get("DATABASE_URI"), dbname=config.get("DATABASE_NAME")
)

Session = adapters.Session.partial(mongo)
session = Session()
