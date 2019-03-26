class ExtractError(Exception):
    """Erro do qual não pode ser recuperado durante uma extração
    de informações de uma base de dados"""

class EnvironmentError(Exception):
    """Erro do qual não pode ser recuperado durante a aquisição
    de informações do ambiente de execução. Informações as quais
    são necessárias para o funcionamento correto do software"""
