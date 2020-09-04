# Coding: utf-8

"""Script para analisar, agrupar dados provenientes dos logs da ferramenta
de migração das coleções SciELO."""

import argparse
import functools
import json
import logging
import re
import sys
from enum import Enum
from io import TextIOWrapper, IOBase
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


class ErrorEnum(Enum):
    """Enumerador para agrupar nomes de erros utilizados na saída.

    Classe enumeradora.

    Atributos:
        Não há atributos.
    """

    RESOURCE_NOT_FOUND = "resource-not-found"
    NOT_UPDATED = "xml-not-update"
    XML_NOT_FOUND = "xml-not-found"
    MISSING_METADATA = "missing-metadata"


PACK_FROM_SITE_PARSERS_PARAMS = [{
    'regex': ASSET_NOT_FOUND_REGEX,
    'error': ErrorEnum.RESOURCE_NOT_FOUND,
    'group': "renditions",
    },
    {
    'regex': RENDITION_NOT_FOUND_REGEX,
    'error': ErrorEnum.RESOURCE_NOT_FOUND,
    'group': "renditions",
    },
    {
    'regex': XML_NOT_UPDATED_REGEX,
    'error': ErrorEnum.NOT_UPDATED
    },
    {
    'regex': XML_NOT_FOUND_REGEX,
    'error': ErrorEnum.XML_NOT_FOUND
    },
    {
    'regex': XML_MISSING_METADATA_REGEX,
    'error': ErrorEnum.MISSING_METADATA
    }
]


class LoggerAnalyzer(object):

    def __init__(self, in_file, out_file=None, log_format=None):
        self.in_file = in_file
        self.out_file = out_file
        self.content = ""
        self.format = LoggerAnalyzer.formatters()

    @classmethod
    def formatters(cls) -> Optional[Dict]:
        return {"jsonl": cls.jsonl_formatter}

    def load(self) -> None:
        """
        Realiza a leitura do conteúdo do arquivo.

        Talves esse método deva lançar uma exceção.
        """
        if isinstance(self.in_file, IOBase):
            self.content = self.in_file.readlines()

    def parse(self, format=None) -> None:
        """
        Método realiza a análise.

        Args:
            format: formato de saída que será utilizado.

        Retornos:
            Não há retorno

        Exceções:
            Não lança exceções.

        """
        self.load()
        formatter = self.set_formatter(format)
        tokenized_lines = self.tokenize()
        lines = formatter(tokenized_lines)
        self.dump(lines)

    def parser(
        self, line: str, regex: re.Pattern, error: ErrorEnum, group: str = None
    ) -> Optional[Dict]:
        """Analise do formato utilizado para verificar padrões por meio
        de expressões regulares. Retorna o tipo de formato especificado na chamada.

        Args:
            line: Linha a ser analisada.
            regex: Expressão regular que será utilizada.
            error: Um enumerador, instância de classe ErroEnum, para qualificar o erro.
            group: Um classificador para o erro.

        Retorno:
            Um dicionário contendo a analise da linha com um seperação semântica.

            Exemplo:

                {
                 'pid': 'S0066-782X2020000500001',
                 'uri': 'bases/pdf/abc/v114n4s1/pt_0066-782X-abc-20180130.pdf',
                 'xml': '0066-782X-abc-20180130.xml',
                 'error': 'resource-not-found',
                 'group': 'renditions'
                }

        Exceções:
            Não lança exceções.

        """

        match = regex.match(line)

        if match is None:
            return None

        return dict(match.groupdict(), **{"error": error.value, "group": group})

    def tokenize(
        self, parsers: List[Callable] = PACK_FROM_SITE_PARSERS_PARAMS
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

        for line in self.content:
            line = line.strip()

            for params in PACK_FROM_SITE_PARSERS_PARAMS:

                data = self.parser(line, **params)

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
                    "Não foi possível analisar a linha '%s', talvés seja necessário especificar um analisador.",
                    line,
                )

        documents_errors_values = list(documents_errors.values())
        errors.extend(documents_errors_values)
        return errors

    def dump(self, lines) -> None:
        """Escreve resultado do parser em um arquivo caminho determinado.
        A sequência de caracteres de dados deve implementar a interface TextIOWrapper

        Args:
            lines: Lista de linhas contento sequência de caracteres.
        Retornos:
            Não há retorno

        Exceções:
            Não lança exceções.
        """

        for line in lines:
            self.out_file.write(line)
            self.out_file.write("\n")

    def jsonl_formatter(self, errors: List[Optional[Dict]]) -> List[str]:
        """Imprime linha a linha da lista de entrada, convertendo o conteúdo para
        JSON. É esperado então que uma lista de dados seja transformada no formato
        JSONL.

        Args:
            errors: Lista de dicionários contendo os erro semânticamente identificado.

        Retornos:

            Retorna um JSONL correspondente a cada dicionário do argumento errors,
            example:

            {"uri": "jbn/nahead/2175-8239-jbn-2019-0218.xml", "error": "xml-not-found"}
            {"uri": "jbn/nahead/2175-8239-jbn-2020-0025.xml", "error": "xml-not-found"}
            {"uri": "jbn/nahead/2175-8239-jbn-2019-0236.xml", "error": "xml-not-found"}
            {"uri": "jbn/nahead/2175-8239-jbn-2020-0050.xml", "error": "xml-not-found"}
            {"uri": "jbn/nahead/2175-8239-jbn-2020-0014.xml", "error": "xml-not-found"}

        Exceções:
            Não lança exceções.
        """

        result = []
        for error in errors:
            result.append(json.dumps(error))

        return result

    def set_formatter(self, format) -> formatters:
        return self.format.get(format, self.jsonl_formatter)


@click.command()
@click.argument("input", type=click.File("r"), required=True)
@click.option(
    "-f",
    "--formatter",
    default="jsonl",
    type=click.Choice(LoggerAnalyzer.formatters().keys()),
    help="Escolha um formato de conversão para o analisador",
)
@click.option(
    "--loglevel",
    default="WARNING",
    type=click.Choice(["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Defini o nível de log de excecução. Padrão é WARNING.",
)
@click.argument("output", type=click.File("w"), required=False)
def main(input, formatter, output, loglevel):
    """
    Document Store Migration (DSM) - Log Analyzer

    Realiza a leitura dos arquivo de log da fase de empacotamento e importação
    da migração dos artigos do DSM.

    O resultado final desse analisador é um arquivo no formato JSONL onde nós
    permite realizar consultas com mais expressividade nos logs.

    """

    logging.basicConfig(format=LOGGER_FORMAT, level=getattr(logging, loglevel.upper()))

    if not output:
        output = sys.stdout

    parser = LoggerAnalyzer(input, output)
    parser.parse()

    # lines = input.readlines()

    # formatter = FORMATTERS.get(formatter)
    # parsed_errors = parse_pack_from_site_errors(lines)
    # formatted_errors = formatter(parsed_errors)

    # if output is not None:
    #     output_lines_to(formatted_errors, output)
    # else:
    #     output_lines_to(formatted_errors, sys.stdout)


if __name__ == "__main__":
    main()
