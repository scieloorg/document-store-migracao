import os

from mako.template import Template
from documentstore_migracao import config
from documentstore_migracao.utils import dicts


def render_pagination(items):

    links = items.link_map(
        "$link_first $link_previous ~4~ $link_next $link_last", url="/?page=$page"
    )
    template = Template(
        filename=os.path.join(
            config.BASE_PATH,
            "documentstore_migracao/webserver/templates/paginator.mako",
        )
    )
    result = template.render(**{"items": items, "links": links})
    return result


def parse_name_file(filename):

    fname, languages, fext = filename.split(".")
    return {"name": "%s.%s" % (fname, fext), "languages": languages.split("-")}


def grouper_items(items):

    return dicts.grouper(len(items) // 2, items)
