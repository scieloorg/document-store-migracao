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


class ErrorEnum(Enum):
    """Enumerador para agrupar nomes de erros utilizados na saída.

    Classe enumeradora.

    Atributos:

        `resource-not-found`: Quando algum asset ou rendition não é encontrado
        durante o empacotamento.

        `xml-not-found`: Quando um documento XML não é encontrado durante o
        empacotamento.

        `xml-not-update`: Quando um algum erro acontece durante a atualização do
        xml em questão. Geralmente são erros ligados ao LXML.

        `missing-metadata`: Quando algum metadado não existe no arquivo CSV
        utilizado para atualizar o XML em questão.

        `missing-manifest`: Quando não é econtrado o manifest no pacote.

        `xml-parser-error`: Quando existe algum erro na análise do XML.

        `bundle-not-found`: Quando não é encontrado o bundle para o documento.

        `issn-not-fount`: Quando não é encontrado o ISSN no documento.

        `package-not-import`: Quando o pacote não pode ser importado por qualquer erro.

    Atributos:
        Não há atributos.
    """

    RESOURCE_NOT_FOUND = "resource-not-found"
    NOT_UPDATED = "xml-not-update"
    XML_NOT_FOUND = "xml-not-found"
    MISSING_METADATA = "missing-metadata"
    MISSING_MANIFEST = "missing-manifest"
    XML_PARSER_ERROR = "xml-parser-error"
    BUNDLE_NOT_FOUND = "bundle-not-found"
    ISSN_NOT_FOUND = "issn-not-found"
    PACKAGE_NOT_IMPORTED = "package-not-import"


class LoggerAnalyzer(object):

    def __init__(self, in_file, out_file=None, log_format=None, out_formatter=None):
        self.in_file = in_file
        self.out_file = out_file
        self.content = ""
        self.out_formatter = self.set_formatter(out_formatter)
        self.log_format = (
            log_format if log_format else "<date> <time> <level> <module> <message>"
        )

    @classmethod
    def formatters(cls) -> Optional[Dict]:
        return {"jsonl": cls.json_formatter}

    def logformat_regex(self) -> (List[str], re.Pattern):
        """
        Método responsável por criar uma expressão regular para dividir as
        menssagens de log semanticamente.

        Args:
            format: formato de saída que será utilizado.

        Retornos:
            header, regex
            header: cabeçalho do formato do log.
            regex: expressão regular do formato.
            None: em caso de não "casamento"

        Exemplo:

            re.compile('^(?P<Date>.*?)
                       \\s+(?P<Time>.*?)
                       \\s+(?P<Error>.*?)
                       \\s+(?P<Module>.*?)
                       \\s+(?P<Message>.*?)$')

        Exceções:
            Não lança exceções.
        """
        headers = []
        splitters = re.split(r"(<[^<>]+>)", self.log_format)
        regex = ""
        for k in range(len(splitters)):
            if k % 2 == 0:
                splitter = re.sub(" +", "\\\s+", splitters[k])
                regex += splitter
            else:
                header = splitters[k].strip("<").strip(">")
                regex += "(?P<%s>.*?)" % header
                headers.append(header)
        regex = re.compile("^" + regex + "$")
        return headers, regex

    def load(self) -> None:
        """
        Realiza a leitura do conteúdo do arquivo.
        """

        if isinstance(self.in_file, IOBase):
            self.content = self.in_file.readlines()

    def parse(self, format=None) -> None:
        raise NotImplementedError("Uma instância de LoggerAnalyzer deve implementar o método parse.")

    def parser(
        self, line: str, regex: re.Pattern, error: ErrorEnum, group: str = None
    ) -> Optional[Dict]:
        """
        Analise do formato utilizado para verificar padrões por meio
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
        self, extra_parsers: List[Callable] = None
    ) -> List[Optional[Dict]]:
        """
        Realiza o parser do arquivo de log.

        Dado um arquivo de formato conhecido, esta função produz uma lista
        de dicionários. Os dicionários comportam ao menos quatro tipos de erros
        registrados no LOG.

        Args:
            extra_parsers = Lista de dicionário que contenha as chaves:
            `regex` e `error `

        Exemplo de uso:
            self.tokenize([
                    {"regex": MANIFEST_NOT_FOUND, "error": ErrorEnum.MISSING_MANIFEST},
                ])

        Retorno:
            Retorna uma lista de dicionário com a avaliação das linhas fornecida
            pelo atributo de classe ``self.content`ˆ.

            Exemplo de retorno:
                >>> [{'assets': ['imagem.tif'], 'pid': 'S1981-38212017000200203', 'error': 'resource'}]

        Exceções:
            Não lança exceções.
        """

        errors: List[Optional[Dict]] = []
        documents_errors: Dict[str, Dict] = {}

        for line in self.content:
            line = line.strip()

            _, regex = self.logformat_regex()

            match = regex.match(line)

            if match:

                format_dict = match.groupdict()

                for params in extra_parsers:

                    data = self.parser(format_dict['message'], **params)

                    if data is not None:
                        pid: Optional[str] = data.get("pid")
                        error: ErrorEnum = data.get("error")
                        uri: Optional[str] = data.get("uri")
                        level: Optional[str] = format_dict.get("level")
                        time: Optional[str] = format_dict.get("time")
                        date: Optional[str] = format_dict.get("date")
                        exception: Optional[str] = format_dict.get("exception")
                        group = data.pop("group", error)

                        if pid is not None:
                            documents_errors.setdefault(pid, {})
                            documents_errors[pid].setdefault(group, [])
                            documents_errors[pid][group].append(uri)
                            documents_errors[pid]["pid"] = pid
                            documents_errors[pid]["error"] = error
                            documents_errors[pid]["level"] = level
                            documents_errors[pid]["time"] = time
                            documents_errors[pid]["date"] = date
                        elif error != ErrorEnum.RESOURCE_NOT_FOUND:
                            data["level"] = level
                            data["time"] = time
                            data["date"] = date
                            errors.append(data)
                        break
            else:
                # Linha que não foi identificada como erro de empacotamento
                LOGGER.debug(
                    "Não foi possível analisar a linha '%s', talvez seja necessário especificar um analisador.",
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

    def json_formatter(self, errors: List[Optional[Dict]]) -> List[str]:
        """
        Imprime linha a linha da lista de entrada, convertendo o conteúdo para
        JSON.

        Args:
            errors: Lista de dicionários contendo os erro semânticamente identificado.

        Retornos:

            Retorna um JSON correspondente a cada dicionário do argumento errors,
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
        return LoggerAnalyzer.formatters().get(format, self.json_formatter)


class AnalyzerImport(LoggerAnalyzer):

    # IMPORT_REGEX
    manifest_not_found = re.compile(
        r".*No such file or directory: '(?P<file_path>[^']+)'",
        re.IGNORECASE,
    )
    xml_not_into_package = re.compile(
        r".*There is no XML file into package '(?P<package_path>[^']+)",
        re.IGNORECASE,
    )
    xml_parser_error = re.compile(
        r".*Could not parse the '(?P<file_path>[^']+)' file",
        re.IGNORECASE,
    )
    bundle_not_found = re.compile(
        r".*The bundle '(?P<bundle>[^']+)' was not updated.",
        re.IGNORECASE,
    )
    issn_not_found = re.compile(
        r".*No ISSN in document '(?P<pid>[^']+)'",
        re.IGNORECASE,
    )
    package_not_imported = re.compile(
        r".*Could not import package '(?P<package_path>[^']+).*'",
        re.IGNORECASE,
    )

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

        parsers = [
            {"regex": self.manifest_not_found, "error": ErrorEnum.MISSING_MANIFEST},
            {"regex": self.xml_not_into_package, "error": ErrorEnum.XML_NOT_FOUND},
            {"regex": self.xml_parser_error, "error": ErrorEnum.XML_PARSER_ERROR},
            {"regex": self.bundle_not_found, "error": ErrorEnum.BUNDLE_NOT_FOUND},
            {"regex": self.issn_not_found, "error": ErrorEnum.ISSN_NOT_FOUND},
            {"regex": self.package_not_imported, "error": ErrorEnum.PACKAGE_NOT_IMPORTED},
        ]

        self.load()
        formatter = self.set_formatter(format)
        tokenized_lines = self.tokenize(extra_parsers=parsers)
        lines = formatter(tokenized_lines)
        self.dump(lines)


class AnalyzerPack(LoggerAnalyzer):

    # PACKAGE_FROM_SITE REGEX
    asset_not_found_regex = re.compile(
        r".*\[(?P<pid>S\d{4}-.*)\].*Could not find asset "
        r"'(?P<uri>[^']+)'.*'(?P<xml>[^']+)'.?$",
        re.IGNORECASE,
    )
    rendition_not_found_regex = re.compile(
        r".*\[(?P<pid>S\d{4}-.*)\].*Could not find rendition "
        r"'(?P<uri>[^']+)'.*'(?P<xml>[^']+)'.?$",
        re.IGNORECASE,
    )
    xml_not_found_regex = re.compile(
        r".*Could not find the XML file '(?P<uri>[^']+)'.?", re.IGNORECASE
    )
    xml_not_updated_regex = re.compile(
        r".*Could not update xml '(?P<uri>[^']+)'.?"
        r"( The exception '(?P<exception>[^']+)')?",
        re.IGNORECASE,
    )
    xml_missing_metadata_regex = re.compile(
        r".*Missing \"(?P<metadata>[\w\s]+)\".* \"(?P<uri>[^']+)\"", re.IGNORECASE
    )

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

        parsers = [
            {
                "regex": asset_not_found_regex,
                "error": ErrorEnum.RESOURCE_NOT_FOUND,
                "group": "renditions",
            },
            {
                "regex": rendition_not_found_regex,
                "error": ErrorEnum.RESOURCE_NOT_FOUND,
                "group": "renditions",
            },
            {"regex": xml_not_updated_regex, "error": ErrorEnum.NOT_UPDATED},
            {"regex": xml_not_found_regex, "error": ErrorEnum.XML_NOT_FOUND},
            {"regex": xml_missing_metadata_regex, "error": ErrorEnum.MISSING_METADATA},
        ]

        self.load()
        formatter = self.set_formatter(format)
        tokenized_lines = self.tokenize(extra_parsers=parsers)
        lines = formatter(tokenized_lines)
        self.dump(lines)


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
    "-s",
    "--step",
    required=True,
    type=click.Choice(['pack', 'import']),
    help="Escolha o passo que deseja analisar",
)
@click.option(
    "--log_format",
    default="<date> <time> <level> <module> <message>",
    type=click.STRING,
    help="Define o formato do log. Padrão: <date> <time> <level> <module> <message>.",
)
@click.option(
    "--log_level",
    default="WARNING",
    type=click.Choice(["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Defini o nível de log de excecução. Padrão WARNING.",
)
@click.argument("output", type=click.File("w"), required=False)
def main(input, step, formatter, log_format, output, log_level):
    """
    Document Store Migration (DSM) - Log Analyzer

    Realiza a leitura dos arquivo de log da fase de empacotamento e importação
    da migração dos artigos do DSM.

    O resultado final desse analisador é um arquivo no formato JSONL onde nós
    permite realizar consultas com mais expressividade nos logs.

    """

    logging.basicConfig(format=LOGGER_FORMAT, level=getattr(logging, log_level.upper()))

    if not output:
        output = sys.stdout

    if step == 'pack':
        parser = AnalyzerPack(input, output, log_format, out_formatter=formatter)
        parser.parse()
    elif step == 'import':
        parser = AnalyzerImport(input, output, log_format, out_formatter=formatter)
        parser.parse()


if __name__ == "__main__":
    main()
