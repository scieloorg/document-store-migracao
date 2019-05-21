#!/usr/bin/python
# coding: utf-8

import sys
import argparse
import textwrap

import fs
from fs import path, copy, errors
from fs.walk import Walker


import logging

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)


class BuildPSPackage(object):
    """
    Build PS package based on SciELO Site folder structure.

    Folder Struture of legacy SciELO Site:

        <INSTALLED_PATH>/bases/xml
        <INSTALLED_PATH>/bases/pdf
        <INSTALLED_PATH>/htdocs/img/revistas

    """

    def __init__(self, acrons, xml_folder, img_folder, pdf_folder, out_folder):
        """
        Param acrons: It list of acronym.

        Example: ['mana', 'aa']
        """
        self.xml_folder = xml_folder
        self.img_folder = img_folder
        self.pdf_folder = pdf_folder
        self.out_folder = out_folder

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

    def collect_pdf(self, acron, issue_folder, pack_name):

        walker = Walker(filter=["*" + pack_name + "*.pdf"], max_depth=2)

        pdf_path = path.join(self.pdf_fs.root_path, acron, issue_folder)

        for pdf in walker.files(fs.open_fs(pdf_path)):

            pdf_path = path.join(acron, issue_folder, path.basename(pdf))

            target_pdf_path = path.join(
                acron, issue_folder, pack_name, self.rename_pdf_trans_filename(pdf)
            )

            self.copy(pdf_path, target_pdf_path, src_fs=self.pdf_fs)

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

        if self.check_acrons():
            for acron in self.acrons:

                logging.info("Process acronym: %s" % acron)

                walker = Walker(filter=["*.xml"], exclude=["*.*.xml"])

                acron_folder = path.join(self.xml_fs.root_path, acron)

                for xml in walker.files(fs.open_fs(acron_folder)):

                    if len(path.iteratepath(xml)) == 2:

                        logging.info("Process XML: %s" % xml)

                        issue_folder, pack_name = self.collect_xml(acron, xml)

                        self.collect_pdf(acron, issue_folder, pack_name)

                        self.collect_img(acron, issue_folder, pack_name)

        else:
            return False


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
        "-v", "--version", action="version", version="version: 0.1.beta"
    )

    args = parser.parse_args()

    build_ps = BuildPSPackage(
        args.acrons,
        args.xml_folder,
        args.img_folder,
        args.pdf_folder,
        args.output_folder,
    )

    return build_ps.run()


if __name__ == "__main__":

    sys.exit(main() or 0)
