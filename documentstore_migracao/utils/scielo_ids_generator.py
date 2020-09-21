from math import log2, ceil
from uuid import UUID, uuid4


DIGIT_CHARS = "bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ3456789"
chars_map = {dig: idx for idx, dig in enumerate(DIGIT_CHARS)}


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


def issue_id(issn_id, year, volume=None, number=None, supplement=None):
    if volume and volume.isdigit() and int(volume) == 0:
        volume = None
    if number and number.isdigit() and int(number) == 0:
        number = None

    labels = ["issn_id", "year", "volume", "number", "supplement"]
    values = [issn_id, year, volume, number, supplement]

    data = dict([(label, value) for label, value in zip(labels, values)])

    labels = ["issn_id", "year"]
    _id = []
    for label in labels:
        value = data.get(label)
        if value:
            _id.append(value)

    labels = [("volume", "v"), ("number", "n"), ("supplement", "s")]
    for label, prefix in labels:
        value = data.get(label)
        if value:
            if value.isdigit():
                value = str(int(value))
            _id.append(prefix + value)

    return "-".join(_id)


def aops_bundle_id(issn_id):
    return issn_id + "-aop"