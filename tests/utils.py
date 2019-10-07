import os
from contextlib import contextmanager


@contextmanager
def environ(**kwargs):
    orig = dict()
    todel = []
    try:
        for k, newval in kwargs.items():
            if k in os.environ:
                orig[k] = os.environ[k]
            else:
                todel.append(k)
            os.environ[k] = newval
        yield
    finally:
        for k, oldval in orig.items():
            os.environ[k] = oldval
        for k in todel:
            del os.environ[k]


def AnyType(cls):
    class AnyType(cls):
        def __eq__(self, other):
            return isinstance(other, cls)

    return AnyType()


def build_xml(
    article_meta_children_xml,
    doi,
    journal_meta="",
    article_ids="",
    pub_date="",
    sps_version="sps-1.9"
):
    default_journal_meta = """
        <journal-id journal-id-type="publisher-id">acron</journal-id>
                <issn pub-type="epub">1234-5678</issn>
                <issn pub-type="ppub">0123-4567</issn>
        """
    default_article_ids = """
        <article-id pub-id-type="publisher-id">S0074-02761962000200006</article-id>
        <article-id pub-id-type="other">00006</article-id>
    """
    default_pubdate = """
        <pub-date date-type="collection">
                <year>2010</year>
            </pub-date>
    """
    doi_elem = ""
    if doi:
        doi_elem = '<article-id pub-id-type="doi">{}</article-id>'.format(doi)
    return """
        <article xmlns:xlink="http://www.w3.org/1999/xlink" specific-use="{sps_version}">
        <front>
        <journal-meta>
            {journal_meta}
        </journal-meta>
        <article-meta>
            {article_meta_doi}
            {article_ids}
            {article_meta_children_xml}
            {pub_date}
        </article-meta>
        </front>
        </article>
        """.format(
        article_meta_children_xml=article_meta_children_xml,
        article_meta_doi=doi_elem,
        article_ids=article_ids or default_article_ids,
        journal_meta=journal_meta or default_journal_meta,
        pub_date=pub_date or default_pubdate,
        sps_version=sps_version,
    )
