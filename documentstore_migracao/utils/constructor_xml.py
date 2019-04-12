import logging
import plumber
import itertools

from lxml import etree
from copy import deepcopy
from documentstore_migracao.utils import string


logger = logging.getLogger(__name__)


class ConstructorXMLPipeline(object):
    def __init__(self):
        self._ppl = plumber.Pipeline(self.SetupPipe(), self.CreatePidPipe())

    class SetupPipe(plumber.Pipe):
        def transform(self, data):
            xml = deepcopy(data)
            return data, xml

    class CreatePidPipe(plumber.Pipe):
        PATHS = [".//article-meta", ".//front-stub"]

        def _append_node(self, parent, new_node):

            node = parent.findall(".//article-id")
            if node:
                parent.insert(parent.index(node[0]), new_node)
            else:
                parent.append(new_node)

        def transform(self, data):
            raw, xml = data

            iterators = [xml.iterfind(path) for path in self.PATHS]
            for article in itertools.chain(*iterators):

                node = article.findall(".//article-id[@pub-id-type='scielo-id']")
                if not node:
                    articleId = etree.Element("article-id")
                    articleId.set("pub-id-type", "scielo-id")
                    articleId.text = string.generate_scielo_pid()
                    self._append_node(article, articleId)

            return data

    def deploy(self, raw):
        transformed_data = self._ppl.run(raw, rewrap=True)
        return next(transformed_data)
