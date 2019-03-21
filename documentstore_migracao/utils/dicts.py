""" module to dicts function """


def merge(result, key, values):

    result.setdefault(key, {})
    for v_key, v_value in values.items():
        result[key].setdefault(v_key, type(v_value)())

        result[key][v_key] += v_value
