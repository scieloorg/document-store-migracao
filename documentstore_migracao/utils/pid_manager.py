# Coding: utf-8

"""
Módulo responsável por obter dados de um banco de dados com a seguinte estrutura:

    CREATE TABLE "pid_versions" (
        "id"    INTEGER,
        "v2"    VARCHAR(23),
        "v3"    VARCHAR(255),
        PRIMARY KEY("id" AUTOINCREMENT),
        UNIQUE("v2","v3")
    );

Reparem que existe uma unicidade entre as colunas v2 e v3.
"""


def get_conn(engine):
    """
    Cria um conexão com o banco de dados.

    param: engine é uma instância de sqlachemy:create_engine
    """
    return engine.connect(close_with_result=True)


def check_pid_v3_by_v2(engine, pid_v2):
    """
    Verifica a existência do pid na versão v3.

    param: engine é uma instância de sqlachemy:create_engine

    param: pid_v2 é uma string Ex: S0006-87051956000100002
    """
    conn = get_conn(engine)

    sqrs = conn.execute("SELECT * FROM pid_versions WHERE v2='%s'" % pid_v2)

    row = sqrs.first()

    if not row:
        return False
    else:
        return bool(row[2])


def get_pid_v3_by_v2(engine, pid_v2):
    """
    Obtém o pid da versão pid_v2.

    param: engine é uma instância de sqlachemy:create_engine

    param: pid_v2 é uma string Ex: S0006-87051956000100002
    """
    conn = get_conn(engine)

    sqrs = conn.execute("SELECT * FROM pid_versions WHERE v2='%s'" % pid_v2)

    return sqrs.first()[2]


def create_pid(engine, pid_v2, pid_v3):
    """
    Adiciona o pid_v2 e pid_v3 no tabela de pids.

    param: pid_v2 é uma string Ex: S0006-87051956000100002

    param: pid_v3 é uma string Ex: jNRgVj3SpLy8ML8Hy3kQ38R
    """
    conn = get_conn(engine)

    conn.execute("INSERT INTO pid_versions (v2, v3) VALUES ('%s', '%s')" % (pid_v2, pid_v3))
