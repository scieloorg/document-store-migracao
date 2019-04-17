""" module to methods to string format """
import re
import unicodedata


def normalize(string):

    return unicodedata.normalize("NFKD", " ".join(string.split()))


def remove_spaces(string):

    return re.sub(" +", " ", string).strip()
