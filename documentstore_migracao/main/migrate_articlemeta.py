"""  """
import logging
import argparse

from .base import base_parser, minio_parser, mongodb_parser

from documentstore_migracao.processing import (
    extrated,
    conversion,
    validation,
    packing,
    inserting,
)
from documentstore_migracao.object_store import minio
from documentstore import adapters as ds_adapters


logger = logging.getLogger(__name__)


def migrate_articlemeta_parser(sargs):
    """ method to migrate articlemeta """

    parser = argparse.ArgumentParser(
        description="Document Store (Kernel) - Migração", parents=[base_parser(sargs)]
    )
    subparsers = parser.add_subparsers(title="Commands", metavar="", dest="command")

    # EXTRACAO
    extrate_parser = subparsers.add_parser(
        "extrate",
        help="Baixar todos os XML do article-meta (AM) de todos os periodicos, "
        "exceto se o argumento '--issn-journal' ou '-j' estiver informado com o ISSN do periodicos expecifico.",
    )
    extrate_parser.add_argument(
        "--issn-journal", "-j", help="Informe o ISSN do periodico que querira extrair"
    )

    # CONVERCAO
    import_parser = subparsers.add_parser(
        "conversion",
        help="Converte o 'body' de todos os arquivos XML de 'SOURCE_PATH' para o formato SPS, "
        "exceto se o argumento '--convetFile' ou '-c' estiver informado com o caminho de um arquivo XML para a converção.",
    )
    import_parser.add_argument(
        "--convetFile", "-c", help="Transformar somente o arquivos XML imformado"
    )

    # VALIDACAO
    validation_parser = subparsers.add_parser(
        "validation",
        help="Valida todos os arquivos XML da pasta 'CONVERSION_PATH', "
        "utilize os parametros: \n"
        "'--move_to_processed_source' ou '-MS' para mover os arquivos válidos de 'SOURCE_PATH' para 'PROCESSED_SOURCE_PATH' \n"
        "'--move_to_valid_xml' ou '-MC' para mover os arquivos válidos de 'CONVERSION_PATH' para 'VALID_XML_PATH' .\n"
        "Para validar somente um arquivo, utilize o argumento '--valideFile' ou '-f' informando o caminho de um arquivo XML para a validação.",
    )
    validation_parser.add_argument(
        "--move_to_processed_source",
        "-MS",
        action="store_true",
        default=False,
        help="Move os arquivos válidos de 'SOURCE_PATH' para 'PROCESSED_SOURCE_PATH'",
    )
    validation_parser.add_argument(
        "--move_to_valid_xml",
        "-MC",
        action="store_true",
        default=False,
        help="Move os arquivos válidos de 'CONVERSION_PATH' para 'VALID_XML_PATH'",
    )
    validation_parser.add_argument(
        "--valideFile", "-f", help="Valida somente o arquivos XML imformado"
    )

    # GERACAO PACOTE SPS
    pack_sps_parser = subparsers.add_parser(
        "pack_sps",
        help="Processa XMLs validados contidos na pasta 'VALID_XML_PATH' e gerar os pacotes no formato SPS, "
        "exceto se argumento '--packFile' ou '-p' estiver informando o caminho de um arquivo XML para geração do pacote",
    )
    pack_sps_parser.add_argument(
        "--packFile", "-p", help="Empacotar somente o documento XML imformado"
    )

    # IMPORTACAO
    import_parser = subparsers.add_parser(
        "import",
        help="Processa todos os pacotes SPS para importar no banco de dados do Document-Store (Kernel)",
        parents=[mongodb_parser(sargs), minio_parser(sargs)],
    )

    ################################################################################################
    args = parser.parse_args(sargs)

    # CHANGE LOGGER
    level = getattr(logging, args.loglevel.upper())
    logger = logging.getLogger()
    logger.setLevel(level)

    if args.command == "extrate":
        if args.issn_journal:
            extrated.extrated_selected_journal(args.issn_journal)
        else:
            extrated.extrated_all_data()

    elif args.command == "conversion":
        if args.convetFile:
            conversion.conversion_article_xml(args.convetFile)
        else:
            conversion.conversion_article_ALLxml()

    elif args.command == "validation":
        if args.valideFile:
            validation.validator_article_xml(args.valideFile)
        else:
            validation.validator_article_ALLxml(
                args.move_to_processed_source, args.move_to_valid_xml
            )

    elif args.command == "pack_sps":
        if args.packFile:
            packing.packing_article_xml(args.packFile)
        else:
            packing.packing_article_ALLxml()

    elif args.command == "import":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db)
        DB_Session = ds_adapters.Session.partial(mongo)

        storage = minio.MinioStorage(
            minio_host=args.minio_host,
            minio_access_key=args.minio_access_key,
            minio_secret_key=args.minio_secret_key,
            minio_secure=args.minio_is_secure,
        )

        inserting.inserting_document_store(session_db=DB_Session(), storage=storage)

    else:
        raise SystemExit(
            "Vc deve escolher algum parametro, ou '--help' ou '-h' para ajuda"
        )

    return 0
