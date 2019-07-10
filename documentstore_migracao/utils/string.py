""" module to methods to string format """

DIGIT_CHARS = "bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ3456789"
chars_map = {dig: idx for idx, dig in enumerate(DIGIT_CHARS)}


def normalize_spaces(_string):
    return " ".join(_string.split())
