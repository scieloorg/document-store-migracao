"""Script para analisar, agrupar dados provenientes dos logs da ferramenta
de migração das coleções SciELO."""

import argparse
import functools
import json
import logging
import re
import sys
from enum import Enum
from io import TextIOWrapper
from typing import Callable, Dict, List, Optional, Union

import click

LOGGER_FORMAT = u"%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s"
LOGGER = logging.getLogger(__name__)

ASSET_NOT_FOUND_REGEX = re.compile(
    r".*ERROR.*\[(?P<pid>S\d{4}-.*)\].*Could not find asset "
    r"'(?P<uri>[^']+)'.*'(?P<xml>[^']+)'.?$",
    re.IGNORECASE,
)
RENDITION_NOT_FOUND_REGEX = re.compile(
    r".*ERROR.*\[(?P<pid>S\d{4}-.*)\].*Could not find rendition "
    r"'(?P<uri>[^']+)'.*'(?P<xml>[^']+)'.?$",
    re.IGNORECASE,
)
XML_NOT_FOUND_REGEX = re.compile(
    r".*Could not find the XML file '(?P<uri>[^']+)'.?", re.IGNORECASE
)
XML_NOT_UPDATED_REGEX = re.compile(
    r".*Could not update xml '(?P<uri>[^']+)'.?"
    r"( The exception '(?P<exception>[^']+)')?",
    re.IGNORECASE,
)
XML_MISSING_METADATA_REGEX = re.compile(
    r".*Missing \"(?P<metadata>[\w\s]+)\".* \"(?P<uri>[^']+)\"", re.IGNORECASE
)


def jsonl_formatter(errors: List[Optional[Dict]]) -> List[str]:
    """Imprime linha a linha da lista de entrada, convertendo o conteúdo para
    JSON. É esperado então que uma lista de dados seja transformada no formato
    JSONL."""

    result = []
    for error in errors:
        result.append(json.dumps(error))

    return result


FORMATTERS = {"jsonl": jsonl_formatter}


def output_lines_to(lines: List[str], stream: TextIOWrapper) -> None:
    """Escreve resultado do parser em um arquivo caminho determinado.
    O stream de dados deve implementar a interface TextIOWrapper"""

    for line in lines:
        stream.write(line)
        stream.write("\n")


class ErrorEnum(Enum):
    """Enum para agrupar nomes de erros utilizados
    na saída do script"""

    RESOURCE_NOT_FOUND = "resource-not-found"
    NOT_UPDATED = "xml-not-update"
    XML_NOT_FOUND = "xml-not-found"
    MISSING_METADATA = "missing-metadata"


def general_parser(
    line: str, regex: re.Pattern, error: ErrorEnum, group: str = None
) -> Optional[Dict]:
    """Parser de formato geral utilizado para verificar padrões por meio
    de regex. Retorna o tipo de formato especificado na chamada."""

    match = regex.match(line)

    if match is None:
        return None

    return dict(match.groupdict(), **{"error": error.value, "group": group})


parse_asset_error = functools.partial(
    general_parser,
    regex=ASSET_NOT_FOUND_REGEX,
    error=ErrorEnum.RESOURCE_NOT_FOUND,
    group="assets",
)

parse_rendition_error = functools.partial(
    general_parser,
    regex=RENDITION_NOT_FOUND_REGEX,
    error=ErrorEnum.RESOURCE_NOT_FOUND,
    group="renditions",
)

parse_xml_update_error = functools.partial(
    general_parser, regex=XML_NOT_UPDATED_REGEX, error=ErrorEnum.NOT_UPDATED
)

parse_xml_not_found_error = functools.partial(
    general_parser, regex=XML_NOT_FOUND_REGEX, error=ErrorEnum.XML_NOT_FOUND
)

parse_missing_metadata_error = functools.partial(
    general_parser, regex=XML_MISSING_METADATA_REGEX, error=ErrorEnum.MISSING_METADATA,
)

PACK_FROM_SITE_PARSERS: List[Callable] = [
    parse_asset_error,
    parse_rendition_error,
    parse_xml_not_found_error,
    parse_xml_update_error,
    parse_missing_metadata_error,
]


def parse_pack_from_site_errors(
    lines: list, parsers: List[Callable] = PACK_FROM_SITE_PARSERS
) -> List[Optional[Dict]]:
    """Fachada que realiza o parser do arquivo de log do processo de
    empacotamento de xml nativos do utilitário `document-store-migracao`.

    Dado um arquivo de formato conhecido, esta função produz uma lista
    de dicionários. Os dicionários comportam ao menos quatro tipos de erros
    registrados no LOG, são eles:

    1) `resource-not-found`: Quando algum asset ou rendition não é encontrado
    durante o empacotamento.
    2) `xml-not-found`: Quando um documento XML não é encontrado durante o
    empacotamento.
    3) `xml-update`: Quando um algum erro acontece durante a atualização do
    xml em questão. Geralmente são erros ligados ao LXML.
    4) `missing-metadata`: Quando algum metadado não existe no arquivo CSV
    utilizado para atualizar o XML em questão.

    Exemplo de uso desta função:
    >>> parse_pack_from_site_errors([
            "2020-05-08 11:43:38 ERROR [documentstore_migracao.utils.build_ps_package] "
            "[S1981-38212017000200203] - Could not find asset 'imagem.tif' during packing XML "
            "'/1981-3821-bpsr-1981-3821201700020001.xml'"
        ])
    >>> [{'assets': ['imagem.tif'], 'pid': 'S1981-38212017000200203', 'error': 'resource'}]
    """

    errors: List[Optional[Dict]] = []
    documents_errors: Dict[str, Dict] = {}

    for line in lines:
        line = line.strip()

        for parser in parsers:
            data = parser(line)

            if data is not None:
                pid: Optional[str] = data.get("pid")
                error: ErrorEnum = data.get("error")
                uri: Optional[str] = data.get("uri")
                group = data.pop("group", error)

                if pid is not None:
                    documents_errors.setdefault(pid, {})
                    documents_errors[pid].setdefault(group, [])
                    documents_errors[pid][group].append(uri)
                    documents_errors[pid]["pid"] = pid
                    documents_errors[pid]["error"] = error
                elif error != ErrorEnum.RESOURCE_NOT_FOUND:
                    errors.append(data)
                break
        else:
            # Linha que não foi identificada como erro de empacotamento
            LOGGER.debug(
                "Cannot parse line '%s', maybe it need an specific parser.", line
            )

    documents_errors_values = list(documents_errors.values())
    errors.extend(documents_errors_values)
    return errors


@click.command()
@click.argument('input', type=click.File("r"),
                required=True)
@click.option('-f', '--formatter', default="jsonl", type=click.Choice(FORMATTERS.keys()),
              help="Choose a formater to convert the log parser")
@click.option('--loglevel', default="WARNING", type=click.Choice(
              ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
              help="Defines the loglevel of script. The default level is WARNING.")
@click.argument('output', type=click.File("w"), required=False)
def main(input, formatter, output, loglevel):
    """
        Document Store Migration (DSM) - Log Analyzer

        Realiza a leitura dos arquivo de log da fase de empacotamento e importação
        da migração dos artigos do DSM.

        O resultado final desse analisador é um arquivo no formato JSONL onde nós
        permite realizar consultas com mais expressividade nos logs.

    """

    logging.basicConfig(
        format=LOGGER_FORMAT, level=getattr(logging, loglevel.upper())
    )
    lines = input.readlines()
    formatter = FORMATTERS.get(formatter)
    parsed_errors = parse_pack_from_site_errors(lines)
    formatted_errors = formatter(parsed_errors)

    if output is not None:
        output_lines_to(formatted_errors, output)
    else:
        output_lines_to(formatted_errors, sys.stdout)


if __name__ == "__main__":
    main()
