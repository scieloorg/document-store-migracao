""" module to processing to inserting methods """
import os
import re
import logging
import json
import concurrent.futures
from typing import List, Tuple
from mimetypes import MimeTypes
from urllib.parse import urlparse

import lxml
from tqdm import tqdm
from xylose.scielodocument import Journal

from documentstore.domain import utcnow, DocumentsBundle, get_static_assets, Document
from documentstore.exceptions import AlreadyExists, DoesNotExist
from documentstore.interfaces import Session

from documentstore_migracao.utils import (
    files,
    xml,
    manifest,
    scielo_ids_generator,
    add_document,
    add_journal,
    update_journal,
    add_bundle,
    update_bundle,
    add_renditions,
    DoJobsConcurrently,
    PoisonPill,
)
from documentstore_migracao import config, exceptions
from documentstore_migracao.export.sps_package import DocumentsSorter, SPS_Package
from documentstore_migracao.processing import reading
from documentstore_migracao.tools import constructor
from documentstore_migracao.utils.files import xml_files_list


logger = logging.getLogger(__name__)


__all__ = ["import_documents_to_kernel", "register_documents_in_documents_bundle"]


def get_document_renditions(
    folder: str, file_prefix: str, storage: object
) -> List[dict]:
    """Faz o envio das manifestações do pacote com base no arquivo
    manifest.json e retorna o resultado do envio destas manifestações
    para o object store."""

    mimetypes = MimeTypes()
    _renditions = []

    try:
        _manifest_json = json.loads(
            files.read_file(os.path.join(folder, "manifest.json"))
        )
    except Exception as exc:
        logger.error("Could not read manifest: %s", str(exc))
    else:
        _manifest = {lang: urlparse(url).path for lang, url in _manifest_json.items()}
        logger.debug("Renditions lang and legacy url: %s", _manifest)

        for lang, legacy_url in _manifest.items():
            rendition = os.path.basename(legacy_url)
            _mimetype = mimetypes.guess_type(rendition)[0]
            _rendition_path = os.path.join(folder, rendition)
            _rendition = {
                "filename": rendition,
                "url": storage.register(
                    _rendition_path, file_prefix, _manifest.get(lang)
                ),
                "size_bytes": os.path.getsize(_rendition_path),
                "mimetype": _mimetype,
                "lang": lang,
            }

            _renditions.append(_rendition)

    return _renditions


def get_document_assets_path(
    xml: lxml.etree, folder_files: list, folder: str, prefered_types=[".tif"]
) -> Tuple[dict, dict]:
    """Retorna a lista de assets e seus respectivos paths no
    filesystem. Também retorna um dicionário com `arquivos adicionais`
    que por ventura existam no pacote SPS. Os arquivos adicionais podem
    existir se o XML referênciar um arquivo estático que possua mais de
    uma extensão dentro do pacote SPS.

    Para os assets do tipo `graphic` existe uma ordem de preferência para os
    tipos de arquivos onde arquivos `.tif` são preferênciais em comparação
    com arquivos `.jp*g` ou `.png`. Exemplo:

    1) Referência para arquivo `1518-8787-rsp-40-01-92-98-gseta`
    2) Pacote com arquivos `1518-8787-rsp-40-01-92-98-gseta.jpeg` e
       `1518-8787-rsp-40-01-92-98-gseta.tif`
    3) Resultado de asset `{'1518-8787-rsp-40-01-92-98-gseta': '1518-8787-rsp-40-01-92-98-gseta.tif'}
    4) Resultado para arquivo adicional: `[1518-8787-rsp-40-01-92-98-gseta.jpeg]`
    """

    # TODO: é preciso que o get_static_assets conheça todos os tipos de assets
    static_assets = dict([(asset[0], None) for asset in get_static_assets(xml)])
    static_additionals = {}

    for folder_file in folder_files:
        file_name, extension = os.path.splitext(folder_file)

        for key in static_assets.keys():
            path = os.path.join(folder, folder_file)

            if key == folder_file:
                static_assets[key] = path
            elif key in folder_file and extension in prefered_types:
                static_assets[key] = path
            elif key in folder_file and static_assets[key] is None:
                static_assets[key] = path
            elif file_name == key:
                static_additionals[key] = path
            elif file_name == os.path.splitext(key)[0]:
                static_additionals[file_name] = path

    return (static_assets, static_additionals)


def put_static_assets_into_storage(
    assets: dict, prefix: str, storage, ignore_missing_assets: bool = True
) -> List[dict]:
    """Armazena os arquivos assets em um object storage"""
    _assets = []

    for asset_name, asset_path in assets.items():
        if not asset_path and ignore_missing_assets:
            continue

        _assets.append(
            {"asset_id": asset_name, "asset_url": storage.register(asset_path, prefix)}
        )

    return _assets


def get_article_result_dict(sps: SPS_Package) -> dict:
    """Produz um dictionário contento informações sobre o artigo.

    O dicionário produzido com informações relevantes para recuperação
    do fascículo ao qual o documento está relacionado e a sua posição de registro ou
    posição na lista de artigos do site (order)."""

    def _format_str(value):
        if value and value.isdigit():
            return value.zfill(5)
        return value or ""

    article_metadata = {}
    article_meta = dict(sps.parse_article_meta)
    journal_meta = dict(sps.journal_meta)
    attributes = (
        ("pid_v3", sps.scielo_pid_v3),
        ("eissn", journal_meta.get("eissn")),
        ("pissn", journal_meta.get("pissn")),
        ("issn", journal_meta.get("issn")),
        ("acron", journal_meta.get("acron")),
        ("pid", sps.scielo_pid_v2),
        ("year", sps.year),
        ("volume", sps.volume),
        ("number", sps.number),
        ("supplement", sps.supplement),
        ("order", sps.order),
    )
    for key, value in attributes:
        if value is not None:
            article_metadata[key] = "%s" % value

    return dict(article_metadata)


def register_document(folder: str, session, storage, pid_database_engine, poison_pill=PoisonPill()) -> None:
    """Registra registra pacotes SPS em uma instância do Kernel e seus
    ativos digitais em um object storage."""

    if poison_pill.poisoned:
        return

    logger.debug("Starting the import step for '%s' package.", folder)

    package_files = files.list_files(folder)
    xmls = files.xml_files_list(folder)

    if xmls is None or len(xmls) == 0:
        raise exceptions.XMLError(
            "There is no XML file into package '%s'. Please verify and try later."
            % folder
        ) from None

    xml_path = os.path.join(folder, xmls[0])
    constructor.article_xml_constructor(xml_path, folder, pid_database_engine, False)

    try:
        obj_xml = xml.loadToXML(xml_path)
    except lxml.etree.ParseError as exc:
        raise exceptions.XMLError(
            "Could not parse the '%s' file, please validate"
            " this file before then try to import again." % xml_path,
        ) from None

    xml_sps = SPS_Package(obj_xml)
    prefix = xml_sps.media_prefix or ""
    url_xml = storage.register(xml_path, prefix)
    static_assets, static_additionals = get_document_assets_path(
        obj_xml, package_files, folder
    )
    registered_assets = put_static_assets_into_storage(static_assets, prefix, storage)

    for additional_path in static_additionals.values():
        storage.register(os.path.join(additional_path), prefix)

    renditions = get_document_renditions(folder, prefix, storage)
    document = Document(
        manifest=manifest.get_document_manifest(
            xml_sps, url_xml, registered_assets, renditions
        )
    )

    try:
        add_document(session, document)
        if renditions:
            add_renditions(session, document)
    except AlreadyExists as exc:
        logger.error(exc)
    else:
        logger.debug("Document with id '%s' was imported.", document.id())

    return get_article_result_dict(xml_sps)


def get_documents_bundle(session_db, bundle_id, is_issue, issn):
    logger.debug("Fetch documents bundle {}".format(bundle_id))
    try:
        documents_bundle = session_db.documents_bundles.fetch(bundle_id)
    except DoesNotExist:
        if is_issue:
            raise ValueError("Nenhum documents_bundle encontrado %s" % bundle_id)
        else:
            try:
                documents_bundle = create_aop_bundle(session_db, issn)
            except DoesNotExist:
                raise ValueError(
                    "Nenhum periódico encontrado para criação do AOP %s" % issn
                )
            else:
                return documents_bundle
    else:
        return documents_bundle


def create_aop_bundle(session_db, issn):
    journal = session_db.journals.fetch(issn)
    bundle_id = scielo_ids_generator.aops_bundle_id(issn)
    bundle = DocumentsBundle(
        manifest=manifest.get_document_bundle_manifest(bundle_id, utcnow())
    )
    add_bundle(session_db, bundle)
    journal.ahead_of_print_bundle = bundle.id()
    update_journal(session_db, journal)
    return session_db.documents_bundles.fetch(bundle.id())


def import_documents_to_kernel(session_db, pid_database_engine, storage, folder, output_path) -> None:
    """Armazena os arquivos do pacote SPS em um object storage, registra o documento
    no banco de dados do Kernel e por fim associa-o ao seu `document bundle`"""

    jobs = [
        {"folder": package_folder, "session": session_db, "storage": storage, "pid_database_engine": pid_database_engine}
        for package_folder, _, files in os.walk(folder)
        if files is not None and len(files) > 0
    ]

    with tqdm(total=len(jobs)) as pbar:

        def update_bar(pbar=pbar):
            pbar.update(1)

        def write_result_to_file(result, path=output_path):
            with open(path, "a") as f:
                f.write(json.dumps(result) + "\n")

        def exception_callback(exception, job, logger=logger):
            logger.error(
                "Could not import package '%s'. The following exception "
                "was raised: '%s'.",
                job["folder"],
                exception,
            )

        # O param executor por padrão é concurrent.futures.ThreadPoolExecutor.
        # É possível e ganhamos velocidade quando utilizamos concurrent.futures.Executor,
        # porém é necessário saber dos por menores que envolve essa alteração, é possível
        # verificar isso em: https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor
        DoJobsConcurrently(
            register_document,
            jobs=jobs,
            max_workers=int(config.get("PROCESSPOOL_MAX_WORKERS")),
            success_callback=write_result_to_file,
            exception_callback=exception_callback,
            update_bar=update_bar,
        )


def link_documents_bundles_with_documents(
    documents_bundle: DocumentsBundle, documents: List[str], session: Session
):
    """Função responsável por atualizar o relacionamento entre
    documents bundles e documents no nível de banco de dados"""
    for document in documents:
        try:
            documents_bundle.add_document(document)
        except AlreadyExists:
            logger.info(
                "Document %s already exists in documents bundle %s"
                % (document, documents_bundle)
            )

    update_bundle(session, documents_bundle)


def register_documents_in_documents_bundle(
    session_db, file_documents: str, file_journals: str
) -> None:
    def get_issn(document):
        """Recupera o ISSN ID do Periódico ao qual documento pertence"""
        journals = reading.read_json_file(file_journals)
        data_journal = {}
        for journal in journals:
            o_journal = Journal(journal)
            if o_journal.print_issn:
                data_journal[o_journal.print_issn] = o_journal.scielo_issn
            if o_journal.electronic_issn:
                data_journal[o_journal.electronic_issn] = o_journal.scielo_issn
            if o_journal.scielo_issn:
                data_journal[o_journal.scielo_issn] = o_journal.scielo_issn

        for issn_type in ("eissn", "pissn", "issn"):
            if document.get(issn_type) is not None:
                issn_value = document[issn_type].strip()
                if data_journal.get(issn_value) is not None:
                    return data_journal[issn_value]

    def get_bundle_info(issn, document):
        """
        Obtém e retorna os dados do `bundle`: ID e se é um fascículo

        Args:
            issn (str): ISSN
            document (dict): Dados do documento

        Returns:
            tuple (bool, str):
                True para é fascículoID do `bundle` de fascículo ou aop
        """
        bundle_id = scielo_ids_generator.any_bundle_id(
                issn,
                document.get("year"),
                document.get("volume"),
                document.get("number"),
                document.get("supplement"),
            )
        aops_bundle_id = scielo_ids_generator.aops_bundle_id(issn)
        is_issue = bundle_id != aops_bundle_id
        return is_issue, bundle_id

    err_filename = os.path.join(
        config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
    )

    with open(file_documents) as f:
        documents = f.readlines()

    documents_bundles = {}
    for document in documents:
        document = json.loads(document)
        issn_id = get_issn(document)
        if issn_id is None:
            logger.error("No ISSN in document '%s'", document["pid_v3"])
            files.write_file(err_filename, document["pid_v3"] + "\n", "a")
            continue
        is_issue, bundle_id = get_bundle_info(issn_id, document)
        documents_bundles.setdefault(bundle_id, {})
        documents_bundles[bundle_id].setdefault("items", [])
        documents_bundles[bundle_id]["items"].append(
            {"id": document.pop("pid_v3"), "order": document.get("order", "")}
        )
        documents_bundles[bundle_id]["data"] = {
            "is_issue": is_issue,
            "bundle_id": bundle_id,
            "issn": issn_id,
        }

    for documents_bundle in documents_bundles.values():

        data = documents_bundle["data"]
        items = documents_bundle["items"]
        try:
            documents_bundle = get_documents_bundle(
                session_db, data["bundle_id"], data["is_issue"], data["issn"]
            )
        except ValueError as exc:
            logger.error(
                "The bundle '%s' was not updated. During executions "
                "this following exception was raised '%s'.",
                data["bundle_id"],
                exc,
            )
            files.write_file(err_filename, data["bundle_id"] + "\n", "a")
        else:
            link_documents_bundles_with_documents(documents_bundle, items, session_db)