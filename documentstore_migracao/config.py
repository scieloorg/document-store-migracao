import os

SCIELO_COLLECTION = "spa"
AM_URL_API = "http://articlemeta.scielo.org/api/v1"

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

SOURCE_PATH = os.path.join(BASE_PATH, "xml/source")
CONVERSION_PATH = os.path.join(BASE_PATH, "xml/conversion")
SUCCESS_PROCESSING_PATH = os.path.join(BASE_PATH, "xml/sucess")
LOGGER_PATH = os.path.join(BASE_PATH, "")

INITIAL_PATH = [LOGGER_PATH, SOURCE_PATH, SUCCESS_PROCESSING_PATH, CONVERSION_PATH]
