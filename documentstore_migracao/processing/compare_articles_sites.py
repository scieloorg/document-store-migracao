import re
import json
import logging
import asyncio
from unidecode import unidecode
from bs4 import BeautifulSoup as soup

from documentstore_migracao import config

import aiohttp
from tenacity import retry, wait_exponential

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
        print(sim)
    except ZeroDivisionError as e:
        return (0, "0.00%")

    return (sim, "{:.2%}".format(sim))


def extract(
    html,
    html_tag,
    remove_tags=[],
    remove_texts=[],
    compare_tags=["p", "li", "b", "i", "em", "sup", "br", "div"],
):
    """
    Extrai o corpo do texto e remove as marcações em HTML.

    Args:
        html: string, texto para comparação.
        html_tag: dictionary, dicionário os atributos para
        obter o trecho ``corpo``.
        remove_tags: list, contento as tags HTML que deve ser removidos da extração
        convert_percentage: boolean, converte ou não para porcentagem.
        compare_tags: list, lista de tags que será avaliado.

    Returno:
        Retorna o texto esperado da extração do HTML.
    """

    if not html:
        return ""

    page = soup(html, "html.parser")

    body = page.find(html_tag.get("tag_name"), html_tag.get("atrib"))

    if not body:
        return ""

    if remove_tags:
        for rtag in remove_tags:
            for _t in body.find_all(rtag.get("tag_name"), rtag.get("atrib")):
                _t.extract()

    text = ""
    for tag in compare_tags:
        inter_tag = body.find_all(tag)
        text += " ".join(
            [
                inter_tag[i].get_text()
                for i in range(len(inter_tag))
                if inter_tag[i].get_text().strip()
            ]
        )

    if remove_texts:
        for rtext in remove_texts:
            text = text.replace(rtext, "")

    return text.strip().lower()


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
    with open(filename, "a") as fp:
        for line in lines:
            fp.write(line)
            fp.write("\n")


@retry(wait=wait_exponential(multiplier=1, min=4, max=20))
async def fetch_article(session, pid, url):
    """
    Obtém um artigo com acesso HTTP.

    Retentativas: Aguarde 2 ^ x * 1 segundo entre cada nova tentativa,
                  começando com 4 segundos, depois até 10 segundos e 10
                  segundos depois

    Args:
        session: http session object(aiohttp), sessão http
        pid: pid do artigo.
        url: Endereço para URL contento uma posição de interpolação.
        output_filepath: Caminho do arquivo de saída.
    Retornos:
        Retorno o corpo da resposta HTTP.
    Exceções:
        Trata a exceções de conexão com o endpoint HTTP.
    """
    logger.info("Obtendo artigo com a url: %s" % url.format(pid))

    try:
        async with session.get(url.format(pid)) as response:
            if response.status != 200:
                logger.error(
                    "Artigo não encontrado '%s' na instância '%s'",
                    pid,
                    url.format(pid),
                )
                return None

            return await response.content.read()
    except Exception as e:
        logger.error("Erro ao obter o artigo, pid: %s, retentando...., erro:%s" % (pid, e))


async def fetch_articles(session, pid, cut_off_mark, output_filepath):
    """
    Obtém os artigos e gera um dicionário contendo as informação necessária para
    saída em JSON.

    A variável comp_data terá a seguinte estrutura:

        {
         'classic': 'Introduction One of the major current public health problems remains sepsis, which persists with hig',
         'new': 'One of the major current public health problems remains sepsis, which persists with high hospital mo',
         'url_classic': 'http://www.scielo.br/scielo.php?script=sci_arttext&pid=S0102-86502017000300175',
         'url_new': 'http://new.scielo.br/article/S0102-86502017000300175',
         'similarity': '72.22%',
         'pid_v2': 'S0102-86502017000300175',
         'similarity_technique': 'jaccard',
         'cut_off_mark': 90,
         'found_text_classic': true,
         'found_text_new': false
        }

    Args:
        session: http session object(aiohttp), sessão http
        pid: pid do artigo.
        cut_off_mark: Régua de similiridade.
        output_filepath: Caminho do arquivo de saída.
    Retornos:
        Não há retorno
    Exceções:
        Não lança exceções.
    """
    comp_list = []
    comp_data = {}

    for inst in config.get("SITE_INSTANCES"):
        html = await fetch_article(session, pid, inst.get("url"))
        comp_data["%s" % inst.get("name")] = extract(
            html,
            inst.get("html"),
            inst.get("remove_tags"),
            inst.get("remove_texts"),
            inst.get("compare_tags"),
        )
        comp_data["url_%s" % inst.get("name")] = inst.get("url").format(pid)

    sim, percent = sim_jaccard(
        normalize(comp_data["classic"]), normalize(comp_data["new"])
    )
    comp_data["similarity"] = percent

    comp_data["found_text_classic"] = bool(comp_data["classic"])
    comp_data["found_text_new"] = bool(comp_data["new"])

    if int(sim * 100) > cut_off_mark:
        del comp_data["classic"]
        del comp_data["new"]

    comp_data["pid_v2"] = pid
    comp_data["similarity_technique"] = "jaccard"
    comp_data["cut_off_mark"] = cut_off_mark

    comp_list.append(json.dumps(comp_data))

    dump_jsonl(output_filepath, comp_list)


async def bound_fetch(fetcher, session, pid, sem, cut_off_mark, output_filepath):
    """
    Responsável por envolver a função de obter os artigos por um semáforo.

    Args:
        fetcher: callable, função responsável por obter os dados da URL
        session: http session object(aiohttp), sessão http
        pid: string, PID identificador do para URL
        sem: semaphore object, um objeto semáforo para envolver a função.
        cut_off_mark: Régua de similiridade.
    """

    async with sem:
        await fetcher(session, pid, cut_off_mark, output_filepath)


async def main(
    input_filepath="pids.txt",
    output_filepath="similarity.jsonl",
    log_level="debug",
    ssl=False,
    semaphore_value=20,
    cut_off_mark=90,
):
    """
    Compara o conteúdo do artigo entre o site novo e o site clássico - Compare articles

    Realiza a leitura de um arquivo contento uma lista de PIDs (Publisher Identifier) versão 2.

    Exemplo:

    S0044-59672016000300233

    O resultado final desse comparador é um arquivo em formato `jsonl` com a seguinte estrutura:

        {
         'classic': 'Introduction One of the major current public health problems remains sepsis, which persists with hig',
         'new': 'One of the major current public health problems remains sepsis, which persists with high hospital mo',
         'url_classic': 'http://www.scielo.br/scielo.php?script=sci_arttext&pid=S0102-86502017000300175',
         'url_new': 'http://new.scielo.br/article/S0102-86502017000300175',
         'similarity': '72.22%',
         'pid_v2': 'S0102-86502017000300175',
         'similarity_technique': 'jaccard',
         'cut_off_mark': 90,
         'found_text_classic': true,
         'found_text_new': false
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
                tasks.append(
                    bound_fetch(
                        fetch_articles,
                        session,
                        pid.strip(),
                        sem,
                        cut_off_mark,
                        output_filepath,
                    )
                )

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
