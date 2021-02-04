"""
# comando para obter colecao article de site scielo
mongoexport --host=mongohost --port=mongoport --db=opacdb -u mongouser -p mongopassword -c article -o opac_documents.json

# comando para obter colecao document de kernel
mongoexport --host=mongohost --port=mongoport --db=kerneldb -u mongouser -p mongopassword -c document -o kernel_documents.json

"""
import os
import argparse
import json
import re
import csv
import logging

from scripts.async_requests import simultaneous_requests, seq_requests


logging.basicConfig(filename='app.log', format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)


def read_file(file_path):
    logging.debug("Reading %s" % file_path)

    with open(file_path) as fp:
        c = fp.read()
    return c


def read_file_rows(file_path):
    return read_file(file_path).splitlines()


def makedir(dirname):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


def makedir_for_file(file_path):
    makedir(os.path.dirname(file_path))


def write_file(file_path, content):
    logging.debug("Writing %s" % file_path)
    makedir_for_file(file_path)
    with open(file_path, "w") as fp:
        fp.write(content)


def write_file_rows(file_path, rows):
    makedir_for_file(file_path)
    return write_file(file_path, "\n".join(rows) + "\n")


def write_csv_file(file_path, rows):
    logging.debug("Writing %s" % file_path)
    makedir_for_file(file_path)
    rows = list(rows)
    fieldnames = rows[0].keys()
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def extract_pids_from_website(content):
    logging.debug("Extract PIDs from Website")
    if not '"scielo_pids":' in content:
        return []
    rows = []
    for row in content.split('"scielo_pids":')[1:]:
        row = row[:row.find("}")+1]
        rows.append(json.loads(row))
    logging.debug("Found %i" % len(rows))
    return rows


def indexed_by_pid_type(rows):
    indexed_by_v3 = {}
    indexed_by_v2 = {}
    for row in rows:
        try:
            v2 = row["v2"]
            v3 = row["v3"]
        except (KeyError, TypeError):
            continue
        indexed_by_v3[v3] = v2
        indexed_by_v2[v2] = v3
    return indexed_by_v2, indexed_by_v3


def extract_pids_from_kernel(content):
    logging.debug("Extract PIDs from Kernel")
    pids_v3 = []
    found = re.findall(r'\"_id\":\"\w{23,23}\"', content)
    for item in found:
        f = re.findall(r'\w{23,23}', item)
        pids_v3.append(f[0])
    logging.debug("Found %i" % len(pids_v3))
    return pids_v3


def get_kernel_front_uri(pid_v3):
    return f"https://kernel.scielo.br/documents/{pid_v3}/front"


def get_pid_from_kernel_front_uri(uri):
    return uri.split("/")[-2]

def json_file_path(pid_v3, path):
    return os.path.join(path, pid_v3 + ".json")


def get_kernel_data(raw_data):
    try:
        doc = json.loads(raw_data)
    except Exception as e:
        logging.exception(e)
    else:
        try:
            v2 = doc["article_meta"][0]["scielo_pid_v2"][0]
        except IndexError:
            v2 = None
        try:
            v3 = doc["article_meta"][0]["scielo_pid_v3"][0]
        except IndexError:
            v3 = None
        return {
            "v2": v2,
            "v3": v3,
        }


def get_kernel_document_front_uri_list(pid_v3_list):
    return [
        get_kernel_front_uri(pid_v3)
        for pid_v3 in pid_v3_list
    ]


def get_kernel_documents_responses_data(responses):
    responses_ = {}
    for resp in responses:
        try:
            uri = resp.uri
        except AttributeError:
            uri = resp.url
        responses_[uri] = resp.text or {"status": resp.status_code, "uri": uri}
    return responses_


# def __get_kernel_documents_responses_data(responses):
#     responses_ = {}
#     failures = {}
#     for resp in responses:
#         try:
#             uri = resp.uri
#         except AttributeError:
#             uri = resp.url
#         try:
#             json.loads(resp.text)
#         except Exception as e:
#             logging.exception(
#                 "Get kernel docs responses data: %s %s \n%s" %
#                 (resp.status_code, resp.text, e))
#             failures[uri] = resp.status_code
#         else:
#             responses_[uri] = resp.text
#     return responses_, failures


def do_requests(uri_items):
    t = len(uri_items)
    logging.debug("Execute %i requests" % t)
    responses = seq_requests(uri_items, body=True)
    # responses = simultaneous_requests(uri_items, body=True)
    return get_kernel_documents_responses_data(responses)


class Kernel:

    def __init__(self, pids_v3, website, cache_path):
        self.pids_v3 = pids_v3
        self.website = website
        self.cache_path = cache_path
        self._get_pid_v2_items()

    def is_registered(self, pid):
        return self.website.is_registered(pid) or bool(self.indexed_by_v2.get(pid) or self.indexed_by_v3.get(pid))

    @property
    def not_published_v3_items(self):
        return [
            v3
            for v3 in self.pids_v3
            if not self.website.is_registered(v3)
        ]

    def _get_cached_data(self, pid_v3_items):
        cached = {}
        for pid_v3 in pid_v3_items:
            file_path = json_file_path(pid_v3, self.cache_path)
            try:
                raw_data = read_file(file_path)
                data = get_kernel_data(raw_data)
            except (FileNotFoundError, Exception) as e:
                logging.exception(e)
            else:
                cached[pid_v3] = data
        logging.info("Cached: %i" % len(cached))
        return cached

    def _get_remote_data(self, pid_v3_items):
        if not pid_v3_items:
            return  {}

        uri_items = get_kernel_document_front_uri_list(pid_v3_items)
        responses = do_requests(uri_items)

        remote = {}
        for uri, raw_data in responses.items():
            pid_v3 = get_pid_from_kernel_front_uri(uri)

            file_path = json_file_path(pid_v3, self.cache_path)
            write_file(file_path, json.dumps(raw_data))

            remote[pid_v3] = get_kernel_data(raw_data)
        logging.info("Remote: %i" % len(remote))
        return remote

    def _get_pid_v2_items(self):
        n = len(self.not_published_v3_items)
        logging.debug("Get PID v2 for %i Kernel documents" % n)

        # get cached data
        cached = self._get_cached_data(self.not_published_v3_items)

        # get remote data, if apply
        pid_v3_items_not_cached = set(self.not_published_v3_items) - set(cached.keys())
        remote_data = self._get_remote_data(pid_v3_items_not_cached)

        t = len(cached) + len(remote_data)
        logging.debug("Get %i documents/%i pids" % (t, n))
        if t != n:
            not_found = set(self.not_published_v3_items) - set(cached.keys()) - set(remote_data.keys())
            logging.error(
                "%i failures. Documents not found: %s\n" % (n - t, "\n".join(not_found)))

        self.indexed_by_v2, self.indexed_by_v3 = indexed_by_pid_type(
            list(cached.values()) + list(remote_data.values()))


class Website:
    def __init__(self, indexed_by_v2, indexed_by_v3):
        self.indexed_by_v2 = indexed_by_v2
        self.indexed_by_v3 = indexed_by_v3

    def is_registered(self, pid):
        return bool(self.indexed_by_v2.get(pid) or self.indexed_by_v3.get(pid))


def report(pids, kernel, website):
    report_indexed_by_v2 = {}
    report_indexed_by_v3 = {}
    for v2 in pids:
        y = v2[10:14]
        v3 = kernel.indexed_by_v2.get(v2) or website.indexed_by_v2.get(v2)
        d = dict(year=y, v2=v2, v3=v3, kernel=kernel.is_registered(v2), published=website.is_registered(v2))
        report_indexed_by_v2[v2] = d
        report_indexed_by_v3[v3] = d
    return report_indexed_by_v2, report_indexed_by_v3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pids_file_path",
        help="Caminho do arquivo que contém uma lista de PIDs para avaliar o status")
    parser.add_argument(
        "kernel_json_file_path",
        help="Caminho do arquivo que contém os dados de documentos registrados no KERNEL")
    parser.add_argument(
        "website_json_file_path",
        help="Caminho do arquivo que contém os dados de documentos registrados no SITE")
    parser.add_argument(
        "report_csv_file_path",
        help="Caminho do arquivo do relatório de status em formato CSV")
    parser.add_argument(
        "cache_path",
        help="Caminho da pasta para baixar os dados resultantes da consulta kernel/documents/ID/front")

    parser.add_argument(
        "--report_v2_json_file_path",
        help="Caminho do arquivo que contém os mesmos dados de `report_csv_file_path` "
             "mas no formato JSON e indexado pelo pid v2")
    parser.add_argument(
        "--report_v3_json_file_path",
        help="Caminho do arquivo que contém os mesmos dados de `report_csv_file_path` "
             "mas no formato JSON e indexado pelo pid v3")
    parser.add_argument(
        "--report_not_imported_file_path",
        help="Caminho do arquivo que contém lista de PIDs que estão na lista de entrada "
             "mas não estão presentes no Kernel")

    args = parser.parse_args()

    kernel_content = read_file(args.kernel_json_file_path)
    kernel_pids = extract_pids_from_kernel(kernel_content)

    website_content = read_file(args.website_json_file_path)
    website_pids = extract_pids_from_website(website_content)
    website_pids_v2, website_pids_v3 = indexed_by_pid_type(website_pids)

    pids_items = read_file_rows(args.pids_file_path)

    website = Website(website_pids_v2, website_pids_v3)
    kernel = Kernel(kernel_pids, website, args.cache_path)

    report_v2, report_v3 = report(pids_items, kernel, website)

    write_csv_file(args.report_csv_file_path, report_v2.values())

    if args.report_v2_json_file_path:
        write_file(args.report_v2_json_file_path, json.dumps(report_v2))
    if args.report_v3_json_file_path:
        write_file(args.report_v3_json_file_path, json.dumps(report_v3))
    if args.report_not_imported_file_path:
        write_file_rows(
            args.report_not_imported_file_path,
            [v2 for v2, d in report_v2.items() if not d.get('kernel')])


if __name__ == "__main__":
    main()