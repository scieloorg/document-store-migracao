import os

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

_default = dict(
    SCIELO_COLLECTION="spa",
    AM_URL_API="http://articlemeta.scielo.org/api/v1",
    SOURCE_PATH=os.path.join(BASE_PATH, "xml/source"),
    CONVERSION_PATH=os.path.join(BASE_PATH, "xml/conversion"),
    SUCCESS_PROCESSING_PATH=os.path.join(BASE_PATH, "xml/sucess"),
    LOGGER_PATH=os.path.join(BASE_PATH, ""),
)

INITIAL_PATH = [
    _default["LOGGER_PATH"],
    _default["SOURCE_PATH"],
    _default["SUCCESS_PROCESSING_PATH"],
    _default["CONVERSION_PATH"],
]


def get(config):
    return os.environ.get(config, _default.get(config, ""))
