from math import log2, ceil
from uuid import UUID, uuid4


DIGIT_CHARS = "bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ3456789"
chars_map = {dig: idx for idx, dig in enumerate(DIGIT_CHARS)}


class NotAnIssueError(Exception):
    pass


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
    """
    Retorna o `ID` de um `issue`
    Args:
        issn_id (str): ISSN usado como ID
        year (str): ano, 4 dígitos
        volume (None or str): volume se aplicável
        number (None or str): número se aplicável
        supplement (None or str): suplemento se aplicável

        Nota: se `number` é igual a `ahead`, equivale a `None`
    Returns:
        {ISSN_ID}[-{YEAR}][-v{VOLUME}][-n{NUMBER}][-s{SUPPL}] para fascículos
        {ISSN_ID}-aop para `ahead of print`
    """
    volume, number = normalize_volume_and_number(volume, number)
    if volume is None and number is None:
        raise NotAnIssueError(
            "Issue must have at least volume or number")

    prefixes = ["", "", "v", "n", "s"]
    values = [issn_id, year, volume, number, supplement]

    _id = []
    for value, prefix in zip(values, prefixes):
        if value:
            if value.isdigit():
                value = str(int(value))
            _id.append(prefix + value)

    return "-".join(_id)


def aops_bundle_id(issn_id):
    return issn_id + "-aop"


def any_bundle_id(issn_id, year, volume=None, number=None, supplement=None):
    """
    Retorna o `ID` de um `bundle` (aop ou fascículo)
    Args:
        issn_id (str): ISSN usado como ID
        year (str): ano, 4 dígitos
        volume (None or str): volume se aplicável
        number (None or str): número se aplicável
        supplement (None or str): suplemento se aplicável

        Nota: se `number` é igual a `ahead`, equivale a `None`
    Returns:
        {ISSN_ID}[-{YEAR}][-v{VOLUME}][-n{NUMBER}][-s{SUPPL}] para fascículos
        {ISSN_ID}-aop para `ahead of print`
    """
    try:
        return issue_id(issn_id, year, volume, number, supplement)
    except NotAnIssueError:
        return aops_bundle_id(issn_id)


def normalize_volume_and_number(volume, number):
    """
    Padroniza os valores de `volume` e `number`
    Args:
        volume (None or str): volume se aplicável
        number (None or str): número se aplicável

        Notas:
        - se `number` é igual a `ahead`, equivale a `None`
        - se `00`, equivale a `None`
        - se `01`, equivale a `1`
        - se `""`, equivale a `None`
    Returns:
        tuple (str or None, str or None)
    """
    if number == "ahead":
        return None, None

    if volume and volume.isdigit():
        value = int(volume)
        volume = str(value) if value > 0 else None
    if number and number.isdigit():
        value = int(number)
        number = str(value) if value > 0 else None

    volume = volume or None
    number = number or None

    return volume, number
