""" module to dicts function """


def merge(result, key, values):

    result.setdefault(key, {})
    for v_key, v_value in values.items():
        result[key].setdefault(v_key, type(v_value)())

        result[key][v_key] += v_value


def group(lst, n):
    """group([0,3,4,10,2,3], 2) => [(0,3), (4,10), (2,3)]

    Group a list into consecutive n-tuples. Incomplete tuples are
    discarded e.g.

    >>> group(range(10), 3)
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    """
    return zip(*[lst[i::n] for i in range(n)])
