#!/usr/bin/python
# coding: utf-8
import os
import shutil
import sys
import argparse
import textwrap
import json
import csv
import logging
import pathlib
from copy import deepcopy

import fs
import packtools
from fs import path, copy, errors
from lxml import etree
from tqdm import tqdm

from documentstore_migracao import config
from documentstore_migracao.utils import xml, files, DoJobsConcurrently
from documentstore_migracao.export.sps_package import SPS_Package
from documentstore_migracao.export.sps_package import (
    InvalidAttributeValueError,
    NotAllowedtoChangeAttributeValueError,
)


logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


class BuildPSPackage(object):
    """
    Build PS package based on SciELO Site folder structure.

    Folder Struture of legacy SciELO Site:

        <INSTALLED_PATH>/bases/xml
        <INSTALLED_PATH>/bases/pdf
        <INSTALLED_PATH>/htdocs/img/revistas

    """

    def __init__(
        self, xml_folder, img_folder, pdf_folder, out_folder, articles_csvfile
    ):
        self.xml_folder = xml_folder
        self.img_folder = img_folder
        self.pdf_folder = pdf_folder
        self.out_folder = out_folder
        self.articles_csvfile = articles_csvfile
        self.issns = {}

    @property
    def xml_fs(self):
        return fs.open_fs(self.xml_folder)

    @property
    def img_fs(self):
        return fs.open_fs(self.img_folder)

    @property
    def pdf_fs(self):
        return fs.open_fs(self.pdf_folder)

    @property
    def out_fs(self):
        return fs.open_fs(self.out_folder)

    def copy(self, src_path, dst_path, src_fs=None, dst_fs=None):

        if not src_fs:
            src_fs = self.xml_fs

        if not dst_fs:
            dst_fs = self.out_fs
        try:
            copy.copy_file(src_fs, src_path, dst_fs, dst_path)

            logger.debug(
                "Copy asset: %s to: %s"
                % (
                    path.join(src_fs.root_path, src_path),
                    path.join(dst_fs.root_path, dst_path),
                )
            )

        except errors.ResourceNotFound as e:
            logger.error(e)

    def _update_sps_package_obj(self, sps_package, pack_name, row, xml_target_path) -> SPS_Package:
        """
        Atualiza instancia SPS_Package com os dados de artigos do arquivo
        articles_data_reader, um CSV com os seguintes campos:
            - 'PID'
            - 'PID AOP'
            - 'FILE'
            - 'DATA (COLLECTION)'
            - 'DATA PRIMEIRO PROCESSAMENTO'
            - 'DATA DO ULTIMO PROCESSAMENTO'
            - 'ACRON'
            - 'VOLNUM'
            - 'LANG'
        """
        def _parse_date(str_date):
            return (
                str_date[:4] if int(str_date[:4]) > 0 else "",
                str_date[4:6] if int(str_date[4:6]) > 0 else "",
                str_date[6:8] if int(str_date[6:8]) > 0 else "",
            )

        def _get_date_value(date_label, date_value):
            if date_value:
                logger.debug('Updating document with %s "%s"', date_label, date_value)
                return _parse_date(date_value)
            else:
                logger.debug('Missing "%s" into XML file "%s".', date_label, xml_target_path)

        def _fix_pid(_sps_package, attr_name, attr_value):
            try:
                _sps_package.fix(attr_name, attr_value)
                logger.debug('Updating document with PID "%s"', attr_value)
            except NotAllowedtoChangeAttributeValueError:
                pass
            except InvalidAttributeValueError:
                logger.error('Missing PID V2')

        def _fix_attr(_sps_package, attr_name, attr_value, f_pid, label):
            try:
                _sps_package.fix(attr_name, attr_value)
                logger.debug('Updating document "%s" with %s "%s"', f_pid, label, attr_value)
            except NotAllowedtoChangeAttributeValueError:
                pass
            except InvalidAttributeValueError:
                logger.debug('No %s for document PID "%s"', label, f_pid)

        _sps_package = deepcopy(sps_package)
        f_pid, f_pid_aop, f_file, f_dt_collection, f_dt_created, f_dt_updated, __, __, f_lang = row
        # Verificar se tem PID
        _fix_pid(_sps_package, "scielo_pid_v2", f_pid)
        _fix_attr(_sps_package, "aop_pid", f_pid_aop, f_pid, "AOP PID")
        _fix_attr(_sps_package, "original_language", f_lang, f_pid, "original language")
        _fix_attr(
            _sps_package, "article_id_which_id_type_is_other",
            _sps_package.order, f_pid, "article-id[@pub-id-type='other']"
        )
        new_issns = self.issns and self.issns.get(f_pid[1:10])
        if new_issns:
            _fix_attr(_sps_package, "issns", new_issns, f_pid, "ISSNs")
        if _sps_package.is_ahead_of_print:
            return _sps_package

        collection_pubdate = _sps_package.documents_bundle_pubdate or ""
        collection_pubdate_from_csv = f_dt_collection or ""
        document_pubdate = _sps_package.document_pubdate or ""
        document_pubdate_from_csv = f_dt_created or f_dt_updated or ""

        # Atualiza a data da coleção
        if (
            len(collection_pubdate) > 0
            and len(collection_pubdate[0]) < 4
            and len(collection_pubdate_from_csv) >= 4
        ):
            _sps_package.documents_bundle_pubdate = _parse_date(f_dt_collection)
            logger.debug(
                "[%s] Updating document collection date with '%s'.",
                f_pid,
                _parse_date(f_dt_collection),
            )

        # Atualiza a data de publicação do documento
        if any(document_pubdate) is False and len(document_pubdate_from_csv) >= 4:
            _sps_package.document_pubdate = _parse_date(document_pubdate_from_csv)
            logger.debug(
                "[%s] Updating document publication date with '%s'.",
                f_pid,
                _parse_date(document_pubdate_from_csv),
            )

        return _sps_package

    def update_xml_file(self, xml_target_path, row, pack_name):
        """
        Lê e atualiza o XML do pacote informado com os dados de artigos do arquivo
        articles_data_reader.
        """
        obj_xmltree = xml.loadToXML(xml_target_path)

        logger.debug('Updating XML "%s" with CSV info', xml_target_path)
        sps_package = self._update_sps_package_obj(
            SPS_Package(obj_xmltree), pack_name, row, xml_target_path
        )

        # Salva XML com alterações
        xml.objXML2file(xml_target_path, sps_package.xmltree, pretty=True)
        return sps_package

    def get_existing_xml_path(self, file_path, f_acron, f_volnum):
        """
        Verifica se ``file_path`` informado existe no diretório ``self.xml_folder`` e
        retorna-o em caso positivo. Caso contrário, monta caminho relativo usando dados
        f_acron e f_volnum para montar o path do XML.
        """
        if file_path.find("\\") >= 0:
            # It is a Windows Path
            xml_path = pathlib.PureWindowsPath(file_path)
        else:
            # It is a Posix Path
            xml_path = pathlib.PurePosixPath(file_path)

        csv_file_path = pathlib.Path(self.xml_folder) / xml_path
        if csv_file_path.is_file():
            return str(file_path)

        logger.debug(
            "Filepath %s not found in %s. Trying to find path using CSV data.",
            file_path, self.xml_folder
        )
        xml_relative_path = pathlib.Path(f_acron.lower()) / f_volnum / xml_path.name
        return str(xml_relative_path)

    def get_target_path(self, xml_relative_path):
        target_folder, ext = os.path.splitext(xml_relative_path)
        target_path = os.path.join(self.out_folder, target_folder)
        if os.path.isdir(target_path):
            for f in os.listdir(target_path):
                try:
                    os.unlink(os.path.join(target_path, f))
                except OSError as e:
                    logger.exception(e)
        else:
            os.makedirs(target_path)

        return target_path

    def collect_xml(self, xml_relative_path, target_path):
        source_xml_path = os.path.join(self.xml_folder, xml_relative_path)
        shutil.copy(source_xml_path, target_path)
        xml_target_path = os.path.join(
            target_path, os.path.basename(xml_relative_path))
        return xml_target_path

    def collect_renditions(
        self, target_path, acron, issue_folder, pack_name, langs, pid,
    ):
        """Coleta as manifestações em formato PDF por meio de um caminho
        produzido a partir de `pasta-dos-pdfs/acronimo/issue-volume-numbero/nome-do-pacote`.

        Este método funciona da seguinte forma:
        1) Dado que um documento possua um idioma padrão e uma tradução (pt, en);
        2) Que o nome do pacote seja `pacote-2020-abc`;
        3) Que o idioma principal seja `pt` e a tradução `en`;
        4) As seguintes tentativas de cópia serão feitas:
        4.1) Arquivo `pacote-2020-abc.pdf` -> `destino/pacote-2020-abc.pdf`
        4.2) Arquivo `en_pacote-2020-abc.pdf` -> `destino/en_pacote-2020-abc.pdf`
        4.3) Se o ponto 4.2 falhar uma próxima tentativa para o idioma `en` será feita;
        4.4) Arquivo `pacote-2020-abc-en.pdf` -> `destino/pacote-2020-abc-en.pdf`;

        Caso o documento possua apenas um idioma (pt), apenas o passo 4.1
        será realizado."""

        source_path = os.path.join(self.pdf_folder, acron, issue_folder)
        filename_formats = ["{lang}_{name}.pdf", "{name}-{lang}.pdf"]

        manifest = {}
        renditions_to_search = {langs[0]: [pack_name + ".pdf"]}

        for lang in langs[1:]:
            renditions_to_search.setdefault(lang, [])

            for filename in filename_formats:
                renditions_to_search[lang].append(
                    filename.format(name=pack_name, lang=lang)
                )

        for lang, renditions in renditions_to_search.items():
            for rendition in renditions:
                source_file_path = os.path.join(source_path, rendition)

                try:
                    shutil.copy(source_file_path, target_path)
                except FileNotFoundError:
                    logger.error(
                        "[%s] - Could not find rendition '%s' during packing XML '%s.xml'.",
                        pid,
                        source_file_path,
                        pack_name,
                    )
                else:
                    manifest[lang] = rendition
                    break

        return manifest

    def save_renditions_manifest(self, target_path, metadata):
        if len(metadata) > 0:
            logger.debug("Saving %s/manifest.json", target_path)
            _renditions_manifest_path = path.join(
                target_path,
                "manifest.json",
            )
            with open(_renditions_manifest_path, "w") as jfile:
                jfile.write(json.dumps(metadata))

    def collect_asset_alternatives(self, img_filename, source_path, target_path):
        # Try to find other files with the same filename root
        filenames_to_update = []
        filename_root, __ = os.path.splitext(img_filename)
        with os.scandir(source_path) as it:
            for entry in it:
                entry_name_root, __ = os.path.splitext(os.path.basename(entry.name))
                if entry.is_file() and entry_name_root == filename_root:
                    logger.debug(
                        'Found alternative "%s" for asset "%s"', entry.name, img_filename
                    )
                    shutil.copy(os.path.join(source_path, entry.name), target_path)
                    filenames_to_update.append(entry.name)
        return filenames_to_update

    def update_xml_with_alternatives(
        self, assets_alternatives, sps_package, xml_target_path
    ):
        def add_alternative_to_alternatives_tag(image_element, image_filename):
            image_parent = image_element.getparent()
            new_alternative = etree.Element(image_element.tag)
            new_alternative.set("{http://www.w3.org/1999/xlink}href", image_filename)
            if image_parent.tag == "alternatives":
                image_parent.append(new_alternative)
            else:
                alternative_node = etree.Element("alternatives")
                alternative_node.tail = image_element.tail
                image_element.tail = None
                alternative_node.append(image_element)
                alternative_node.append(new_alternative)
                image_parent.append(alternative_node)

        _xmltree = deepcopy(sps_package.xmltree)
        for asset_filename, alternatives in assets_alternatives.items():
            for new_name in alternatives:
                logger.debug(
                    'New alternative name for asset "%s": "%s"', asset_filename, new_name
                )
                asset_elems = _xmltree.findall(
                    f'.//*[@xlink:href="{asset_filename}"]',
                    namespaces={"xlink": "http://www.w3.org/1999/xlink"},
                )
                for elem in asset_elems:
                    add_alternative_to_alternatives_tag(elem, new_name)

        # Salva XML com alterações
        xml.objXML2file(xml_target_path, _xmltree, pretty=True)

    def collect_assets(
        self,
        target_path: str,
        acron: str,
        issue_folder: str,
        pack_name: str,
        sps_package: SPS_Package,
        xml_target_path: str,
        pid: str,
    ) -> None:
        """Obtém os ativos digitais que estão vinculados ao XML.

        Os ativos digitais capturados incluem também os matériais
        suplementares. Alguns destes materiais estão no formato pdf e portanto
        serão buscados no ponto de montagem específico para tal.

        Por medida de resiliência os arquivos suplementares são buscados nos
        diretórios de imagens e pdfs.

        Params:
            target_path (str): Pasta destino para onde o asset será copiado
            acron (str): Acrônimo do periódico
            issue_folder (str): Nome do diretório relacionado com a issue
            pack_name (str): Nome do pacote
            sps_package (SPS_Package): Instância de SPS_Package iniciada com
                artigo processado
            xml_target_path (str): Caminho final do XML processado
            pid (str): PID do XML processado
        Returns:
            None
        """

        def get_source_directory(asset_name: str) -> str:
            """Retorna o caminho para o diretório onde o aquivo foi procurado.

            Por causa de detalhes no contexto de uso desta função, o retorno
            sempre será um caminho válido por mais que o arquivo não seja localizado,
            tal comportamento é necessário por causa dos arquivos chamados de
            alternativos."""
            if asset_name.endswith(".pdf"):
                for path in [
                    os.path.join(self.pdf_folder, acron, issue_folder),
                    os.path.join(self.img_folder, acron, issue_folder),
                ]:
                    if os.path.exists(os.path.join(path, asset_name)):
                        return path
            return os.path.join(self.img_folder, acron, issue_folder)

        assets_alternatives = {}

        for asset_name in set(sps_package.assets):
            source_path = get_source_directory(asset_name)
            asset_source_path = os.path.join(source_path, asset_name)
            logger.debug('Collection asset "%s" to %s', asset_source_path, target_path)

            try:
                shutil.copy(asset_source_path, target_path)
            except FileNotFoundError:
                alternatives = self.collect_asset_alternatives(
                    asset_name, source_path, target_path
                )
                if len(alternatives) > 0:
                    assets_alternatives[asset_name] = alternatives
                else:
                    logger.error(
                        "[%s] - Could not find asset '%s' during packing XML '%s'.",
                        pid,
                        asset_source_path,
                        xml_target_path,
                    )
        if len(assets_alternatives) > 0:
            self.update_xml_with_alternatives(assets_alternatives, sps_package, xml_target_path)

    def optimise_xml_to_web(self, target_path, xml_target_path, pid):
        xml_filename = os.path.basename(xml_target_path)

        def read_file(filename):
            file_source_path = os.path.join(target_path, filename)
            try:
                with open(file_source_path, "rb") as file_obj:
                    file_bytes = file_obj.read()
            except OSError as exc:
                raise packtools.exceptions.SPPackageError(
                    "[%s] -  Error reading file {} during {} optimization: {}".format(
                        pid, filename, xml_filename, str(exc)
                    )
                )
            else:
                logger.debug(
                    'File "%s" reading %s bytes', file_source_path, len(file_bytes)
                )
                return file_bytes

        logger.debug("Optimizing XML file %s", xml_filename)
        try:
            xml_web_optimiser = packtools.XMLWebOptimiser(
                xml_filename, os.listdir(target_path), read_file, target_path
            )
        except (etree.XMLSyntaxError, etree.SerialisationError) as exc:
            logger.error(
                '[%s] - Error creating XMLWebOptimiser for "%s": %s',
                pid,
                xml_target_path,
                str(exc),
            )
        else:
            optimised_xml = xml_web_optimiser.get_xml_file()
            logger.debug("Saving optimised XML file %s", xml_filename)
            xml.objXML2file(xml_target_path, etree.fromstring(optimised_xml), pretty=True)

            # Salva ativos digitais otimizados
            for asset_filename, asset_bytes in xml_web_optimiser.get_optimised_assets():
                if asset_bytes is None:
                    logger.error(
                        '[%s] - Error saving image file "%s" referenced in "%s": '
                        "no file bytes",
                        pid,
                        asset_filename,
                        xml_filename,
                    )
                else:
                    image_target_path = os.path.join(target_path, asset_filename)
                    logger.debug('Saving image file "%s"', image_target_path)
                    files.write_file_binary(image_target_path, asset_bytes)
            for asset_filename, asset_bytes in xml_web_optimiser.get_assets_thumbnails():
                if asset_bytes is None:
                    logger.error(
                        '[%s] - Error saving image file "%s" referenced in "%s": '
                        "no file bytes",
                        pid,
                        asset_filename,
                        xml_filename,
                    )
                else:
                    image_target_path = os.path.join(target_path, asset_filename)
                    logger.debug('Saving image file "%s"', image_target_path)
                    files.write_file_binary(image_target_path, asset_bytes)

    def get_acron_issuefolder_packname(self, xml_relative_path):
        dirname = os.path.dirname(xml_relative_path)
        basename = os.path.basename(xml_relative_path)
        pack_name, ext = os.path.splitext(basename)
        acron = os.path.dirname(dirname)
        issue_folder = os.path.basename(dirname)
        return acron, issue_folder, pack_name

    def start_collect(self, row, poison_pill=None):
        if len(row) == 0:
            return

        (
            f_pid,
            f_pid_aop,
            f_file,
            f_dt_collection,
            f_dt_created,
            f_dt_updated,
            f_acron,
            f_volnum,
            f_lang,
        ) = row.values()

        xml_relative_path = self.get_existing_xml_path(f_file, f_acron, f_volnum)
        target_path = self.get_target_path(xml_relative_path)
        logger.debug(
            "Processing ID: %s, XML: %s, Package: %s",
            f_pid,
            xml_relative_path,
            target_path,
        )
        try:
            xml_target_path = self.collect_xml(xml_relative_path, target_path)
        except FileNotFoundError as e:
            logger.error(
                "[%s] Could not find the XML file '%s'.", f_pid, xml_relative_path
            )
        else:
            acron, issue_folder, pack_name = self.get_acron_issuefolder_packname(
                xml_relative_path
            )

            try:
                xml_sps = self.update_xml_file(xml_target_path, row.values(), pack_name)
            except Exception as exc:
                logger.error(
                    "[%s] Could not update xml '%s'. The exception '%s' was raised.",
                    f_pid,
                    xml_relative_path,
                    exc,
                )
            else:
                renditions = self.collect_renditions(
                    target_path,
                    acron,
                    issue_folder,
                    pack_name,
                    xml_sps.languages,
                    f_pid,
                )
                self.save_renditions_manifest(target_path, dict(renditions))
                self.collect_assets(
                    target_path,
                    acron,
                    issue_folder,
                    pack_name,
                    xml_sps,
                    xml_target_path,
                    f_pid,
                )
                self.optimise_xml_to_web(target_path, xml_target_path, f_pid)

    def run(self):
        fieldnames = (
            "pid",
            "aop_pid",
            "file_path",
            "date_collection",
            "date_created",
            "date_updated",
            "acron",
            "volnum",
            "lang",
        )
        with open(self.articles_csvfile, encoding="utf-8", errors="replace") as csvfile:
            # pid, aoppid, file, pubdate, epubdate, update, acron, volnum
            articles_data_reader = csv.DictReader(csvfile, fieldnames=fieldnames)
            jobs = [{"row": row} for row in articles_data_reader]
            with tqdm(total=len(jobs)) as pbar:

                def update_bar(pbar=pbar):
                    pbar.update(1)

                def exception_callback(exception, job, logger=logger):
                    logger.error(
                        "Could not import package '%s'. The following exception "
                        "was raised: '%s'.",
                        job["row"],
                        exception,
                     )

                DoJobsConcurrently(
                    self.start_collect,
                    jobs=jobs,
                    max_workers=int(config.get("THREADPOOL_MAX_WORKERS")),
                    exception_callback=exception_callback,
                    update_bar=update_bar,
                )


def main():
    usage = """\
    Build PS package based on SciELO Site folder structure.

    Folders used by this script are:

        bases/xml
        bases/pdf
        htdocs/img/revistas

    IMPORTANTE: This script must be execute on a SciELO Site instance.

    Execute example: python build_ps_package.py  -Xfolder data/xml -Ifolder data/img -Pfolder data/pdf -Ofolder data/output

    """

    parser = argparse.ArgumentParser(textwrap.dedent(usage))

    parser.add_argument(
        "-Xfolder",
        "--Xfolder",
        dest="xml_folder",
        required=True,
        help="XML folder path.",
    )

    parser.add_argument(
        "-Ifolder",
        "--Ifolder",
        dest="img_folder",
        required=True,
        help="IMG folder path.",
    )

    parser.add_argument(
        "-Pfolder",
        "--pfolder",
        dest="pdf_folder",
        required=True,
        help="PDF folder path.",
    )

    parser.add_argument(
        "-Ofolder",
        "--ofolder",
        dest="output_folder",
        required=True,
        help="Output path.",
    )

    parser.add_argument(
        "-Article-csvfile",
        "--article-csvfile",
        dest="articles_csvfile",
        required=True,
        help="Article CSV data file from ISIS bases",
    )

    parser.add_argument(
        "-v", "--version", action="version", version="version: 0.1.beta"
    )

    args = parser.parse_args()

    build_ps = BuildPSPackage(
        args.xml_folder,
        args.img_folder,
        args.pdf_folder,
        args.output_folder,
        args.articles_csvfile,
    )

    return build_ps.run()


if __name__ == "__main__":

    sys.exit(main() or 0)
