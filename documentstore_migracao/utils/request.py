import requests
from requests.exceptions import HTTPError


class HTTPGetError(Exception):
    pass


def get(uri, **kwargs):

    r = requests.get(uri, **kwargs)
    try:
        r.raise_for_status()
    except HTTPError as exc:
        raise HTTPGetError(str(exc))
    else:
        return r
