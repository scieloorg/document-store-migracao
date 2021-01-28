# coding: utf-8

import os
import sys
import json
import logging
import argparse
import urllib3
import asyncio

from .base import base_parser, minio_parser, mongodb_parser

from documentstore_migracao import config
from documentstore_migracao.utils.build_ps_package import BuildPSPackage
from documentstore_migracao.utils import quality_checker

from documentstore_migracao.processing import (
    extracted,
    conversion,
    validation,
    packing,
    inserting,
    rollback,
    compare_articles_sites,
)
from documentstore_migracao.object_store import minio
from documentstore import adapters as ds_adapters

from sqlalchemy import create_engine


logger = logging.getLogger(__name__)


def migrate_articlemeta_parser(sargs):
    """ method to migrate articlemeta """

    parser = argparse.ArgumentParser(
        epilog="""Para mais informações de subcomando utilizar o
            argumento `-h`, exemplo: ds_migracao extract -h""",
        description="Document Store (Kernel) - Migração",
        parents=[base_parser(sargs)],
    )
    subparsers = parser.add_subparsers(title="Commands", metavar="", dest="command")

    # EXTRACAO
    extraction_parser = subparsers.add_parser(
        "extract", help="Extrai todos os artigos originários do formato HTML"
    )
    extraction_parser.add_argument(
        "file",
        type=argparse.FileType("r"),
        help="Arquivo com a lista de PIDs dos artigos a serem extraidos",
    )

    # CONVERSAO
    conversion_parser = subparsers.add_parser(
        "convert", help="Converte o conteúdo da tag `body` dos XMLs extraídos"
    )
    conversion_parser.add_argument(
        "--file",
        dest="convertFile",
        metavar="",
        help="Converte apenas o arquivo XML imformado",
    )

    conversion_parser.add_argument(
        "--spy",
        action="store_true",
        default=False,
        help="Compara a versão do texto antes e depois de cada Pipe de conversão",
    )

    # VALIDACAO
    validation_parser = subparsers.add_parser(
        "validate", help="Valida os XMLs por meio das regras da `SPS` vigente"
    )
    validation_parser.add_argument(
        "--move_to_processed_source",
        action="store_true",
        default=False,
        help="Move os arquivos válidos de 'SOURCE_PATH' para 'PROCESSED_SOURCE_PATH'",
    )
    validation_parser.add_argument(
        "--move_to_valid_xml",
        action="store_true",
        default=False,
        help="Move os arquivos válidos de 'CONVERSION_PATH' para 'VALID_XML_PATH'",
    )
    validation_parser.add_argument(
        "--file",
        "-f",
        dest="validateFile",
        metavar="",
        help="Valida apenas o arquivo XML imformado",
    )

    # GERACAO PACOTE SPS
    pack_sps_parser = subparsers.add_parser(
        "pack", help="Gera pacotes `SPS` a partir de XMLs válidos"
    )
    pack_sps_parser.add_argument(
        "--file",
        "-f",
        dest="packFile",
        metavar="",
        help="Gera o pacote `SPS` apenas para o documento XML imformado",
    )

    pack_sps_parser.add_argument(
        "-Issns-jsonfile",
        "--issns-jsonfile",
        dest="issns_jsonfile",
        required=False,
        help="ISSNs JSON data file",
    )

    # GERACAO PACOTE SPS FROM SITE STRUTURE
    pack_sps_parser_from_site = subparsers.add_parser(
        "pack_from_site", help="Gera pacotes `SPS` a partir da estrutura do Site SciELO"
    )
    pack_sps_parser_from_site.add_argument(
        "-a", "--acrons", dest="acrons", nargs="+", help="journal acronyms."
    )

    pack_sps_parser_from_site.add_argument(
        "-Xfolder",
        "--Xfolder",
        dest="xml_folder",
        required=True,
        help="XML folder path.",
    )

    pack_sps_parser_from_site.add_argument(
        "-Ifolder",
        "--Ifolder",
        dest="img_folder",
        required=True,
        help="IMG folder path.",
    )

    pack_sps_parser_from_site.add_argument(
        "-Pfolder",
        "--pfolder",
        dest="pdf_folder",
        required=True,
        help="PDF folder path.",
    )

    pack_sps_parser_from_site.add_argument(
        "-Ofolder",
        "--ofolder",
        dest="output_folder",
        default=config.get("SITE_SPS_PKG_PATH"),
        help="Output path.",
    )

    pack_sps_parser_from_site.add_argument(
        "-Article-csvfile",
        "--article-csvfile",
        dest="articles_csvfile",
        required=True,
        help="Article CSV data file from ISIS bases",
    )

    pack_sps_parser_from_site.add_argument(
        "-Issns-jsonfile",
        "--issns-jsonfile",
        dest="issns_jsonfile",
        required=False,
        help="ISSNs JSON data file",
    )

    # IMPORTACAO
    import_parser = subparsers.add_parser(
        "import",
        help="Processa todos os pacotes SPS para importar no banco de dados do Document-Store (Kernel)",
        parents=[mongodb_parser(sargs), minio_parser(sargs)],
    )

    import_parser.add_argument(
        "--folder",
        default=config.get("SPS_PKG_PATH"),
        metavar="",
        help=f"""Entry path to import SPS packages. The default path
        is: {config.get("SPS_PKG_PATH")}""",
    )

    import_parser.add_argument(
        "--pid_database_dsn",
        default=config.get("PID_DATABASE_DSN"),
        dest="pid_database_dsn",
        required=True,
        help="""Adicionar o DSN para checagem do PID V3 na base de dados do XC, \
        formatos de DSN suportados: https://docs.sqlalchemy.org/en/13/core/engines.html"""
    )

    import_parser.add_argument("--output", required=True, help="The output file path")

    # IMPORTACAO
    link_documents_issues = subparsers.add_parser(
        "link_documents_issues",
        help="Processa todos os documentos importados e relaciona eles com suas respectivas issues",
        parents=[mongodb_parser(sargs)],
    )
    link_documents_issues.add_argument(
        "documents",
        help="JSON file de documentos importados, e.g: ~/json/collection-issues.json",
    )
    link_documents_issues.add_argument(
        "journals", help="JSON file de journals result, e.g: ~/json/journal.json"
    )

    # ROLLBACK
    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Rollback of import process, deleting data registered on Kernel and MinIO",
        parents=[mongodb_parser(sargs)],
    )
    rollback_parser.add_argument(
        "imported_documents", help="The output file path of import command execution"
    )
    rollback_parser.add_argument(
        "extracted_title", help="ISIS Title extracted to JSON file, e.g: ~/json/title-today.json"
    )
    rollback_parser.add_argument(
        "--output", required=True, dest="output", help="The output file path",
    )

    # Referências
    example_text = """Usage:

    Before you update XMLs' mixed citations is necessary to create intermediary
    cache files using mst database(s). The first option is to use a fixed
    directory structure, for example:

    $ ds_migracao mixed-citations set-cache /bases/scl.000/bases/artigo/p

    The second option uses a single database which contains all articles'
    paragraphs (it may take some time), look:

    $ ds_migracao mixed-citations set-cache /bases/scl.000/bases/artigo/artigo.mst

    After the command is finished you can start to update XML with their mixed
    citations texts:

    $ ds_migracao mixed-citations update xml/source
    """

    references = subparsers.add_parser(
        "mixed-citations",
        help="Update mixed citations",
        epilog=example_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    references_subparser = references.add_subparsers(
        title="Commands", metavar="", dest="refcommand"
    )

    # Subparser mixed citations set cache
    references_cache = references_subparser.add_parser(
        "set-cache", help="Create cache files for selected articles"
    )

    references_cache.add_argument(
        "mst", help="Directory root or MST file where paragraphs are located"
    )

    references_cache.add_argument(
        "--override",
        action="store_true",
        help="Override previous cached files",
    )

    # Subparser mixed citations update
    references_update = references_subparser.add_parser(
        "update", help="Update XML mixed citations"
    )

    references_update.add_argument(
        "source", help="XML file or directory containing XMLs"
    )

    references_update.add_argument(
        "--output", metavar="dir", help="Output directory path"
    )

    references_update.add_argument(
        "--override",
        action="store_true",
        help="Override old mixed citations in XML file",
    )

    quality_parser = subparsers.add_parser(
        "quality", help="Help to check the quality of the migration process.",
    )

    quality_parser.add_argument(
        "pids",
        help="File containg a list of pids to check.",
        type=argparse.FileType("r"),
    )

    quality_parser.add_argument(
        "--output",
        help="Path to the output file that will contain URLs unavailable.",
        type=argparse.FileType("a"),
    )

    quality_parser.add_argument(
        "target",
        help='Define an URL template for target Website (e.g "http://www.scielo.br/article/\$id"',
    )

    check_similarity = subparsers.add_parser(
        "check_similarity", help="Checks the similarity between the new and the old site.",
    )

    check_similarity.add_argument(
        "--similarity_input",
        required=True,
        help="File containg a list of pids to check similarity.",
        dest="similarity_input",
    )

    check_similarity.add_argument(
        "--similarity_output",
        required=True,
        help="Path to the output file will write a jsonl file.",
        dest="similarity_output",
    )

    check_similarity.add_argument(
        "--cut_off_mark",
        default=90,
        type=int,
        help="cut note to indicate items that are considered similar or not.",
        dest="cut_off_mark",
    )

    ################################################################################################
    args = parser.parse_args(sargs)

    # CHANGE LOGGER
    level = getattr(logging, args.loglevel.upper())
    logger = logging.getLogger()
    logger.setLevel(level)

    options = {'maxIdleTimeMS': config.get('MONGO_MAX_IDLE_TIME_MS'),
               'socketTimeoutMS': config.get('MONGO_SOCKET_TIMEOUT_MS'),
               'connectTimeoutMS': config.get('MONGO_CONNECT_TIMEOUT_MS')}

    if args.command == "extract":
        extracted.extract_all_data(args.file.readlines())

    elif args.command == "convert":
        if args.convertFile:
            conversion.convert_article_xml(args.convertFile, spy=args.spy)
        else:
            conversion.convert_article_ALLxml(args.spy)

    elif args.command == "validate":
        if args.validateFile:
            validation.validate_article_xml(args.validateFile)
        else:
            validation.validate_article_ALLxml(
                args.move_to_processed_source, args.move_to_valid_xml
            )

    elif args.command == "pack":

        # verifica a existência da pasta PDF essencial para empacotamento.
        pdf = config.get('SOURCE_PDF_FILE')
        if not os.path.exists(pdf):
            logger.error("A pasta para obter os PDFs para a fase de empacotamento, não está acessível: %s (revise o arquivo de configuração ``SOURCE_PDF_FILE``) ", pdf)
            sys.exit()

        # verifica a existência da pasta IMG essencial para empacotamento.
        img = config.get('SOURCE_IMG_FILE')
        if not os.path.exists(img):
            logger.error("A pasta para obter os IMGs para a fase de empacotamento, não está acessível: %s (revise o arquivo de configuração ``SOURCE_IMG_FILE``) ", pdf)
            sys.exit()

        if args.issns_jsonfile:
            with open(args.issns_jsonfile) as fp:
                packing.ISSNs = json.loads(fp.read())

        # pack HTML
        if args.packFile:
            packing.pack_article_xml(args.packFile)
        else:
            packing.pack_article_ALLxml()

    elif args.command == "pack_from_site":
        # pack XML
        build_ps = BuildPSPackage(
            args.xml_folder,
            args.img_folder,
            args.pdf_folder,
            args.output_folder,
            args.articles_csvfile,
        )
        if args.issns_jsonfile:
            with open(args.issns_jsonfile) as fp:
                build_ps.issns = json.loads(fp.read())
        build_ps.run()

    elif args.command == "import":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db, options=options)
        DB_Session = ds_adapters.Session.partial(mongo)

        pid_database_engine = create_engine(args.pid_database_dsn,
                                            connect_args=json.loads(config.get('DATABASE_CONNECT_ARGS')))

        http_client = urllib3.PoolManager(
            timeout=config.get('MINIO_TIMEOUT'),
            maxsize=10,
            cert_reqs='CERT_REQUIRED',
            retries=urllib3.Retry(
                total=5,
                backoff_factor=0.2,
                status_forcelist=[500, 502, 503, 504]
            ))

        storage = minio.MinioStorage(
            minio_host=args.minio_host,
            minio_access_key=args.minio_access_key,
            minio_secret_key=args.minio_secret_key,
            minio_secure=args.minio_is_secure,
            minio_http_client=http_client
        )

        inserting.import_documents_to_kernel(
            session_db=DB_Session(), pid_database_engine=pid_database_engine, storage=storage,
            folder=args.folder, output_path=args.output
        )

    elif args.command == "link_documents_issues":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db, options=options)
        DB_Session = ds_adapters.Session.partial(mongo)

        inserting.register_documents_in_documents_bundle(
            session_db=DB_Session(), file_documents=args.documents, file_journals=args.journals
        )

    elif args.command == "rollback":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db, options=options)

        rollback.rollback_kernel_documents(
            session_db=rollback.RollbackSession(mongo),
            import_output_path=args.imported_documents,
            extracted_title_path=args.extracted_title,
            output_path=args.output,
        )

    elif args.command == "mixed-citations":
        from documentstore_migracao.processing import pipeline

        if args.refcommand == "set-cache":
            pipeline.set_mixed_citations_cache(args.mst, override=args.override)
        elif args.refcommand == "update":
            pipeline.update_articles_mixed_citations(
                source=args.source, output_folder=args.output, override=args.override,
            )
    elif args.command == "quality":
        quality_checker.check_documents_availability_in_website(
            args.pids.readlines(), args.target, args.output
        )
    elif args.command == "check_similarity":

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(compare_articles_sites.main(
                input_filepath=args.similarity_input,
                output_filepath=args.similarity_output,
                cut_off_mark=args.cut_off_mark,
            ))

    else:
        parser.print_help()

    return 0
