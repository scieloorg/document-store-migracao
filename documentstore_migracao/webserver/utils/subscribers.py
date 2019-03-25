from . import helpers


def add_renderer_globals(event):
    """ add helpers """
    event["h"] = helpers
