""" module to dicts function """
from itertools import zip_longest


def merge(result, key, values):

    result.setdefault(key, {})
    for v_key, v_value in values.items():
        result[key].setdefault(v_key, type(v_value)())
        try:
            result[key][v_key] += v_value
        except TypeError:
            result[key][v_key] = v_value


def group(lst, n):
    """group([0,3,4,10,2,3], 2) => [(0,3), (4,10), (2,3)]

    Group a list into consecutive n-tuples. Incomplete tuples are
    discarded e.g.

    >>> group(range(10), 3)
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    """
    return zip(*[lst[i::n] for i in range(n)])


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)] * n, fillvalue=padvalue)
