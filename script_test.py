import unicodedata
from lxml import etree
import html.parser


def str2objXML(string):
    parser = html.parser.HTMLParser()

    txt = parser.unescape(" ".join(string.split()))
    # print(txt)

    return etree.fromstring("<div>%s</div>" % (txt))


txt = "<div id='1'> teste <p id='2'> teste 2</p><p id='3'> teste 3</p></div>"
html = str2objXML(txt)


media = []
# IMG
nodes = html.findall(".//div")
import pdb

pdb.set_trace()

for index, node in enumerate(nodes):
    node.tag = "sec"
    node.attrib = {}

    print(index)

print(etree.tostring(html, encoding="utf-8"))
