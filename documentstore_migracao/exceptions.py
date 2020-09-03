class ExtractError(Exception):
    """Erro do qual não pode ser recuperado durante uma extração
    de informações de uma base de dados"""


class FetchEnvVariableError(Exception):
    """Erro do qual não pode ser recuperado durante a aquisição
    de informações do ambiente de execução. Informações as quais
    são necessárias para o funcionamento correto do software"""


class XMLError(Exception):
    """ Represents errors that would block HTMLGenerator instance from
    being created.
    """


class NoJournalInWebsiteError(Exception):
    """Não há periódicos no site para migração dos logos. É necessário que a migração
    dos periódicos seja feita antes da migração dos logos.
    """


class RollbackError(Exception):
    """ Rollback command error."""
