import os
from packtools.catalogs import XML_CATALOG

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

"""
SOURCE_PATH:
    arquivos XML baixados do AM (body HTML)
PROCESSED_SOURCE_PATH:
    arquivos XML baixados do AM, mas que após convertidos para SPS e
    validados sem erro, são movidos de SOURCE_PATH para PROCESSED_SOURCE_PATH
CONVERSION_PATH:
    arquivos XML resultantes da conversão de
    "XML do AM" (SOURCE_PATH) para "XML SPS" (CONVERSION_PATH)
VALID_XML_PATH:
    arquivos "XML SPS" sem erros
XML_ERRORS_PATH:
    arquivos .err cujo conteúdo é XML + mensagens de erro
SPS_PKG_PATH:
    pacotes de XML validados e nomeados de acordo com SPS
INCOMPLETE_SPS_PKG_PATH:
    pacotes de XML validados e nomeados de acordo com SPS, mas com ativos digitais faltantes
"""

_default = dict(
    SCIELO_COLLECTION="spa",
    AM_URL_API="http://articlemeta.scielo.org/api/v1",
    STATIC_URL_FILE="http://www.scielo.br/",
    SOURCE_PATH=os.path.join(BASE_PATH, "xml/source"),
    CONVERSION_PATH=os.path.join(BASE_PATH, "xml/conversion"),
    SUCCESS_PROCESSING_PATH=os.path.join(BASE_PATH, "xml/success"),
    VALID_XML_PATH=os.path.join(BASE_PATH, "xml/xml_valid"),
    XML_ERRORS_PATH=os.path.join(BASE_PATH, "xml/xml_errors"),
    PROCESSED_SOURCE_PATH=os.path.join(BASE_PATH, "xml/source_processed"),
    GENERATOR_PATH=os.path.join(BASE_PATH, "xml/html"),
    DOWNLOAD_PATH=os.path.join(BASE_PATH, "xml/download"),
    LOGGER_PATH=os.path.join(BASE_PATH, ""),
    ISIS_BASE_PATH=os.environ.get("ISIS_BASE_PATH"),
    SPS_PKG_PATH=os.path.join(BASE_PATH, "xml/sps_packages"),
    INCOMPLETE_SPS_PKG_PATH=os.path.join(BASE_PATH, "xml/incomplete_sps_packages"),
    DATABASE_URI=os.environ.get("DATABASE_URI", "localhost:27017"),
    DATABASE_NAME=os.environ.get("DATABASE_NAME", "document-store"),
)


def get(config: str):
    """Recupera configurações do sistema, caso a configuração não
    esteja definida como uma variável de ambiente deve-se retornar a
    configuração padrão.
    """
    return os.environ.get(config, _default.get(config, ""))


INITIAL_PATH = [get(k) for k, v in _default.items() if k.endswith("_PATH")]
INITIAL_PATH = [item for item in INITIAL_PATH if item is not None]


DOC_TYPE_XML = """<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "JATS-journalpublishing1.dtd">"""

os.environ["XML_CATALOG_FILES"] = XML_CATALOG

os.environ["CLASSPATH"] = "".join(
    [
        os.path.join(BASE_PATH, "documentstore_migracao/utils/isis2json/lib/Bruma.jar"),
        ":",
        os.path.join(
            BASE_PATH, "documentstore_migracao/utils/isis2json/lib/jyson-1.0.1.jar"
        ),
    ]
)
