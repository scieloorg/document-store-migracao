import os
from packtools.catalogs import XML_CATALOG

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

_default = dict(
    SCIELO_COLLECTION="spa",
    AM_URL_API="http://articlemeta.scielo.org/api/v1",
    SOURCE_PATH=os.path.join(BASE_PATH, "xml/source"),
    CONVERSION_PATH=os.path.join(BASE_PATH, "xml/conversion"),
    SUCCESS_PROCESSING_PATH=os.path.join(BASE_PATH, "xml/success"),
    GENERATOR_PATH=os.path.join(BASE_PATH, "xml/html"),
    LOGGER_PATH=os.path.join(BASE_PATH, ""),
)

INITIAL_PATH = [
    _default["LOGGER_PATH"],
    _default["SOURCE_PATH"],
    _default["SUCCESS_PROCESSING_PATH"],
    _default["CONVERSION_PATH"],
    _default["GENERATOR_PATH"],
]

DOC_TYPE_XML = """<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "JATS-journalpublishing1.dtd">"""

os.environ["XML_CATALOG_FILES"] = XML_CATALOG


def get(config):
    return os.environ.get(config, _default.get(config, ""))
