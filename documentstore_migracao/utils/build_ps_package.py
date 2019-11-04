#!/usr/bin/python
# coding: utf-8

import sys
import argparse
import textwrap
import json
import csv
import logging
from copy import deepcopy

import fs
from fs import path, copy, errors
from fs.walk import Walker

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
        self, acrons, xml_folder, img_folder, pdf_folder, out_folder, articles_csvfile
    ):
        """
        Param acrons: It list of acronym.

        Example: ['mana', 'aa']
        """
        self.xml_folder = xml_folder
        self.img_folder = img_folder
        self.pdf_folder = pdf_folder
        self.out_folder = out_folder
        self.articles_csvfile = articles_csvfile

        if acrons:
            self.acrons = acrons
        else:
            self.acrons = [
                acron for acron in self.xml_fs.listdir(".") if self.xml_fs.isdir(acron)
            ]

    def check_acrons(self):
        """
        The struture of the xml_folder:

            xml
             |---aa
             |---mana
             |---ars
             |---ct

        The sub-folder of this structure are acronyms.

        This method must check if exists file system directory acronym.

        Return True or False, if all directory exists or not.
        """

        with self.xml_fs as cwd:
            for acron in self.acrons:
                if not cwd.exists(acron) or not cwd.isdir(acron):
                    logging.info("There ins`t folder with acronym: %s" % acron)
                    return False

        return True

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

    def _update_sps_package_object(self, articles_data_reader, sps_package, pack_name):
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
        def _get_article_data_by_file_path(articles_data_reader):
            article_data = None
            for row in articles_data_reader:
                if pack_name in row[f_file]:
                    article_data = row
                    logging.debug(
                        'Updating document with PID "%s"', article_data[f_pid]
                    )
                    break
            return article_data

        def _get_article_data_by_publisher_id(articles_data_reader):
            article_data = None
            logging.debug('Reading document PID "%s" data', _sps_package.publisher_id)
            for row in articles_data_reader:
                if _sps_package.publisher_id == row[f_pid]:
                    article_data = row
                    break
            return article_data

        def _has_attr_to_set(attr, field, min_attr_len=1):
            _sps_package_attr = getattr(_sps_package, attr) or ""
            _has_attr = len("".join(_sps_package_attr)) > min_attr_len
            if _has_attr:
                return False
            _data_field = article_data[field]
            if _data_field is not None and len(_data_field) > 0:
                return True
            return False

        def _parse_date(str_date):
            return (
                str_date[:4] if int(str_date[:4]) > 0 else "",
                str_date[4:6] if int(str_date[4:6]) > 0 else "",
                str_date[6:8] if int(str_date[6:8]) > 0 else "",
            )

        _sps_package = deepcopy(sps_package)
        f_pid, f_pid_aop, f_file, f_dt_collection, f_dt_created, f_dt_updated = (
            articles_data_reader.fieldnames
        )
        # Verificar se tem PID
        if _sps_package.publisher_id is None:
            article_data = _get_article_data_by_file_path(articles_data_reader)
            _sps_package.publisher_id = article_data[f_pid]
        else:
            article_data = _get_article_data_by_publisher_id(articles_data_reader)

        if article_data is not None:
            if _has_attr_to_set("aop_pid", f_pid_aop):
                logging.debug(
                    'Updating document with AOP PID "%s"', article_data[f_pid_aop]
                )
                _sps_package.aop_pid = article_data[f_pid_aop]

            # Verificar data de publicação e da coleção
            if not _sps_package.is_ahead_of_print:
                if _has_attr_to_set("documents_bundle_pubdate", f_dt_collection, 3):
                    logging.debug(
                        'Updating document with collection date "%s"',
                        article_data[f_dt_collection],
                    )
                    _sps_package.documents_bundle_pubdate = _parse_date(
                        article_data[f_dt_collection]
                    )
                if _has_attr_to_set("document_pubdate", f_dt_created, 5):
                    if len(_sps_package.documents_bundle_pubdate[0]) > 0:
                        logging.debug(
                            'Updating document with first date "%s"',
                            article_data[f_dt_created],
                        )
                        _sps_package.document_pubdate = _parse_date(
                            article_data[f_dt_created]
                        )
                elif _has_attr_to_set("document_pubdate", f_dt_updated, 5):
                    if len(_sps_package.documents_bundle_pubdate[0]) > 0:
                        logging.debug(
                            'Updating document with update date "%s"',
                            article_data[f_dt_updated],
                        )
                        _sps_package.document_pubdate = _parse_date(
                            article_data[f_dt_updated]
                        )

        return _sps_package

    def update_xml_file(self, articles_data_reader, acron, issue_folder, pack_name):
        """
        Lê e atualiza o XML do pacote informado com os dados de artigos do arquivo
        articles_data_reader.
        """
        target_xml_path = path.join(
            self.out_fs.root_path, acron, issue_folder, pack_name, pack_name + ".xml"
        )
        # Ler target_xml_path
        obj_xmltree = xml.loadToXML(target_xml_path)
        obj_xml = obj_xmltree.getroot()
        sps_package = self._update_sps_package_object(
            articles_data_reader, SPS_Package(obj_xmltree), pack_name
        )
        # Salva XML com alterações
        xml.objXML2file(target_xml_path, sps_package.xmltree, pretty=True)
        return sps_package

    def collect_xml(self, acron, xml):
        issue_folder = path.basename(path.dirname(xml))

        file_name_ext = path.basename(xml)

        file_name, _ = path.splitext(file_name_ext)

        target_folder = path.join(acron, issue_folder, file_name)

        logging.info("Make dir package: %s" % target_folder)

        self.out_fs.makedirs(target_folder, recreate=True)

        xml_path = path.combine(acron, xml)

        target_xml_path = path.join(acron, issue_folder, file_name, file_name_ext)

        self.copy(xml_path, target_xml_path)
        return issue_folder, file_name

    def rename_pdf_trans_filename(self, filename):

        if filename.find("_") == 3:
            name, ext = path.splitext(path.basename(filename))

            return "%s%s%s%s" % (name[3:], "-", name[0:2], ext)
        else:
            return path.basename(filename)

    def collect_pdf(self, acron, issue_folder, pack_name, languages):
        def get_rendition_info(languages, pdf_filename):
            pdf_uri = path.join("pdf", acron, issue_folder, pdf_filename)
            if pdf_filename.find("_") == 2:
                return {lang: pdf_uri for lang in languages if lang in pdf_filename}
            else:
                pdf_lang = [lang for lang in languages if lang in pdf_filename]
                if len(pdf_lang) == 0:
                    return {languages[0]: pdf_uri}

        def save_renditions_manifest(metadata):
            if len(metadata) > 0:
                logging.info(
                    "Saving %s/%s/%s/manifest.json", acron, issue_folder, pack_name
                )
                _renditions_manifest_path = path.join(
                    self.out_fs.root_path,
                    acron,
                    issue_folder,
                    pack_name,
                    "manifest.json",
                )
                with open(_renditions_manifest_path, "w") as jfile:
                    jfile.write(json.dumps(metadata))

        walker = Walker(filter=["*" + pack_name + "*.pdf"], max_depth=2)

        pdf_path = path.join(self.pdf_fs.root_path, acron, issue_folder)

        renditions_manifest = {}
        for pdf in walker.files(fs.open_fs(pdf_path)):

            pdf_path = path.join(acron, issue_folder, path.basename(pdf))

            target_pdf_path = path.join(
                acron, issue_folder, pack_name, self.rename_pdf_trans_filename(pdf)
            )

            self.copy(pdf_path, target_pdf_path, src_fs=self.pdf_fs)

            rendition_info = get_rendition_info(languages, path.basename(pdf))
            if rendition_info is not None:
                logging.info("Updating renditions manifest with %s", rendition_info)
                renditions_manifest.update(rendition_info)

        save_renditions_manifest(renditions_manifest)

    def collect_img(self, acron, issue_folder, pack_name):

        walker = Walker(
            filter=["*" + pack_name + "*"], max_depth=2, exclude_dirs=["html"]
        )

        img_path = path.join(self.img_fs.root_path, acron, issue_folder)

        for img in walker.files(fs.open_fs(img_path)):

            img_path = path.join(acron, issue_folder, path.basename(img))

            target_img_path = path.join(
                acron, issue_folder, pack_name, path.basename(img)
            )

            self.copy(img_path, target_img_path, src_fs=self.img_fs)

    def run(self):

        if not self.check_acrons():
            return False

        with open(self.articles_csvfile, encoding="utf-8", errors="replace") as csvfile:
            # pid, aoppid, file, pubdate, epubdate, update
            articles_data_reader = csv.DictReader(csvfile)

            for acron in self.acrons:

                logging.info("Process acronym: %s" % acron)

                walker = Walker(filter=["*.xml"], exclude=["*.*.xml"])

                acron_folder = path.join(self.xml_fs.root_path, acron)

                for xml in walker.files(fs.open_fs(acron_folder)):

                    if len(path.iteratepath(xml)) == 2:

                        logging.info("Process XML: %s" % xml)

                        issue_folder, pack_name = self.collect_xml(acron, xml)

                        csvfile.seek(0)
                        xml_sps = self.update_xml_file(
                            articles_data_reader, acron, issue_folder, pack_name
                        )

                        self.collect_pdf(
                            acron, issue_folder, pack_name, xml_sps.languages
                        )

                        self.collect_img(acron, issue_folder, pack_name)


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
        "-a", "--acrons", dest="acrons", nargs="+", help="journal acronyms."
    )

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
        args.acrons,
        args.xml_folder,
        args.img_folder,
        args.pdf_folder,
        args.output_folder,
        args.articles_csvfile,
    )

    return build_ps.run()


if __name__ == "__main__":

    sys.exit(main() or 0)
