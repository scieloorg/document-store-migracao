""" module to processing to inserting methods """

import os
import re
import logging
import json
from typing import List, Tuple
from mimetypes import MimeTypes
import lxml
from xylose.scielodocument import Journal

from documentstore_migracao.utils import files, xml, manifest, scielo_ids_generator
from documentstore_migracao import config, exceptions
from documentstore_migracao.export.sps_package import DocumentsSorter, SPS_Package
from documentstore_migracao.processing import reading

from documentstore.domain import utcnow, DocumentsBundle, get_static_assets
from documentstore.exceptions import AlreadyExists, DoesNotExist
from documentstore.interfaces import Session
from documentstore_migracao.tools import constructor


logger = logging.getLogger(__name__)


class ManifestDomainAdapter:
    """Complementa o manifesto produzido na fase de transformação
    para o formato exigido pelos adapters do Kernel para
    realizar a inserção no MongoDB"""

    def __init__(self, manifest):
        self._manifest = manifest

    def id(self) -> str:
        return self.manifest["id"]

    @property
    def manifest(self) -> dict:
        return self._manifest


def get_document_renditions(
    folder: str, renditions: List[str], file_prefix: str, storage: object
) -> List[dict]:
    """Obtem informações sobre todos os `rendition` informados
    e retorna um dicionário com informações relevantes sobre
    os arquivos"""

    def get_language(filename: str) -> str:
        """Busca pelo idioma do rendition a partir do seu nome"""

        try:
            LANG_REGEX = re.compile(r".*-([a-zA-z-_]+)\.\w+")
            return LANG_REGEX.findall(filename)[-1]
        except:
            return None

    mimetypes = MimeTypes()

    _renditions = []

    for rendition in renditions:
        _mimetype = mimetypes.guess_type(rendition)[0]
        _rendition_path = os.path.join(folder, rendition)
        _lang = get_language(rendition)

        _rendition = {
            "filename": rendition,
            "url": storage.register(_rendition_path, file_prefix),
            "size_bytes": os.path.getsize(_rendition_path),
            "mimetype": _mimetype,
        }

        if _lang is not None:
            _rendition["lang"] = _lang

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


def register_document(folder: str, session_db, storage) -> None:

    logger.info("Processando a Pasta %s", folder)
    list_files = files.list_files(folder)

    obj_xml = None
    prefix = ""
    xml_files = files.xml_files_list(folder)
    _renditions = list(
        filter(lambda file: ".pdf" in file or ".html" in file, list_files)
    )

    if len(xml_files) > 1:
        raise exceptions.XMLError("Existe %s xmls no pacote SPS", len(xml_files))
    else:
        try:
            x_file = xml_files[0]
        except IndexError as ex:
            raise exceptions.XMLError("Não existe XML no pacote SPS: %s", ex)

    xml_path = os.path.join(folder, x_file)
    obj_xml = xml.loadToXML(xml_path)

    xml_sps = SPS_Package(obj_xml)

    # TODO: é possível que alguns artigos não possuam o self.acron
    prefix = xml_sps.media_prefix
    url_xml = storage.register(xml_path, prefix)

    static_assets, static_additionals = get_document_assets_path(
        obj_xml, list_files, folder
    )
    registered_assets = put_static_assets_into_storage(static_assets, prefix, storage)

    for additional_path in static_additionals.values():
        storage.register(os.path.join(additional_path), prefix)

    if obj_xml:
        renditions = get_document_renditions(folder, _renditions, prefix, storage)
        manifest_data = ManifestDomainAdapter(
            manifest=manifest.get_document_manifest(
                obj_xml, url_xml, registered_assets, renditions
            )
        )

        try:
            session_db.documents.add(data=manifest_data)
            session_db.changes.add(
                {"timestamp": utcnow(), "entity": "Document", "id": manifest_data.id()}
            )
            logger.info("Document-store save: %s", manifest_data.id())
        except AlreadyExists as exc:
            logger.exception(exc)

    return obj_xml, manifest_data.id()


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
    _journal = session_db.journals.fetch(issn)
    bundle_id = scielo_ids_generator.aops_bundle_id(issn)
    manifest_data = ManifestDomainAdapter(
        manifest=manifest.get_document_bundle_manifest(bundle_id, utcnow())
    )
    session_db.documents_bundles.add(data=manifest_data)
    session_db.changes.add(
        {"timestamp": utcnow(), "entity": "DocumentsBundle", "id": bundle_id}
    )
    _journal.ahead_of_print_bundle = bundle_id
    session_db.journals.update(_journal)
    session_db.changes.add({"timestamp": utcnow(), "entity": "Journal", "id": issn})
    return session_db.documents_bundles.fetch(bundle_id)


def import_documents_to_kernel(session_db, storage, folder, output_path) -> None:
    """Armazena os arquivos do pacote SPS em um object storage, registra o documento
    no banco de dados do Kernel e por fim associa-o ao seu `document bundle`"""
    documents_sorter = DocumentsSorter()

    register_documents(session_db, storage, documents_sorter, folder)
    with open(output_path, "w") as output:
        output.write(
            json.dumps(documents_sorter.documents_bundles, indent=4, sort_keys=True)
        )


def register_documents(session_db, storage, documents_sorter, folder) -> None:
    """Realiza o processo de importação de pacotes SPS no diretório indicado. O
    processo de importação segue as fases: registro de assets/renditions no
    object storage informado, registro do manifesto na base de dados do Kernel
    informada e ordenação dos documentos em um `documents_sorter` para posterior
    associação aos seus respectivos fascículos"""

    err_filename = os.path.join(config.get("ERRORS_PATH"), "insert_documents.err")

    for path, _, sps_files in os.walk(folder):
        if not sps_files:
            continue

        try:
            xml = list(filter(lambda f: f.endswith(".xml"), sps_files))[0]
            xml_path = os.path.join(path, xml)
            constructor.article_xml_constructor(xml_path, path, False)
            registration_result = register_document(path, session_db, storage)

            if registration_result:
                document_xml, document_id = registration_result
                documents_sorter.insert_document(document_id, document_xml)

        except (IndexError, ValueError, TypeError, exceptions.XMLError) as ex:
            msg = "Falha ao registrar documento %s: %s" % (path, ex)
            logger.error(msg)
            files.write_file(err_filename, msg, "a")


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

    session.documents_bundles.update(documents_bundle)

    session.changes.add(
        {
            "timestamp": utcnow(),
            "entity": "DocumentsBundle",
            "id": documents_bundle.id(),
        }
    )


def register_documents_in_documents_bundle(
    session_db, file_documents: str, file_journals: str
) -> None:

    err_filename = os.path.join(
        config.get("ERRORS_PATH"), "insert_documents_in_bundle.err"
    )

    not_registered = []
    journals = reading.read_json_file(file_journals)
    documents = reading.read_json_file(file_documents)

    data_journal = {}
    for journal in journals:
        o_journal = Journal(journal)
        data_journal[o_journal.print_issn] = o_journal.scielo_issn
        data_journal[o_journal.electronic_issn] = o_journal.scielo_issn
        data_journal[o_journal.scielo_issn] = o_journal.scielo_issn

    documents_bundles = {}
    for scielo_id, document in documents.items():
        is_issue = bool(document.get("volume") or document.get("number"))
        if is_issue:
            bundle_id = scielo_ids_generator.issue_id(
                data_journal[document.get("issn")],
                document.get("year"),
                document.get("volume"),
                document.get("number"),
                document.get("supplement"),
            )
        else:
            bundle_id = scielo_ids_generator.aops_bundle_id(
                data_journal[document.get("issn")]
            )

        documents_bundles.setdefault(bundle_id, {})
        documents_bundles[bundle_id].setdefault("items", [])

        documents_bundles[bundle_id]["items"].append(
            {
                "id": scielo_id,
                "order": document.get("order", ""),
            }
        )
        documents_bundles[bundle_id]["data"] = {
            "is_issue": is_issue,
            "bundle_id": bundle_id,
            "issn": data_journal[document.get("issn")],
        }

    for documents_bundle in documents_bundles.values():

        data = documents_bundle["data"]
        items = documents_bundle["items"]
        try:
            documents_bundle = get_documents_bundle(
                session_db, data["bundle_id"], data["is_issue"], data["issn"]
            )
        except ValueError as error:
            files.write_file(err_filename, data["bundle_id"] + "\n", "a")
            not_registered.append(data["bundle_id"])
        else:
            link_documents_bundles_with_documents(documents_bundle, items, session_db)
