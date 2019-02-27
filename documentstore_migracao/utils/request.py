import requests


def get(uri, **kwargs):

    r = requests.get(uri, **kwargs)
    r.raise_for_status()
    return r
