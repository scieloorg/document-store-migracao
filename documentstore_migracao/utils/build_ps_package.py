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
from copy import deepcopy

import fs
from fs import path, copy, errors

from documentstore_migracao.utils import xml
from documentstore_migracao.export.sps_package import SPS_Package


logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)


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

            logging.info(
                "Copy asset: %s to: %s"
                % (
                    path.join(src_fs.root_path, src_path),
                    path.join(dst_fs.root_path, dst_path),
                )
            )

        except errors.ResourceNotFound as e:
            logging.info(e)

    def _update_sps_package_obj(self, sps_package, pack_name, row):
        """
        Atualiza instancia SPS_Package com os dados de artigos do arquivo
        articles_data_reader, um CSV com os seguintes campos:
            - 'PID'
            - 'PID AOP'
            - 'FILE'
            - 'DATA (COLLECTION)'
            - 'DATA PRIMEIRO PROCESSAMENTO'
            - 'DATA DO ULTIMO PROCESSAMENTO'
        """
        def _has_attr_to_set(attr, min_attr_len=1):
            _sps_package_attr = getattr(_sps_package, attr) or ""
            _has_attr = len("".join(_sps_package_attr)) >= min_attr_len
            if _has_attr:
                return False
            return True

        def _parse_date(str_date):
            return (
                str_date[:4] if int(str_date[:4]) > 0 else "",
                str_date[4:6] if int(str_date[4:6]) > 0 else "",
                str_date[6:8] if int(str_date[6:8]) > 0 else "",
            )

        def _get_date_value(date_label, date_value):
            if date_value:
                logging.debug(
                    'Updating document with %s "%s"',
                    date_label,
                    date_value,
                )
                return _parse_date(date_value)
            else:
                logging.exception('Missing "%s"', date_label)

        _sps_package = deepcopy(sps_package)
        f_pid, f_pid_aop, f_file, f_dt_collection, f_dt_created, f_dt_updated = row
        # Verificar se tem PID
        if _has_attr_to_set("scielo_pid_v2"):
            if f_pid:
                _sps_package.scielo_pid_v2 = f_pid
            else:
                logging.exception("Missing PID")

        if _has_attr_to_set("aop_pid"):
            if f_pid_aop:
                _sps_package.aop_pid = f_pid_aop
            else:
                logging.info("It has no AOP PID")

        # Verificar data de publicação e da coleção
        if not _sps_package.is_ahead_of_print:
            if _has_attr_to_set("documents_bundle_pubdate", 4):
                dt_collection = _get_date_value("collection date", f_dt_collection)
                if dt_collection:
                    _sps_package.documents_bundle_pubdate = dt_collection

            if _has_attr_to_set("document_pubdate", 8):
                if len(_sps_package.documents_bundle_pubdate[0]) > 0:

                    date_value = _get_date_value("first date", f_dt_created)
                    if not date_value:
                        date_value = _get_date_value(
                            "update date", f_dt_updated)
                    if date_value:
                        _sps_package.document_pubdate = date_value

        return _sps_package

    def update_xml_file(self, xml_target_path, row, pack_name):
        """
        Lê e atualiza o XML do pacote informado com os dados de artigos do arquivo
        articles_data_reader.
        """
        obj_xmltree = xml.loadToXML(xml_target_path)

        sps_package = self._update_sps_package_obj(
            SPS_Package(obj_xmltree), pack_name, row
        )
        # Salva XML com alterações
        xml.objXML2file(xml_target_path, sps_package.xmltree, pretty=True)
        return sps_package

    def get_target_path(self, xml_relative_path):
        target_folder, ext = os.path.splitext(xml_relative_path)
        logging.info("Make dir package: %s", target_folder)
        target_path = os.path.join(self.out_folder, target_folder)
        if os.path.isdir(target_path):
            for f in os.listdir(target_path):
                try:
                    os.unlink(os.path.join(target_path, f))
                except OSError as e:
                    logging.exception(e)
        else:
            os.makedirs(target_path)

        return target_path

    def collect_xml(self, xml_relative_path, target_path):
        source_xml_path = os.path.join(self.xml_folder, xml_relative_path)
        shutil.copy(source_xml_path, target_path)
        xml_target_path = os.path.join(
            target_path, os.path.basename(xml_relative_path))
        return xml_target_path

    def collect_renditions(self, target_path, acron, issue_folder, pack_name, langs):
        source_path = os.path.join(self.pdf_folder, acron, issue_folder)
        renditions = []
        files = [(pack_name+".pdf", pack_name+".pdf")]
        for lang in langs[1:]:
            files.append(
                (lang + "_" + pack_name + ".pdf",
                    pack_name + "-" + lang + ".pdf"))
        for source, dest in files:
            try:
                shutil.copy(os.path.join(source_path, source), target_path)
            except FileNotFoundError:
                logging.exception("Not found %s" % source)
            else:
                renditions.append(dest)
        return list(zip(langs, renditions))

    def save_renditions_manifest(self, target_path, metadata):
        if len(metadata) > 0:
            logging.info(
                "Saving %s/manifest.json", target_path
            )
            _renditions_manifest_path = path.join(
                target_path,
                "manifest.json",
            )
            with open(_renditions_manifest_path, "w") as jfile:
                jfile.write(json.dumps(metadata))

    def collect_assets(self, target_path, acron, issue_folder, pack_name, images):
        source_path = os.path.join(self.img_folder, acron, issue_folder)
        for img in set(images):
            try:
                shutil.copy(os.path.join(source_path, img), target_path)
            except FileNotFoundError:
                logging.exception("Not found %s" % img)

    def get_acron_issuefolder_packname(self, xml_relative_path):
        dirname = os.path.dirname(xml_relative_path)
        basename = os.path.basename(xml_relative_path)
        pack_name, ext = os.path.splitext(basename)
        acron = os.path.dirname(dirname)
        issue_folder = os.path.basename(dirname)
        return acron, issue_folder, pack_name

    def run(self):

        fieldnames = "pid,aop_pid,file_path,date_collection,date_created,date_updated".split(",")
        with open(self.articles_csvfile, encoding="utf-8", errors="replace") as csvfile:
            # pid, aoppid, file, pubdate, epubdate, update
            articles_data_reader = csv.DictReader(
                csvfile, fieldnames=fieldnames)
            """
            - 'PID'
            - 'PID AOP'
            - 'FILE'
            - 'DATA (COLLECTION)'
            - 'DATA PRIMEIRO PROCESSAMENTO'
            - 'DATA DO ULTIMO PROCESSAMENTO'
            """
            for row in articles_data_reader:
                if len(row) == 0:
                    continue
                f_pid, f_pid_aop, f_file, f_dt_collection, f_dt_created, f_dt_updated = row.values()

                xml_relative_path = f_file
                logging.info("Process ID: %s" % f_pid)
                logging.info("Process XML: %s" % xml_relative_path)
                target_path = self.get_target_path(xml_relative_path)
                logging.info("Package: %s" % target_path)
                try:
                    xml_target_path = self.collect_xml(xml_relative_path, target_path)
                except FileNotFoundError as e:
                    logging.exception(e)
                else:
                    acron, issue_folder, pack_name = self.get_acron_issuefolder_packname(xml_relative_path)

                    xml_sps = self.update_xml_file(
                        xml_target_path, row.values(), pack_name
                    )
                    renditions = self.collect_renditions(
                        target_path, acron, issue_folder, pack_name,
                        xml_sps.languages)
                    self.save_renditions_manifest(
                        target_path, dict(renditions))
                    self.collect_assets(
                        target_path, acron, issue_folder, pack_name,
                        xml_sps.assets)


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
