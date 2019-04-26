""" module to methods to string format """
import re
import unicodedata

from math import log2, ceil
from uuid import UUID, uuid4


DIGIT_CHARS = "bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ3456789"
chars_map = {dig: idx for idx, dig in enumerate(DIGIT_CHARS)}


def normalize(_string):

    return unicodedata.normalize("NFKD", " ".join(_string.split()))


def remove_spaces(_string):

    return re.sub(" +", " ", _string).strip()


def uuid2str(value):
    result = []
    unevaluated = value.int
    for unused in range(ceil(128 / log2(len(DIGIT_CHARS)))):
        unevaluated, remainder = divmod(unevaluated, len(DIGIT_CHARS))
        result.append(DIGIT_CHARS[remainder])
    return "".join(result)


def str2uuid(value):
    acc = 0
    mul = 1
    for digit in value:
        acc += chars_map[digit] * mul
        mul *= len(DIGIT_CHARS)
    return UUID(int=acc)


def generate_scielo_pid():
    """Funções para a geração e conversão do novo PID dos documentos do SciELO
    """
    return uuid2str(uuid4())
