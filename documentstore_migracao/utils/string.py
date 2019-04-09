""" module to methods to string format """
import os
import re
import logging
import unicodedata


def normalize(string):

    return unicodedata.normalize("NFKD", " ".join(string.split()))


def remove_spaces(string):

    return re.sub(" +", " ", string).strip()


def extract_filename_ext_by_path(inputFilepath):

    filename_w_ext = os.path.basename(inputFilepath)
    c_filename, file_extension = os.path.splitext(filename_w_ext)
    filename, _ = os.path.splitext(c_filename)
    return filename, file_extension
