# Document Store (Kernel) - Migração


[![Build Status](https://travis-ci.org/scieloorg/document-store-migracao.svg?branch=master)](https://travis-ci.org/scieloorg/document-store-migracao)

[![codecov](https://codecov.io/gh/scieloorg/document-store-migracao/branch/master/graph/badge.svg)](https://codecov.io/gh/scieloorg/document-store-migracao)


## Migração ISIS

Esta ferramenta possui a capacidade de migrar dados de bases ISIS (title e issue) em formato MST para o formato aceito pelo **Kernel**. A utilização de ferramentas externas se fez necessário com o intuito de garantir a máxima integralidade de dados entre as duas bases.

#### Dependências
Antes de executar a ferramenta de migração observe se as seguintes dependências estão presentes:

- Java `>= 1.8`
- [Jython](http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.5.3/jython-installer-2.5.3.jar) `== 2.5.x`
- Python `== 3.6.x`

#### Configuração

Para o devido funcionamento desta ferramenta é necessário que algumas configurações sejam feitas, siga as seguintes instruções:

1. Instale o Java.
2. Instale o Jython.
3. Instale o Python.
4. Instale os utilitários de migração

```shell
python setup.py install
```

Este comando possibilitará que os utilitários de migração estejam disponíveis no seu `path` de execução.


#### Execução da fase ISIS

Após realizar a configurações descritas logo acima o sistema está apto para executar as fases de extração e carga na base de dados.

##### Extração de bases

```shell
migrate_isis extract /home/user/bases/title/title.mst --output /home/user/jsons/title.json
```
O comando acima executa a extração do arquivo `/home/user/bases/title/title.mst` e salva o seu resultado na pasta `/home/user/jsons/title.json`.

Para visualizar todas as opções e a ajuda digite:
```shell
migrate_isis --help
```

## Getting Started Pyramid
---------------

- cd <directory containing this file>

- $VENV/bin/pip install -e .

- $VENV/bin/pserve development.ini
