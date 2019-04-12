""" module to methods to string format """
import os
import re
import logging
import unicodedata
import string
from datetime import datetime
from math import log2, ceil
from uuid import UUID, uuid4


DIGIT_CHARS = "bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ3456789"
chars_map = {dig: idx for idx, dig in enumerate(DIGIT_CHARS)}


def normalize(string):

    return unicodedata.normalize("NFKD", " ".join(string.split()))


def remove_spaces(string):

    return re.sub(" +", " ", string).strip()


def extract_filename_ext_by_path(inputFilepath):

    filename_w_ext = os.path.basename(inputFilepath)
    c_filename, file_extension = os.path.splitext(filename_w_ext)
    filename, _ = os.path.splitext(c_filename)
    return filename, file_extension


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
