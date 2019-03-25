from pyramid.config import Configurator
from pyramid.events import BeforeRender
from .utils.subscribers import add_renderer_globals


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_subscriber(add_renderer_globals, BeforeRender)
    config.include("pyramid_jinja2")
    config.add_static_view(
        name="static",
        path="documentstore_migracao:webserver/static",
        cache_max_age=3600,
    )
    config.add_route("list_converted_xml", "/")
    config.add_route("render_html_converted", "/html/:file_xml")
    config.scan()
    return config.make_wsgi_app()
