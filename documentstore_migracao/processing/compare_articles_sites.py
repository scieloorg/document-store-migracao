import re
import json
import logging
import asyncio
from unidecode import unidecode
from bs4 import BeautifulSoup as soup

from documentstore_migracao import config

import aiohttp

LOGGER_FORMAT = u"%(asctime)s %(levelname)-5.5s %(message)s"
logger = logging.getLogger(__name__)


def normalize(text):
    """
    Normaliza o texto mantendo somente palavras e baixando a caixa.

    Exemplo o texto "Hello World!" deve retornar somente "hello world".

    Args:
        text: string, texto para normalização

    Returno:
        Retorno o texto normalizado mantendo momente palavras e espaços e em
        caixa baixa.
    """

    regex = re.compile(r"[^\w\s]")
    text = regex.sub(" ", unidecode(text).lower())
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def sim_jaccard(text1, text2):
    """
    Calcula a similaridade utilizando a técnica Jaccard

    Mais sobre essa técnica de similaridade pode ser encontrado em:

    https://en.wikipedia.org/wiki/Jaccard_index
    https://towardsdatascience.com/overview-of-text-similarity-metrics-3397c4601f50

    Args:
        text1: string, texto para comparação.
        text2: string, texto para comparação.
        convert_percentage: boolean, converte ou não para porcentagem.

    Returno:
        Retorna uma tupla (float, string) com o valor aritmético da similaridade
        em inteiro e em porcentagem.
    """

    set_text1 = set(text1.split())
    set_text2 = set(text2.split())

    intersection = set_text1.intersection(set_text2)

    union = set_text1.union(set_text2)
    try:
        sim = float(len(intersection)) / (len(union))
    except ZeroDivisionError as e:
        logger.error("Erro: %s.", e)
        return (0, '0.00%')

    return (sim, '{:.2%}'.format(sim))


def extract_body(html, html_tag, remove_tags=[]):
    """
    Extrai o corpo do texto e remove as marcações em HTML.

    Args:
        html: string, texto para comparação.
        html_tag: dictionary, dicionário os atributos para
        obter o trecho ``corpo``.
        remove_tags: list, contento as tags HTML que deve ser removidos da extração
        convert_percentage: boolean, converte ou não para porcentagem.

    Returno:
        Retorna o texto esperado da extração do HTML.
    """

    if not html:
        return ' '

    page = soup(html, 'html.parser')

    body = page.find('div', html_tag)

    if remove_tags:
        for rtag in remove_tags:
            for _t in body.find_all(rtag.get('tag_name'), rtag.get('atrib')):
                _t.extract()

    if body:
        ps = body.find_all('p')
    else:
        return ' '

    return ' '.join([ps[i].text for i in range(len(ps)) if ps[i].text])


def extract_back(html, html_tags, remove_tags=[], remove_texts=[]):
    """
    Extrai o corpo do texto e remove as marcações em HTML.

    Args:
        html: string, texto para comparação.
        html_tag: dictionary, dicionário os atributos para
        obter o trecho ``corpo``.
        remove_tags: list, contento as tags HTML que deve ser removidos da extração
        remove_texts: list, contento os textos que deve ser removidos da extração

    Returno:
        Retorna o texto esperado da extração do HTML.
    """

    if not html:
        return ' '

    page = soup(html, 'html.parser')

    for html_tag in html_tags:
        back = page.find('div', html_tag)

        if back:
            break

    if not back:
        return ' '

    if remove_tags:
        for rtag in remove_tags:
            for _t in back.find_all(rtag.get('tag_name'), rtag.get('atrib')):
                _t.extract()

    text = back.text

    if remove_texts:
        for rtext in remove_texts:
            text = text.replace(rtext, "")

    return text


def dump_jsonl(filename, lines):
    """Escreve resultado em um arquivo caminho determinado.

    Args:
        lines: Lista de linhas contento sequência de caracteres.
        filename: Caminho para o arquivo.
    Retornos:
        Não há retorno

    Exceções:
        Não lança exceções.
    """
    with open(filename, 'a') as fp:
        for line in lines:
            fp.write(line)
            fp.write("\n")


async def fetch_article(session, pid, instance_url):

    logger.info("Obtendo artigo com a url: %s" % instance_url.format(pid))

    try:
        async with session.get(instance_url.format(pid)) as response:
            if response.status != 200:
                logger.error(
                    "Article not found '%s' in instance '%s'",
                    pid,
                    instance_url.format(pid),
                )
                return None

            return await response.content.read()
    except aiohttp.ClientResponseError as e:
        logger.error("Erro: %s.", e)


async def fetch_articles(session, pid, output_filepath):
    comp_list = []
    comp_data = {}

    for inst in config.get('SITE_INSTANCES'):
        html = await fetch_article(session, pid, inst.get('url'))
        comp_data["%s_body" % inst.get('name')] = extract_body(html, inst.get('html_body'), inst.get('remove_body_tags'))
        comp_data["%s_back" % inst.get('name')] = extract_back(html, inst.get('html_back'), inst.get('remove_back_tags'), inst.get('remove_back_texts'))
        comp_data["url_%s" % inst.get('name')] = inst.get('url').format(pid)

    sim, percent = sim_jaccard(normalize(comp_data['classic_body']), normalize(comp_data['new_body']))
    comp_data['similarity_body'] = percent

    sim, percent = sim_jaccard(normalize(comp_data['classic_back']), normalize(comp_data['new_back']))
    comp_data['similarity_back'] = percent

    comp_data['pid_v2'] = pid
    comp_data['similarity_technique'] = 'jaccard'

    comp_list.append(json.dumps(comp_data))

    dump_jsonl(output_filepath, comp_list)


async def bound_fetch(fetcher, session, pid, sem, output_filepath):
    """
    Responsável por envolver a função de obter os artigos por um semáforo.

    Args:
        fetcher: callable, função responsável por obter os dados da URL
        session: http session object(aiohttp), sessão http
        pid: string, PID identificador do para URL
        sem: semaphore object, um objeto semáforo para envolver a função.
    """

    async with sem:
        await fetcher(session, pid, output_filepath)


async def main(
    input_filepath="pids.txt",
    output_filepath="similarity.jsonl",
    log_level="debug",
    ssl=False,
    semaphore_value=20,
):
    """
    Compara o conteúdo do artigo entre o site novo e o site clássico - Compare articles

    Realiza a leitura de um arquivo contento uma lista de PIDs (Publisher Identifier) versão 2.

    Exemplo:

    S0044-59672016000300233

    O resultado final desse comparador é um arquivo em formato `jsonl` com a seguinte estrutura:

        {
         'classic_body': 'Introduction One of the major current public health problems remains sepsis, which persists with hig',
         'new_body': 'One of the major current public health problems remains sepsis, which persists with high hospital mo',
         'url_classic': 'http://www.scielo.br/scielo.php?script=sci_arttext&pid=S0102-86502017000300175',
         'url_new': 'http://new.scielo.br/article/S0102-86502017000300175',
         'similarity_body': '72.22%',
         'similarity_back': '100.00%',
         'pid_v2': 'S0102-86502017000300175',
         'similarity_technique': 'jaccard'
        }

    Args:
        input_filepath: string, caminho para o arquivo contendo os PID V2 como conteúdo ``Linha por linha``, padrão: pids.txt
        output_filepath: string, Caminho para o arquivo de saída no formato ``jsonl``, padrão: similarity.jsonl
        log_level: string, defini o nível de log de excecução. padrão: debug.
        ssl: boolean, liga e desliga a validação de certificado ssl, padrão: False
        semaphore_value: int, valor inicial do semáfaro padrão: 20
    """
    logging.basicConfig(format=LOGGER_FORMAT, level=getattr(logging, log_level.upper()))

    tasks = []
    sem = asyncio.Semaphore(semaphore_value)

    with open(input_filepath) as f:
        logger.info("Realizando a leitura do arquivo com os PIDs V2")
        pids = f.readlines()

    try:
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:

            for pid in pids:
                tasks.append(bound_fetch(fetch_articles, session, pid.strip(), sem, output_filepath))

            if tasks:
                logger.info("Quantidade de tarefas registradas: %s", len(tasks))
                responses = asyncio.gather(*tasks)
                await responses

    except Exception as e:
        logger.error("Erro: %s.", e)
        logger.exception(e)

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(main())
