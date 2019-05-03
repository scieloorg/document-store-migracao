import argparse
import pkg_resources


def base_parser(args):
    """ Parser com parametros basico da execução do app """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--loglevel", default="INFO")

    packtools_version = pkg_resources.get_distribution("documentstore-migracao").version
    parser.add_argument("--version", action="version", version=packtools_version)

    return parser


def mongodb_parser(args):
    """Parser utilizado para capturar informações sobre conexão
    com o MongoDB"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--uri",
        required=True,
        help="""URI to connect at MongoDB where the import
        will be done, e.g: "mongodb://user:password@mongodb-host/?authSource=admin" """,
    )

    parser.add_argument("--db", required=True, help="Database name to import registers")

    return parser


def minio_parser(args):
    """Parser utilizado para capturar informações sobre conexão
    com o Min.io"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--minio_host",
        required=True,
        help="""Host to connect to Min.io ObjectStorage, e.g: "play.min.io:9000" """,
    )
    parser.add_argument(
        "--minio_access_key", required=True, help="Access key to Min.io, e.g: minion"
    )
    parser.add_argument(
        "--minio_secret_key", required=True, help="Secure key to Min.io, e.g: minion123"
    )
    parser.add_argument(
        "--minio_is_secure",
        default=False,
        help="if connection wich to Min.io is secure, default False",
        action="store_true",
    )

    return parser


def paths_parser(args, d_source, h_source, d_desc, h_desc):
    """Parser utilizado para capturar informações sobre path de origem e path de destino
    dos comandos de tools """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--source-path", "-p", default=d_source, help=h_source)
    parser.add_argument("--desc-path", "-d", default=d_desc, help=h_desc)

    return parser
