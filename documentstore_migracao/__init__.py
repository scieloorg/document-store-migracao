import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from documentstore_migracao.utils import logger, files
from documentstore_migracao import config


# SET LOGGER
logger.configure_logger()

# SET FOLDER PROCESSOR
files.setup_processing_folder()
