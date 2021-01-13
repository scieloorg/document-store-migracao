import os
from packtools.catalogs import XML_CATALOG

BASE_PATH = os.path.dirname(os.path.dirname(__file__))
INFERERER_RULES_FILE_PATH = os.path.join(BASE_PATH, "documentstore_migracao", "utils", "convert_html_body.txt")

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
SITE_SPS_PKG_PATH:
    Caminhio para os pacotes SPS XML gerados a partir da estrutura do Site antigo do SciELO
INCOMPLETE_SPS_PKG_PATH:
    pacotes de XML validados e nomeados de acordo com SPS, mas com ativos digitais faltantes
ERRORS_PATH:
    arquivos de erros
"""

_default = dict(
    SCIELO_COLLECTION="scl",
    AM_URL_API="http://articlemeta.scielo.org/api/v1",
    STATIC_URL_FILE="http://www.scielo.br/",
    SOURCE_PATH=os.path.join(BASE_PATH, "xml/source"),
    PROCESSED_SOURCE_PATH=os.path.join(BASE_PATH, "xml/source_processed"),
    CONVERSION_PATH=os.path.join(BASE_PATH, "xml/conversion"),
    VALID_XML_PATH=os.path.join(BASE_PATH, "xml/xml_valid"),
    XML_ERRORS_PATH=os.path.join(BASE_PATH, "xml/xml_errors"),
    SPS_PKG_PATH=os.path.join(BASE_PATH, "xml/sps_packages"),
    SITE_SPS_PKG_PATH=os.path.join(BASE_PATH, "xml/site_sps_packages"),
    INCOMPLETE_SPS_PKG_PATH=os.path.join(BASE_PATH, "xml/incomplete_sps_packages"),
    LOGGER_PATH=os.path.join(BASE_PATH, ""),
    GENERATOR_PATH=os.path.join(BASE_PATH, "xml/html"),
    CONSTRUCTOR_PATH=os.path.join(BASE_PATH, "xml/constructor"),
    ERRORS_PATH=os.path.join(BASE_PATH, "xml/errors"),
    CACHE_PATH=os.path.join(BASE_PATH, ".cache"),
    PARAGRAPH_CACHE_PATH=os.path.join(BASE_PATH, "xml/paragraphs"),
    VALIDATE_ALL="FALSE",
    THREADPOOL_MAX_WORKERS=os.cpu_count() * 5,
    PROCESSPOOL_MAX_WORKERS=os.cpu_count(),
    PID_DATABASE_DSN="sqlite:///pid_manager_database.db",
    MONGO_MAX_IDLE_TIME_MS=20000,
    MONGO_SOCKET_TIMEOUT_MS=20000,
    MONGO_CONNECT_TIMEOUT_MS=20000,
    MINIO_TIMEOUT=20000,

    # DATABASE_CONNECT_ARGS must be a JSON String
    DATABASE_CONNECT_ARGS='{"connect_timeout": 20000}',
    SOURCE_PDF_FILE=os.path.join(BASE_PATH, "bases"),
    SOURCE_IMG_FILE=os.path.join(BASE_PATH, "htdocs"),

    SITE_INSTANCES=[
        {
            "name": "classic",
            "url": "http://www.scielo.br/scielo.php?script=sci_arttext&pid={}",
            "html": {'tag_name': 'div', 'atrib': {'class': 'content'}},
            "compare_tags": ["p", "li", "b", "i", "em", "sup", "br", "blockquote", "div"],
            "remove_tags": [{'tag_name': 'script', 'atrib': {}},
                            {'tag_name': 'div', 'atrib': {'class': 'footer'}},
                            {'tag_name': 'div', 'atrib': {'id': 'group'}},
                            {'tag_name': 'div', 'atrib': {'class': 'license'}}, ],
            "remove_texts": ['REFERENCES', 'References', '[ Links ]', 'abstract', 'abstracts',
                             'ABSTRACT', 'ABSTRACTS', 'Abstract', 'Abstracts',
                             'resumo', 'RESUMO', 'doi', 'thumbnail', 'Thumbnail',
                             'http', 'https', 'version', 'Print', 'author',
                             'AUHTOR', 'How', 'cite', 'Close', 'close', 'suppl', 'about', 'About', 'ABOUT',
                             '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Copy', 'copy', 'pdf', 'PDF',
                             'figures', 'Figures', 'FIGURES']
        },
        {
            "name": "new",
            "url": "http://new.scielo.br/article/{}",
            "html": {'tag_name': 'div', 'atrib': {'id': 'standalonearticle'}},
            "compare_tags": ["p", "li", "b", "i", "em", "sup", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "table"],
            "remove_tags": [{'tag_name': 'span', 'atrib': {'class': 'refCtt'}},
                            {'tag_name': 'script', 'atrib': {}},
                            {'tag_name': 'sup', 'atrib': {'class': 'big'}},
                            {'tag_name': 'div', 'atrib': {'class': 'thumb'}},
                            {'tag_name': 'ul', 'atrib': {'class': 'articleMenu'}},
                            {'tag_name': 'div', 'atrib': {'data-anchor': 'Datas de Publicação '}},
                            {'tag_name': 'div', 'atrib': {'data-anchor': 'Publication Dates'}},
                            {'tag_name': 'section', 'atrib': {'class': 'documentLicense'}}],
            "remove_texts": ['REFERENCES', 'References', 'REFERÊNCIAS BIBLIOGRÁFICAS', 'references',
                             'abstract', 'abstracts', 'Abstract', 'Abstracts',
                             'ABSTRACT', 'ABSTRACTS', 'thumbnail', 'Thumbnail',
                             'resumo', 'RESUMO', 'doi', 'http', 'https',
                             'version', 'Print', 'author', 'AUHTOR', 'How',
                             'cite', 'Close', 'close', 'suppl', 'about', 'About', 'ABOUT'
                             '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Copy', 'copy', 'pdf', 'PDF',
                             'figures', 'Figures', 'FIGURES']
        },
    ]

)

def get(config: str):
    """Recupera configurações do sistema, caso a configuração não
    esteja definida como uma variável de ambiente deve-se retornar a
    configuração padrão.
    """
    return os.environ.get(config, _default.get(config, ""))


INITIAL_PATH = [get(k) for k, v in _default.items() if k.endswith("_PATH")]
INITIAL_PATH = [item for item in INITIAL_PATH if item is not None]


DOC_TYPE_XML = """<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd">"""

os.environ["XML_CATALOG_FILES"] = XML_CATALOG

JAVA_LIB_DIR = os.path.join(BASE_PATH, "documentstore_migracao/utils/isis2json/lib/")

JAVA_LIBS_PATH = [
    os.path.join(JAVA_LIB_DIR, file)
    for file in os.listdir(JAVA_LIB_DIR)
    if file.endswith(".jar")
]

os.environ["CLASSPATH"] = ":".join(JAVA_LIBS_PATH)
