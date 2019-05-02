""" module to methods to string format """
import re
import unicodedata


DIGIT_CHARS = "bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ3456789"
chars_map = {dig: idx for idx, dig in enumerate(DIGIT_CHARS)}


def normalize(_string):

    return unicodedata.normalize("NFKD", " ".join(_string.split()))


def remove_spaces(_string):

    return re.sub(" +", " ", _string).strip()
