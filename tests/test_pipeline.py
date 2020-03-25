import unittest
import random
import string
import tempfile
import os

from lxml import etree

from documentstore_migracao.processing.pipeline import update_articles_mixed_citations


class TestUpdateMixedCitations(unittest.TestCase):
    def setUp(self):
        self.random_source_folder = "".join(
            random.choice(string.ascii_uppercase) for _ in range(10)
        )

        os.environ["PARAGRAPH_CACHE_PATH"] = "tests/fixtures/paragraphs"

        _, self.sample_xml = tempfile.mkstemp()

        with open(self.sample_xml, "w") as f:
            f.write(
                """<?xml version='1.0' encoding='utf-8'?>
            <!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd">
            <article xmlns:xlink="http://www.w3.org/1999/xlink" specific-use="sps-1.9" dtd-version="1.1" xml:lang="en" article-type="research-article">
                <front>
                    <article-meta><article-id pub-id-type="publisher-id" specific-use="scielo-v2">S1984-46702010000500003</article-id></article-meta>
                </front>
                <back>
                    <ref-list>
                        <ref id="B1">
                        </ref>
                        <ref id="B2">
                            <mixed-citation>Second mixed citation</mixed-citation>
                        </ref>
                    </ref-list>
                </back>
            </article>"""
            )

    def tearDown(self):
        os.unlink(self.sample_xml)

    def test_should_require_an_existent_source_folder(self):
        with self.assertRaises(FileNotFoundError):
            update_articles_mixed_citations(source=self.random_source_folder)

    def test_should_update_mixed_citation(self):
        artiles_situations = (
            (self.sample_xml, lambda _, **k: k, self.assertNotIn),
            (self.sample_xml, update_articles_mixed_citations, self.assertIn),
        )

        for xml, func, assertCheckIn in artiles_situations:
            with self.subTest(assertCheckIn=assertCheckIn):
                func(xml, disable_bar=True)
                tree = etree.parse(xml)

                assertCheckIn(
                    b"<mixed-citation>with two new genera. <bold>Entomological "
                    b"News 84</bold>: 143-146.</mixed-citation>",
                    etree.tostring(tree),
                )

    def test_should_override_existents_mixed_citations(self):
        update_articles_mixed_citations(
            self.sample_xml, override=True, disable_bar=True
        )

        tree = etree.parse(self.sample_xml)
        self.assertNotIn(b"Second mixed citation", etree.tostring(tree))
        self.assertIn(
            b"<mixed-citation>VAN VELLER, M.G.P. &amp; D.J. "
            b"BROOKS. 2001. When simplicity is not parsimonious: a priori and "
            b"a posteriori methods in historical biogeography. <bold>Journal "
            b"of Biogeography 28</bold>: 1-11.</mixed-citation>",
            etree.tostring(tree),
        )
