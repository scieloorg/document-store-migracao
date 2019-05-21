import os
import unittest
from lxml import etree

from documentstore_migracao.utils.convert_html_body import DataSanitizationPipeline


class TestDataSanitizationPipeline(unittest.TestCase):
    def _transform(self, text, pipe):
        tree = etree.fromstring(text)
        data = text, tree
        raw, transformed = pipe.transform(data)
        self.assertEqual(raw, text)
        return raw, transformed

    def setUp(self):
        self.pipeline = DataSanitizationPipeline()

    def test__wrap_graphic_in_extlink(self):
        text = """<root><ext-link href="#top"><graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/></ext-link></root>"""

        raw, transformed = self._transform(text, self.pipeline.GraphicInExtLink())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><ext-link href="#top"><p><inline-graphic xmlns:ns2="http://www.w3.org/1999/xlink" ns2:href="/img/revistas/gs/v29n2/seta.gif"/></p></ext-link></root>""",
        )

    def test__table_in_body(self):
        text = """<root><body><table><tr><td>TEXTO</td></tr></table></body></root>"""

        raw, transformed = self._transform(text, self.pipeline.TableinBody())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><body><table-wrap><table><tr><td>TEXTO</td></tr></table></table-wrap></body></root>""",
        )

    def test__table_in_p(self):
        text = """<root><p><table><tr><td>TEXTO</td></tr></table></p></root>"""

        raw, transformed = self._transform(text, self.pipeline.TableinP())
        self.assertEqual(
            etree.tostring(transformed),
            b"""<root><p><table-wrap><table><tr><td>TEXTO</td></tr></table></table-wrap></p></root>""",
        )

    def test__add_p_in_fn(self):
        text = """<root><fn>TEXTO</fn></root>"""

        raw, transformed = self._transform(text, self.pipeline.AddPinFN())
        self.assertEqual(
            etree.tostring(transformed), b"""<root><fn><p>TEXTO</p></fn></root>"""
        )

    def test__add_p_in_fn_case_2(self):
        text = """<root><fn><p>TEXTO</p></fn></root>"""

        raw, transformed = self._transform(text, self.pipeline.AddPinFN())
        self.assertEqual(
            etree.tostring(transformed), b"""<root><fn><p>TEXTO</p></fn></root>"""
        )
