"""  """
import logging
import argparse

from .base import base_parser, paths_parser

from documentstore_migracao.tools import generation, constructor
from documentstore_migracao import config


def tools_parser(sargs):
    parser = argparse.ArgumentParser(
        description="Document Store (Kernel) - Tools", parents=[base_parser(sargs)]
    )
    subparsers = parser.add_subparsers(title="Commands", metavar="", dest="command")

    # GENERATION HTML
    generation_parser = subparsers.add_parser(
        "generation",
        help="Gera todos os html dos XML contidos na pasta informada pelo argumento '--source-path' ou '-p' "
        "ou o default é a pasta 'VALID_XML_PATH' e salva os arquivos na pasta informada pelo '--desc-path' ou '-d' "
        "ou o default é a pasta 'GENERATOR_PATH' ",
        parents=[
            paths_parser(
                sargs,
                **{
                    "d_source": config.get("VALID_XML_PATH"),
                    "h_source": "Pasta onde esta os xml para gerar os html, default: VALID_XML_PATH",
                    "d_desc": config.get("GENERATOR_PATH"),
                    "h_desc": "Pasta onde sera salvo os HTML gerado, default: GENERATOR_PATH",
                }
            )
        ],
    )

    # CONSTRUCTOR XML
    construction_parser = subparsers.add_parser(
        "construction",
        help="Alterá todos os XML contidos na pasta informada pelo argumento '--source-path' ou '-p' "
        "ou o default é a pasta 'VALID_XML_PATH' e salva os arquivos na pasta informada pelo '--desc-path' ou '-d' "
        "ou o default é a pasta 'CONSTRUCTOR_PATH' e gerando a tag `article-id` com o scielo-id nos xml",
        parents=[
            paths_parser(
                sargs,
                **{
                    "d_source": config.get("VALID_XML_PATH"),
                    "h_source": "Pasta onde esta os xml para transformação, default: VALID_XML_PATH",
                    "d_desc": config.get("CONSTRUCTOR_PATH"),
                    "h_desc": "Pasta onde sera salvo os XML alterados, default: CONSTRUCTOR_PATH",
                }
            )
        ],
    )

    ################################################################################################
    args = parser.parse_args(sargs)

    # CHANGE LOGGER
    level = getattr(logging, args.loglevel.upper())
    logger = logging.getLogger()
    logger.setLevel(level)

    if args.command == "generation":
        generation.article_ALL_html_generator(args.source_path, args.desc_path)

    elif args.command == "construction":
        constructor.article_ALL_constructor(args.source_path, args.desc_path)

    else:
        raise SystemExit(
            "Vc deve escolher algum parametro, ou '--help' ou '-h' para ajuda"
        )

    return 0
