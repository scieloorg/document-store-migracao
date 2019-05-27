"""  """
import logging
import argparse

from .base import base_parser, minio_parser, mongodb_parser

from documentstore_migracao import config
from documentstore_migracao.utils.build_ps_package import BuildPSPackage

from documentstore_migracao.processing import (
    extracted,
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

    # CONVERCAO
    import_parser = subparsers.add_parser(
        "convert", help="Converte o conteúdo da tag `body` dos XMLs extraídos"
    )
    import_parser.add_argument(
        "--file",
        dest="convertFile",
        metavar="",
        help="Converte apenas o arquivo XML imformado",
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
        default=config.get('SITE_SPS_PKG_PATH'),
        help="Output path.",
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

    if args.command == "extract":
        extracted.extract_all_data(args.file.readlines())

    elif args.command == "convert":
        if args.convertFile:
            conversion.convert_article_xml(args.convertFile)
        else:
            conversion.convert_article_ALLxml()

    elif args.command == "validate":
        if args.validateFile:
            validation.validate_article_xml(args.validateFile)
        else:
            validation.validate_article_ALLxml(
                args.move_to_processed_source, args.move_to_valid_xml
            )

    elif args.command == "pack":
        if args.packFile:
            packing.pack_article_xml(args.packFile)
        else:
            packing.pack_article_ALLxml()

    elif args.command == "pack_from_site":
        build_ps = BuildPSPackage(
            args.acrons,
            args.xml_folder,
            args.img_folder,
            args.pdf_folder,
            args.output_folder,
        )

        build_ps.run()

    elif args.command == "import":
        mongo = ds_adapters.MongoDB(uri=args.uri, dbname=args.db)
        DB_Session = ds_adapters.Session.partial(mongo)

        storage = minio.MinioStorage(
            minio_host=args.minio_host,
            minio_access_key=args.minio_access_key,
            minio_secret_key=args.minio_secret_key,
            minio_secure=args.minio_is_secure,
        )

        inserting.import_documents_to_kernel(session_db=DB_Session(), storage=storage)

    else:
        raise SystemExit(
            "Vc deve escolher algum parametro, ou '--help' ou '-h' para ajuda"
        )

    return 0
