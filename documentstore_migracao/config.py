import os

SCIELO_COLLECTION = "spa"
AM_URL_API = "http://articlemeta.scielo.org/api/v1"

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

SOURCE_PATH = os.path.join(BASE_PATH, "xml/source")
SUCCESS_PROCESSING_PATH = os.path.join(BASE_PATH, "xml/sucess")

LOGGER_PATH = os.path.join(BASE_PATH, "")
