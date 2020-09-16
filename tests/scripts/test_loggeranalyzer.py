import io
import re
import json
import unittest

from scripts import loggeranalyzer


class TestLoggerAnalyzer(unittest.TestCase):

    def setUp(self):
        self.log_file = io.StringIO()
        self.out_file = io.StringIO()

    def tearDown(self):
        self.log_file.close()
        self.out_file.close()

    def test_is_instance_loggeranalyzer(self):
        """
        Testa a instanciação.
        """
        parser = loggeranalyzer.LoggerAnalyzer(self.log_file)

        self.assertIsInstance(parser, loggeranalyzer.LoggerAnalyzer)

    def test_json_formatter_return_expect_list(self):
        """
        Testa se o retorno do método LoggerAnalyzer.json_formatter é uma lista.
        """
        errors = [{'uri': 'cadbto/nahead/2526-8910-cadbto-2526-8910ctoAO1930.xml', 'error': 'xml-not-found', 'level': 'ERROR', 'time': '14:49:55', 'date': '2020-08-26'},
                  {'renditions': ['bases/pdf/abc/v114n4s1/pt_0066-782X-abc-20180130.pdf'], 'pid': 'S0066-782X2020000500001', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '13:46:05', 'date': '2020-08-26'},
                  {'renditions': ['bases/pdf/esa/v25n3/1809-4457-esa-s1413-41522020137661.pdf'], 'pid': 'S1413-41522020000300451', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '13:57:25', 'date': '2020-08-26'},
                  {'renditions': ['htdocs/img/revistas/jbpneu/v46n6/1806-3713-jbpneu-46-6-e20190272-suppl01-en'], 'pid': 'S1806-37132020000600204', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '14:03:13', 'date': '2020-08-26'},
                  {'renditions': ['htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig02.tif', 'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig01.tif', 'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig06.tif',
                                  'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig03.tif', 'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig07.tif'], 'pid': 'S0102-77862020000100089', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '14:22:50', 'date': '2020-08-26'}]

        parser = loggeranalyzer.LoggerAnalyzer(self.log_file)

        self.assertIsInstance(parser.json_formatter(errors), list)
        expected_list = ['{"uri": "cadbto/nahead/2526-8910-cadbto-2526-8910ctoAO1930.xml", "error": "xml-not-found", "level": "ERROR", "time": "14:49:55", "date": "2020-08-26"}',
                         '{"renditions": ["bases/pdf/abc/v114n4s1/pt_0066-782X-abc-20180130.pdf"], "pid": "S0066-782X2020000500001", "error": "resource-not-found", "level": "ERROR", "time": "13:46:05", "date": "2020-08-26"}',
                         '{"renditions": ["bases/pdf/esa/v25n3/1809-4457-esa-s1413-41522020137661.pdf"], "pid": "S1413-41522020000300451", "error": "resource-not-found", "level": "ERROR", "time": "13:57:25", "date": "2020-08-26"}',
                         '{"renditions": ["htdocs/img/revistas/jbpneu/v46n6/1806-3713-jbpneu-46-6-e20190272-suppl01-en"], "pid": "S1806-37132020000600204", "error": "resource-not-found", "level": "ERROR", "time": "14:03:13", "date": "2020-08-26"}',
                         '{"renditions": ["htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig02.tif", "htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig01.tif", "htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig06.tif", "htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig03.tif", "htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig07.tif"], "pid": "S0102-77862020000100089", "error": "resource-not-found", "level": "ERROR", "time": "14:22:50", "date": "2020-08-26"}']
        self.assertEqual(parser.json_formatter(errors), expected_list)

    def test_json_formatter_if_each_is_json_unserialized(self):
        """
        Testa se o retorno do método LoggerAnalyzer.json_formatter é um deserializável
        """
        errors = [{'uri': 'cadbto/nahead/2526-8910-cadbto-2526-8910ctoAO1930.xml', 'error': 'xml-not-found', 'level': 'ERROR', 'time': '14:49:55', 'date': '2020-08-26'},
                  {'renditions': ['bases/pdf/abc/v114n4s1/pt_0066-782X-abc-20180130.pdf'], 'pid': 'S0066-782X2020000500001', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '13:46:05', 'date': '2020-08-26'},
                  {'renditions': ['bases/pdf/esa/v25n3/1809-4457-esa-s1413-41522020137661.pdf'], 'pid': 'S1413-41522020000300451', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '13:57:25', 'date': '2020-08-26'},
                  {'renditions': ['htdocs/img/revistas/jbpneu/v46n6/1806-3713-jbpneu-46-6-e20190272-suppl01-en'], 'pid': 'S1806-37132020000600204', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '14:03:13', 'date': '2020-08-26'},
                  {'renditions': ['htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig02.tif', 'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig01.tif', 'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig06.tif',
                                  'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig03.tif', 'htdocs/img/revistas/rbmet/v35n1/0102-7786-rbmet-35-01-0004-fig07.tif'], 'pid': 'S0102-77862020000100089', 'error': 'resource-not-found', 'level': 'ERROR', 'time': '14:22:50', 'date': '2020-08-26'}]

        parser = loggeranalyzer.LoggerAnalyzer(self.log_file)
        for log_line in parser.json_formatter(errors):
            self.assertIsInstance(json.loads(log_line), dict)

    def test_dump_write_line_in_out_file_atribute(self):
        """
        Testa se o método dump escreve linhas no atributo out_file e garante que
        cada linha contém o caracter de retorno ``\n``"
        """

        lines = ['{"uri": "alea/nahead/1807-0299-alea-22-01-9-errata.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:42:29", "date": "2020-08-26"}',
                 '{"uri": "alea/nahead/1807-0299-alea-22-01-15-errata.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:42:30", "date": "2020-08-26"}',
                 '{"uri": "abc/nahead/0066-782X-abc-20190243.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:46:09", "date": "2020-08-26"}',
                 '{"uri": "abc/nahead/0066-782X-abc-2020023.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:46:09", "date": "2020-08-26"}',
                 '{"uri": "abc/nahead/0066-782X-abc-20190331.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:46:09", "date": "2020-08-26"}',
                 '{"uri": "abc/nahead/0066-782X-abc-20190867.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:46:09", "date": "2020-08-26"}',
                 '{"uri": "abc/nahead/0066-782X-abc-20190053.xml", "error": "xml-not-found", "level": "ERROR", "time": "13:46:10", "date": "2020-08-26"}']

        parser = loggeranalyzer.LoggerAnalyzer(self.log_file, self.out_file)

        parser.dump(lines)

        parser.out_file.seek(0)

        for i, line in enumerate(parser.out_file.readlines()):
            self.assertEqual('%s\n' % lines[i], line)

    def test_logformat_regex(self):
        """
        Testa se o método retorna uma expressão regular a partir de um formato e
        um cabeçalho do formato do log.

        """

        parser = loggeranalyzer.LoggerAnalyzer(self.log_file, self.out_file,
                                               "<date> <time> <level> <module> <message>")

        header, regex = parser.logformat_regex()

        self.assertTrue(header, ['date', 'time', 'level', 'module', 'message'])
        self.assertTrue(regex, re.compile('^(?P<date>.*?)\\s+(?P<time>.*?)\\s+(?P<level>.*?)\\s+(?P<module>.*?)\\s+(?P<message>.*?)$'))

    def test_load_set_content_atribute(self):
        """
        Testa se o método LoggerAnalyzer.load atribui as linhas à LoggerAnalyzer.content.
        """
        self.log_file.write("22020-08-17 14:17:25 ERROR [documentstore_migracao.processing.inserting] Could not import package 'path/S0100-39842010000300012'. The following exception was raised: '(sqlite3.OperationalError) unable to open database")
        self.log_file.seek(0)

        parser = loggeranalyzer.LoggerAnalyzer(self.log_file)

        parser.load()

        self.assertEqual(parser.content, ["22020-08-17 14:17:25 ERROR [documentstore_migracao.processing.inserting] Could not import package 'path/S0100-39842010000300012'. The following exception was raised: '(sqlite3.OperationalError) unable to open database"])

    def test_parser_return_expect_dict(self):
        """
        Testa se o método parser retorna um dicionário contendo conteúdo
        correspondente os errors.
        """
        line = "No ISSN in document 'JwqGdMDrdcV3Z7MFHgtKvVk'"
        self.log_file.write(line)
        self.log_file.seek(0)

        _ = loggeranalyzer.LoggerAnalyzer(self.log_file)

        parsed = _.parser(line, **loggeranalyzer.IMPORT_PARSERS_PARAMS[-2])

        self.assertEqual(parsed, {'pid': 'JwqGdMDrdcV3Z7MFHgtKvVk', 'error': 'issn-not-found', 'group': None})

    def test_tokenize_return_expect_list(self):
        """
        Testa se o retorno do método tokenize é o esperado.
        """

        lines = ["2020-09-11 08:35:56 ERROR [documentstore_migracao.processing.inserting] The bundle '0036-3634-2009-v45-n4' was not updated. During executions this following exception was raised 'Nenhum documents_bundle encontrado 0036-3634-2009-v45-n4'.\n",
                 "2020-09-11 08:35:56 ERROR [documentstore_migracao.processing.inserting] The bundle '0036-3634-2009-v45-n4' was not updated. During executions this following exception was raised 'Nenhum documents_bundle encontrado 0036-3634-2009-v45-n4'.\n",
                 "2020-09-11 08:35:56 ERROR [documentstore_migracao.processing.inserting] No ISSN in document 'JwqGdMDrdcV3Z7MFHgtKvVk'\n", ]

        self.log_file.writelines(lines)
        self.log_file.seek(0)

        parsed = loggeranalyzer.LoggerAnalyzer(self.log_file)

        parsed.load()
        tokenized_lines = parsed.tokenize(loggeranalyzer.IMPORT_PARSERS_PARAMS)

        self.assertEqual(tokenized_lines, [{'bundle': '0036-3634-2009-v45-n4', 'error': 'bundle-not-found', 'level': 'ERROR', 'time': '08:35:56', 'date': '2020-09-11'},
                                           {'bundle': '0036-3634-2009-v45-n4', 'error': 'bundle-not-found', 'level': 'ERROR', 'time': '08:35:56', 'date': '2020-09-11'},
                                           {None: [None], 'pid': 'JwqGdMDrdcV3Z7MFHgtKvVk', 'error': 'issn-not-found', 'level': 'ERROR', 'time': '08:35:56', 'date': '2020-09-11'}])
