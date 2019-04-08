import os
from paginate import Page
from pyramid.view import view_config
from pyramid.response import Response
from packtools import HTMLGenerator, XML, catalogs

from lxml import etree
from documentstore_migracao.utils import files
from documentstore_migracao import config


@view_config(
    route_name="list_converted_xml", renderer="templates/list_converted_xml.jinja2"
)
def list_converted_xml_view(request):
    list_files_xmls = files.xml_files_list(config.get("CONVERSION_PATH"))
    list_files_xmls += files.xml_files_list(config.get("VALID_XML_PATH"))
    xmls = Page(
        list_files_xmls,
        page=int(request.params.get("page", 1)),
        items_per_page=20,
        item_count=len(list_files_xmls),
    )
    return {"xmls": xmls, "page_title": "Lista de XMLS Convertidos"}


@view_config(route_name="render_html_converted")
def render_html_converted_view(request):

    file_xml_path = os.path.join(
        config.get("CONVERSION_PATH"), request.matchdict["file_xml"]
    )

    parsed_xml = XML(file_xml_path, no_network=False)
    html_generator = HTMLGenerator.parse(
        parsed_xml,
        valid_only=False,
        css="/static/css/scielo-article.css",
        print_css="/static/css/scielo-bundle-print.css",
        js="/static/js/scielo-article-min.js",
    )

    html = html_generator.generate(request.matchdict["language"])

    return Response(
        etree.tostring(
            html,
            doctype=u"<!DOCTYPE html>",
            pretty_print=True,
            encoding="utf-8",
            method="html",
        ).decode("utf-8")
    )
